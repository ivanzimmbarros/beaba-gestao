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
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.backup_sync_cloud import _prefix_norm, boto3_client, repo_root  # noqa: E402
from scripts.e17_1_crypto import decrypt_file, parse_backup_key  # noqa: E402
from scripts.sqlite_backup_verify import verify_backup_destination  # noqa: E402

STATE_REL = Path("staging_restore_drill_state.json")


def _env_kind() -> str:
    return (
        os.environ.get("ENV_TYPE")
        or os.environ.get("BEABA_ENV")
        or "local"
    ).strip().lower()


def _require_staging() -> None:
    k = _env_kind()
    if k in ("staging", "stg"):
        return
    print(f"Este script só corre em staging (ENV_TYPE/BEABA_ENV). Valor actual: «{k}».", file=sys.stderr)
    raise SystemExit(2)


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


def _write_state(root: Path, payload: dict) -> None:
    path = root / STATE_REL.name
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run_drill(root: Path | None = None) -> int:
    _require_staging()
    root = root or repo_root()
    bucket = os.environ.get("S3_BUCKET_NAME", "").strip()
    if not bucket:
        print("S3_BUCKET_NAME ausente.", file=sys.stderr)
        return 2

    key_prefix = _prefix_norm(os.environ.get("S3_PRODUCTION_RESTORE_PREFIX", "production/hourly"))
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
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
    }

    enc_local: Path | None = None
    dec_local: Path | None = None
    target_db = root / "data" / "beaba_gestao.db"
    hourly = root / "backups" / "hourly"
    hourly.mkdir(parents=True, exist_ok=True)

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

        ef, ef_raw = tempfile.mkstemp(prefix="drill_enc_", suffix=".beaba.enc")
        os.close(ef)
        enc_local = Path(ef_raw)
        df, df_raw = tempfile.mkstemp(prefix="drill_dec_", suffix=".db")
        os.close(df)
        dec_local = Path(df_raw)

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

        if target_db.is_file():
            bak = hourly / f"pre_drill_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}.db"
            shutil.copy2(target_db, bak)

        target_db.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dec_local, target_db)

        vr = subprocess.run(
            [sys.executable, str(root / "scripts" / "sqlite_backup_verify.py"), str(target_db)],
            cwd=str(root),
            capture_output=True,
            text=True,
        )
        out = (vr.stdout or "").strip() + (vr.stderr or "").strip()
        stub["sqlite_backup_verify_stdout"] = out[:8000]
        stub["sqlite_backup_verify_rc"] = int(vr.returncode)
        ok_tgt = vr.returncode == 0
        stub["verify_ok"] = ok_tgt
        stub["verify_message"] = out or "(sem saída)"
        stub["ok"] = ok_tgt
        stub["production_encrypted_objects_seen"] = len(lst)
        if not ok_tgt:
            stub["error"] = f"Cópia final em dados falhou `sqlite_backup_verify.py` (rc={vr.returncode})."
            stub["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            _write_state(root, stub)
            return 1

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
        if enc_local is not None:
            enc_local.unlink(missing_ok=True)
        if dec_local is not None:
            dec_local.unlink(missing_ok=True)


def main() -> int:
    return run_drill()


if __name__ == "__main__":
    raise SystemExit(main())
