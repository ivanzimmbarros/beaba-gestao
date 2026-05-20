#!/usr/bin/env python3
"""
Limpeza operacional de ambiente de teste (DEV / STG) — preserva um único utilizador admin.

Uso (na raiz do repositório):
  python scripts/wipe_ambiente_teste.py --ambiente dev --alvo local --confirm WIPE-DEV
  python scripts/wipe_ambiente_teste.py --ambiente dev --alvo cloud --confirm WIPE-DEV
  python scripts/wipe_ambiente_teste.py --ambiente stg --alvo cloud --confirm WIPE-STG
  python scripts/wipe_ambiente_teste.py --run-authorized-batch --confirm WIPE-BATCH

Ver ``docs/governanca/WIPE_AMBIENTE_TESTE.md``.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PRESERVE_EMAIL = "ivanzimmbarros@gmail.com"
PRESERVE_NOME = "Diretor"
DEFAULT_PASSWORD = "BeaBaTeste2026!"

CONFIRM_TOKENS = {
    "dev": "WIPE-DEV",
    "stg": "WIPE-STG",
    "batch": "WIPE-BATCH",
}

AMBIENTE_CONFIG = {
    "dev": {
        "env_type": "dev",
        "beaba_env": "dev",
        "s3_prefix": "dev/hourly/",
        "confirm": CONFIRM_TOKENS["dev"],
        "cloud_url": "https://dev-beabagestao.streamlit.app",
    },
    "stg": {
        "env_type": "staging",
        "beaba_env": "staging",
        "s3_prefix": "stg/hourly/",
        "confirm": CONFIRM_TOKENS["stg"],
        "cloud_url": "https://testes-beabagestao.streamlit.app",
    },
}

OPERATIONAL_TABLES = (
    "dw_etl_run",
    "dw_cliente_kpi",
    "dw_fact_venda",
    "dw_fact_agendamento",
    "repasse_linhas",
    "agendamento_historico",
    "agendamento_colaboradores",
    "agendamentos",
    "credito_movimentos",
    "venda_recebimentos_previstos",
    "venda_pagamento_linhas",
    "venda_pagamentos",
    "venda_itens",
    "vendas",
    "colaborador_disponibilidade_regra",
    "colaborador_disponibilidade_plano",
    "colaborador_servicos",
    "colaboradores",
    "servico_evento_participantes",
    "servico_pacote_produtos",
    "servico_pacote_sessoes",
    "servicos",
    "especialidades",
    "cliente_contatos_emergencia",
    "cliente_filhos",
    "clientes",
    "financeiro_gasto_lancamentos",
    "financeiro_tipo_gasto",
    "financeiro_natureza",
    "financeiro_centro_custo",
    "mfa_tokens",
    "auditoria_sistema",
)

COUNT_TABLES = (
    "clientes",
    "colaboradores",
    "servicos",
    "especialidades",
    "vendas",
    "agendamentos",
    "usuarios",
    "auditoria_sistema",
    "mfa_tokens",
)


def _env_slug(ambiente: str) -> str:
    if ambiente == "stg":
        return "stg"
    return "dev"


def _configure_ambiente(ambiente: str) -> dict:
    if ambiente not in AMBIENTE_CONFIG:
        raise ValueError(f"Ambiente inválido: {ambiente!r} (use dev ou stg).")
    cfg = AMBIENTE_CONFIG[ambiente]
    os.environ["ENV_TYPE"] = cfg["env_type"]
    os.environ["BEABA_ENV"] = cfg["beaba_env"]
    os.environ["S3_UPLOAD_PREFIX"] = cfg["s3_prefix"]
    return cfg


def _load_dotenv() -> None:
    load_dotenv(ROOT / ".env", override=False)


def _latest_enc_key(bucket: str, prefix: str, client) -> str | None:
    objs: list[dict] = []
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        for item in page.get("Contents") or []:
            k = item.get("Key")
            if k and str(k).endswith(".beaba.enc"):
                objs.append(item)
    if not objs:
        return None
    objs.sort(key=lambda x: x.get("LastModified") or 0)
    return str(objs[-1].get("Key"))


def _download_cloud_db(ambiente: str, work_dir: Path) -> Path:
    from scripts.backup_sync_cloud import _prefix_norm, boto3_client
    from scripts.e17_1_crypto import decrypt_file, parse_backup_key

    bucket = (os.environ.get("S3_BUCKET_NAME") or "").strip()
    if not bucket:
        raise RuntimeError("S3_BUCKET_NAME ausente no .env")
    prefix = _prefix_norm(os.environ.get("S3_UPLOAD_PREFIX", ""))
    client = boto3_client()
    remote_key = _latest_enc_key(bucket, prefix, client)
    if not remote_key:
        raise RuntimeError(f"Nenhum backup .beaba.enc em s3://{bucket}/{prefix}")
    enc_local = work_dir / "cloud_latest.beaba.enc"
    dec_local = work_dir / "cloud_restored.db"
    client.download_file(bucket, remote_key, str(enc_local))
    decrypt_file(enc_local, dec_local, parse_backup_key())
    return dec_local


def _snapshot_db(
    db_path: Path,
    *,
    ambiente: str,
    alvo: str,
    label: str,
) -> Path:
    slug = _env_slug(ambiente)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest_dir = ROOT / "backups" / "pre_wipe" / slug / f"{ts}_{alvo}_{label}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_db = dest_dir / "beaba_gestao.db"
    shutil.copy2(db_path, dest_db)

    evidence: dict = {"ambiente": ambiente, "alvo": alvo, "label": label, "db": str(dest_db)}
    try:
        from scripts.e17_1_sqlite_evidence import gather_evidence

        evidence["pre_wipe"] = gather_evidence(dest_db)
    except Exception as exc:
        evidence["pre_wipe_error"] = str(exc)
    (dest_dir / "manifest.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return dest_dir


def _upload_pre_wipe_cloud(snapshot_db: Path, ambiente: str) -> str | None:
    from scripts.backup_sync_cloud import boto3_client
    from scripts.e17_1_crypto import encrypt_file, parse_backup_key

    bucket = (os.environ.get("S3_BUCKET_NAME") or "").strip()
    if not bucket:
        return None
    slug = _env_slug(ambiente)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    remote_key = f"{slug}/pre_wipe/beaba_gestao_{ts}.beaba.enc"
    enc_path = snapshot_db.parent / f"{snapshot_db.stem}.beaba.enc"
    encrypt_file(snapshot_db, enc_path, parse_backup_key())
    client = boto3_client()
    client.upload_file(str(enc_path), bucket, remote_key)
    return remote_key


def _wipe_tables(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys=OFF")
    for table in OPERATIONAL_TABLES:
        try:
            cur.execute(f'DELETE FROM "{table}"')
        except sqlite3.OperationalError:
            pass
    conn.commit()
    cur.execute("PRAGMA foreign_keys=ON")


def _ensure_preserved_user(conn: sqlite3.Connection) -> None:
    from src.modules.auth_utils import hash_password

    mail = PRESERVE_EMAIL.strip().lower()
    pwd_hash = hash_password(DEFAULT_PASSWORD)
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM usuarios WHERE LOWER(TRIM(email)) = LOWER(TRIM(?)) LIMIT 1",
        (mail,),
    )
    row = cur.fetchone()
    if row:
        uid = int(row[0])
        cur.execute(
            """
            UPDATE usuarios
            SET nome = ?, senha_hash = ?, perfil = 'admin', ativo = 1,
                must_change_password = 0
            WHERE id = ?
            """,
            (PRESERVE_NOME, pwd_hash, uid),
        )
    else:
        cur.execute(
            """
            INSERT INTO usuarios (
                nome, email, senha_hash, perfil, ativo, must_change_password, data_cadastro
            ) VALUES (?, ?, ?, 'admin', 1, 0, datetime('now'))
            """,
            (PRESERVE_NOME, mail, pwd_hash),
        )
    cur.execute(
        "DELETE FROM usuarios WHERE LOWER(TRIM(email)) != LOWER(TRIM(?))",
        (mail,),
    )
    conn.commit()


def _finalize_schema(db_path: Path) -> None:
    os.environ["BEABA_SQLITE_PATH"] = str(db_path.resolve())
    os.environ["BEABA_SKIP_EXAMPLE_SEEDS"] = "1"
    from src.database.connection import create_tables

    create_tables()


def _gather_counts(db_path: Path) -> dict[str, int | str]:
    out: dict[str, int | str] = {}
    conn = sqlite3.connect(db_path)
    try:
        ic = conn.execute("PRAGMA integrity_check").fetchone()
        out["integrity_check"] = ic[0] if ic else "?"
        for name in COUNT_TABLES:
            try:
                n = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
                out[name] = int(n)
            except sqlite3.Error:
                out[name] = "n/a"
        row = conn.execute(
            "SELECT email, perfil, ativo FROM usuarios LIMIT 5"
        ).fetchall()
        out["usuarios_sample"] = [list(r) for r in row]
    finally:
        conn.close()
    return out


def _install_operational_db(db_path: Path) -> Path:
    """Copia a base limpa para ``data/beaba_gestao.db`` (fonte dos backups horários)."""
    target = ROOT / "data" / "beaba_gestao.db"
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.parent / f".wipe_tmp_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.db"
    shutil.copy2(db_path, tmp)
    os.replace(tmp, target)
    os.environ["BEABA_SQLITE_PATH"] = str(target.resolve())
    return target


def _force_cloud_sync() -> int:
    py = sys.executable
    repo = str(ROOT)
    hourly = subprocess.run(
        [py, str(ROOT / "scripts" / "backup_sqlite_hourly.py")],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if hourly.returncode != 0:
        print(hourly.stderr or hourly.stdout, file=sys.stderr)
        return hourly.returncode
    sync = subprocess.run(
        [py, str(ROOT / "scripts" / "backup_sync_cloud.py"), "--force-all"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    print(sync.stdout or "", end="")
    if sync.returncode != 0:
        print(sync.stderr or "", file=sys.stderr)
    return sync.returncode


def _resolve_local_db() -> Path:
    from src.database.connection import get_sqlite_database_path

    return Path(get_sqlite_database_path())


def run_wipe(*, ambiente: str, alvo: str, dry_run: bool = False) -> dict:
    if ambiente == "prod":
        raise ValueError("Produção bloqueada. Use dev ou stg.")
    cfg = _configure_ambiente(ambiente)
    _load_dotenv()
    _configure_ambiente(ambiente)

    slug = _env_slug(ambiente)
    work = ROOT / "backups" / slug / "wipe_work"
    work.mkdir(parents=True, exist_ok=True)

    report: dict = {
        "ambiente": ambiente,
        "alvo": alvo,
        "env_type": cfg["env_type"],
        "s3_prefix": cfg["s3_prefix"],
        "cloud_url": cfg.get("cloud_url"),
    }

    if alvo == "local":
        db_path = _resolve_local_db()
        if not db_path.is_file():
            raise FileNotFoundError(f"Base local inexistente: {db_path}")
    elif alvo == "cloud":
        db_path = _download_cloud_db(ambiente, work)
        report["cloud_source"] = str(db_path)
    else:
        raise ValueError(f"Alvo inválido: {alvo!r}")

    report["db_path"] = str(db_path)

    if dry_run:
        report["dry_run"] = True
        report["pre_counts"] = _gather_counts(db_path)
        return report

    snap_dir = _snapshot_db(db_path, ambiente=ambiente, alvo=alvo, label="antes_wipe")
    report["snapshot_dir"] = str(snap_dir)
    try:
        remote_pre = _upload_pre_wipe_cloud(snap_dir / "beaba_gestao.db", ambiente)
        report["snapshot_cloud_key"] = remote_pre
    except Exception as exc:
        report["snapshot_cloud_error"] = str(exc)

    conn = sqlite3.connect(db_path)
    try:
        _wipe_tables(conn)
        _ensure_preserved_user(conn)
    finally:
        conn.close()

    _finalize_schema(db_path)

    if alvo == "cloud":
        installed = _install_operational_db(db_path)
        report["installed_db"] = str(installed)
        sync_rc = _force_cloud_sync()
        report["cloud_sync_exit_code"] = sync_rc
        if sync_rc != 0:
            raise RuntimeError(f"Sync cloud falhou (exit {sync_rc})")
    else:
        sync_rc = None
        if (os.environ.get("S3_BUCKET_NAME") or "").strip():
            installed = _install_operational_db(db_path)
            report["installed_db"] = str(installed)
            try:
                sync_rc = _force_cloud_sync()
                report["optional_local_cloud_sync"] = sync_rc
            except Exception as exc:
                report["optional_local_cloud_sync_error"] = str(exc)

    report["post_counts"] = _gather_counts(db_path if alvo == "local" else _resolve_local_db())
    report["password_reset"] = DEFAULT_PASSWORD
    report["preserve_email"] = PRESERVE_EMAIL
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Wipe de ambiente de teste BeaBa (DEV/STG).")
    ap.add_argument("--ambiente", choices=("dev", "stg"), help="Ambiente alvo.")
    ap.add_argument("--alvo", choices=("local", "cloud"), help="Base local ou cópia cloud (R2).")
    ap.add_argument(
        "--confirm",
        required=True,
        help="Token: WIPE-DEV, WIPE-STG ou WIPE-BATCH.",
    )
    ap.add_argument(
        "--run-authorized-batch",
        action="store_true",
        help="Executa dev/local, dev/cloud e stg/cloud (autorização PROSSEGUIR).",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.run_authorized_batch:
        if args.confirm != CONFIRM_TOKENS["batch"]:
            print(f"Confirmação batch requer {CONFIRM_TOKENS['batch']!r}.", file=sys.stderr)
            return 2
        batch = [
            ("dev", "local"),
            ("dev", "cloud"),
            ("stg", "cloud"),
        ]
        results = []
        for amb, alvo in batch:
            print(f"\n=== WIPE {amb.upper()} / {alvo.upper()} ===\n")
            try:
                rep = run_wipe(ambiente=amb, alvo=alvo, dry_run=args.dry_run)
                results.append(rep)
                print(json.dumps(rep, ensure_ascii=False, indent=2))
            except Exception as exc:
                print(f"FALHA {amb}/{alvo}: {exc}", file=sys.stderr)
                return 1
        out_path = ROOT / "backups" / "pre_wipe" / "last_batch_report.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nRelatório batch: {out_path}")
        return 0

    if not args.ambiente or not args.alvo:
        ap.error("--ambiente e --alvo são obrigatórios (ou use --run-authorized-batch).")

    expected = CONFIRM_TOKENS[args.ambiente]
    if args.confirm != expected:
        print(f"Confirmação para {args.ambiente!r} requer {expected!r}.", file=sys.stderr)
        return 2

    try:
        rep = run_wipe(ambiente=args.ambiente, alvo=args.alvo, dry_run=args.dry_run)
    except Exception as exc:
        print(f"FALHA: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
