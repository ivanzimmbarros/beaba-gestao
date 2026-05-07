"""
Grande teste DR (staging): recupera o último backup **de Produção** do armazenamento S3-compatível,
decripta, substitui o SQLite local de staging e valida com ``sqlite_backup_verify``.

Requisito estrito de ambiente: ``ENV_TYPE`` ou ``BEABA_ENV`` igual a ``staging`` / ``stg``.

Credenciais: ``S3_ACCESS_KEY``, ``S3_SECRET_KEY``, ``S3_BUCKET_NAME`` (e ``S3_ENDPOINT_URL``, ``S3_REGION`` se aplicável).

Prefixo onde estão cópias de produção: ``S3_PRODUCTION_RESTORE_PREFIX`` (defeito ``production/hourly/`` —
alinhado típico de ``S3_UPLOAD_PREFIX`` em produção).

Chave de cópias: ``BEABA_BACKUP_KEY`` (AES-256, igual à usada ao encriptar no upload).

Estado do último fluxo escrito na raiz: ``staging_restore_drill_state.json``.

Coberturas: ``tests/test_backup_drill_contract.py`` (gate staging), ingestão horária ``scripts/backup_sqlite_hourly.py``,
verificação SQLite ``scripts/sqlite_backup_verify.py``, UI admin ``src/ui/page_governanca.py`` + smoke dedicado.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.backup_sync_cloud import _prefix_norm, boto3_client, repo_root  # noqa: E402
from scripts.e17_1_crypto import decrypt_file, parse_backup_key  # noqa: E402
from scripts.sqlite_backup_verify import verify_backup_destination  # noqa: E402

STATE_REL = Path("docs") / "governanca" / "telemetry" / "staging_restore_drill_state.json"


def _env_kind() -> str:
    return (
        os.environ.get("ENV_TYPE")
        or os.environ.get("BEABA_ENV")
        or "local"
    ).strip().lower()


def _require_staging() -> None:
    k = _env_kind()
    if k in ("production", "prod", "main"):
        print(
            f"Trava: restore drill recusado em produção (ENV_TYPE/BEABA_ENV={k!r}).",
            file=sys.stderr,
        )
        raise SystemExit(3)
    if k in ("staging", "stg"):
        return
    print(f"Este script só corre em staging (ENV_TYPE/BEABA_ENV). Valor actual: «{k}».", file=sys.stderr)
    raise SystemExit(2)


def _env_folder_slug() -> str:
    k = _env_kind()
    if k in ("production", "prod", "main"):
        return "prod"
    if k in ("staging", "stg"):
        return "stg"
    return "dev"


def _count_table_rows(db_path: Path, table: str) -> int | None:
    try:
        conn = sqlite3.connect(db_path, timeout=15.0)
        try:
            row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            return int(row[0]) if row else 0
        finally:
            conn.close()
    except sqlite3.Error:
        return None


def _latest_prod_enc_key(bucket: str, prefix: str, client) -> tuple[str | None, list[dict[str, object]]]:
    objs: list[dict[str, object]] = []
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        for item in page.get("Contents") or []:
            k = item.get("Key")
            if not k or isinstance(k, (bytes, bytearray)):
                continue
            if str(k).endswith(".beaba.enc"):
                objs.append(item)
    if not objs:
        return None, []
    objs.sort(key=lambda x: x.get("LastModified") or 0)
    best = objs[-1]
    return str(best.get("Key")), objs


def _obj_last_modified_utc(objs: list[dict[str, object]], key: str) -> datetime | None:
    for item in objs:
        if str(item.get("Key") or "") != key:
            continue
        lm = item.get("LastModified")
        if isinstance(lm, datetime):
            return lm.astimezone(timezone.utc)
    return None


def _rpo_eval(now_utc: datetime, last_modified_utc: datetime | None) -> tuple[str, str, int | None]:
    if last_modified_utc is None:
        return "alerta", "ALERTA: timestamp do backup não disponível para cálculo de RPO.", None
    delay_min = int(round((now_utc - last_modified_utc).total_seconds() / 60.0))
    if delay_min <= 65:
        msg = (
            f"Recuperação garantida: Backup de {last_modified_utc.strftime('%Y-%m-%dT%H:%M:%SZ')} "
            f"(atraso de {delay_min} min) cumpre a meta de 1h"
        )
        return "cumprido", msg, delay_min
    msg = f"ALERTA: Backup com atraso de {delay_min} min. Excede a meta de 1h"
    return "alerta", msg, delay_min


def _write_state(root: Path, payload: dict) -> None:
    path = root / STATE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run_drill(root: Path | None = None) -> int:
    _require_staging()
    root = root or repo_root()
    load_dotenv(root / ".env", override=False)
    bucket = os.environ.get("S3_BUCKET_NAME", "").strip()
    if not bucket:
        print("S3_BUCKET_NAME ausente.", file=sys.stderr)
        return 2

    env_slug = _env_folder_slug()
    if env_slug != "stg":
        print(f"Este script só corre em staging/stg. Pasta resolvida: {env_slug!r}.", file=sys.stderr)
        return 2

    # Prefixo onde estão os backups reais da produção.
    key_prefix = _prefix_norm(os.environ.get("S3_PRODUCTION_RESTORE_PREFIX", "prod/hourly/"))
    now_dt = datetime.now(timezone.utc)
    ts = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    stub = {
        "type": "restore_drill_staging",
        "started_at": ts,
        "finished_at": "",
        "ok": False,
        "error": "",
        "prod_remote_key": None,
        "verify_ok": False,
        "verify_message": "",
        "hostname": socket.gethostname(),
        "environment": env_slug,
        "row_counts_proof": {"clientes": None, "vendas": None},
        "rpo_status": "",
        "rpo_message": "",
        "rpo_delay_minutes": None,
        "prod_backup_last_modified_utc": "",
    }

    base = root / "backups" / "stg"
    restore_verify = base / "restore_verify"
    hourly = base / "hourly"
    restore_verify.mkdir(parents=True, exist_ok=True)
    hourly.mkdir(parents=True, exist_ok=True)

    # Caminhos determinísticos (evita colisões com outros ambientes e facilita auditoria).
    enc_local = restore_verify / "drill_latest_prod.beaba.enc"
    dec_local = restore_verify / "drill_temp.db"

    target_db = root / "data" / "beaba_gestao.db"

    try:
        client = boto3_client()
        rk, lst = _latest_prod_enc_key(bucket, key_prefix, client)
        if not rk:
            stub["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            stub["error"] = f"Sem objectos *.beaba.enc em s3://{bucket}/{key_prefix}"
            _write_state(root, stub)
            print(stub["error"], file=sys.stderr)
            return 1
        stub["prod_remote_key"] = rk
        lm_utc = _obj_last_modified_utc(lst, rk)
        if lm_utc is not None:
            stub["prod_backup_last_modified_utc"] = lm_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        rpo_status, rpo_message, rpo_delay = _rpo_eval(now_dt, lm_utc)
        stub["rpo_status"] = rpo_status
        stub["rpo_message"] = rpo_message
        stub["rpo_delay_minutes"] = rpo_delay
        print(rpo_message)

        obj = client.get_object(Bucket=bucket, Key=rk)
        with enc_local.open("wb") as fh:
            shutil.copyfileobj(obj["Body"], fh)

        dk = parse_backup_key()
        decrypt_file(enc_local, dec_local, dk)

        ok_dec, msg_dec = verify_backup_destination(dec_local)
        stub["verify_ok"] = ok_dec
        stub["verify_message"] = msg_dec
        if not ok_dec:
            stub["error"] = f"Verificação pós-descodificação falhou: {msg_dec}"
            stub["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            _write_state(root, stub)
            print(stub["error"], file=sys.stderr)
            return 1

        vr_tmp = subprocess.run(
            [sys.executable, str(root / "scripts" / "sqlite_backup_verify.py"), str(dec_local)],
            cwd=str(root),
            capture_output=True,
            text=True,
        )
        out_tmp = (vr_tmp.stdout or "").strip() + (vr_tmp.stderr or "").strip()
        stub["sqlite_backup_verify_stdout"] = out_tmp[:8000]
        stub["sqlite_backup_verify_rc"] = int(vr_tmp.returncode)
        ok_tmp = vr_tmp.returncode == 0
        stub["verify_ok"] = ok_tmp
        stub["verify_message"] = out_tmp or "(sem saída)"
        if not ok_tmp:
            stub["error"] = f"Aborto: `sqlite_backup_verify.py` falhou no banco temporário (rc={vr_tmp.returncode})."
            stub["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            _write_state(root, stub)
            print(stub["error"], file=sys.stderr)
            return 1

        # Prova visual mínima (tabelas-chave).
        stub["row_counts_proof"] = {
            "clientes": _count_table_rows(dec_local, "clientes"),
            "vendas": _count_table_rows(dec_local, "vendas"),
        }

        if target_db.is_file():
            bak = hourly / f"pre_drill_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}.db"
            shutil.copy2(target_db, bak)

        target_db.parent.mkdir(parents=True, exist_ok=True)
        tmp_target = target_db.parent / f".beaba_gestao_drill_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}.db"
        shutil.copy2(dec_local, tmp_target)
        os.replace(tmp_target, target_db)

        stub["ok"] = True
        stub["production_encrypted_objects_seen"] = len(lst)

        stub["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        _write_state(root, stub)
        print(f"OK drill: restaurado a partir de s3://{bucket}/{rk} → {target_db}")
        return 0
    except Exception as exc:
        stub["error"] = str(exc)
        stub["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        _write_state(root, stub)
        print(f"Erro no drill DR: {exc}", file=sys.stderr)
        return 1
    finally:
        # Segurança: remove temporários após sucesso.
        try:
            enc_local.unlink(missing_ok=True)
        except OSError:
            pass
        try:
            if bool(stub.get("ok")):
                dec_local.unlink(missing_ok=True)
        except OSError:
            pass


def main() -> int:
    return run_drill()


if __name__ == "__main__":
    raise SystemExit(main())
