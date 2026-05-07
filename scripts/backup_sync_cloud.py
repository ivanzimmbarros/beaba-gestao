"""
Sincroniza cópias horárias (SQLite `.db`) com armazenamento compatível com S3 (AWS, Cloudflare R2, DO Spaces).

Encriptação: AES-256-GCM (``.beaba.enc``) antes do envio (`BEABA_BACKUP_KEY`).
Variáveis (credenciais S3 são obrigatórias para envio real):

  S3_ACCESS_KEY — chave API (IAM / token R2).
  S3_SECRET_KEY — segredo correspondente.
  S3_BUCKET_NAME — bucket/object storage.

 Opcionais:
  S3_ENDPOINT_URL — obrigatório para R2/Spaces (URL base API S3-compatível).
  S3_REGION — região (ex.: ``auto``, ``us-east-1``).
  S3_UPLOAD_PREFIX — prefixo dentro do bucket (ex.: ``production/hourly/``; sem barras repetidas geridas em código).

  BEABA_REPO_ROOT — raiz do projeto (opcional).

Teste rápido local sem enviar: ``--dry-run`` (encriptação + plano apenas).

Coberturas: ``tests/test_backup_drill_contract.py``, ``tests/gov_ui_contract.py``,
``tests/smoke_test_ui.py::test_smoke_governanca_admin_sector_widgets``,
``e2e_stress_test.py::test_e2e_governanca_backup_visual_shell_contract``; orquestrador ``scripts/scheduler.py``; ingestão local ``scripts/backup_sqlite_hourly.py``.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.e17_1_crypto import encrypt_file, parse_backup_key  # noqa: E402

MANIFEST_REL = Path("backups") / "cloud_sync_manifest.json"


def repo_root() -> Path:
    raw = os.environ.get("BEABA_REPO_ROOT")
    if raw:
        return Path(raw).resolve()
    return Path(__file__).resolve().parents[1]


def _env_folder_slug() -> str:
    raw = (os.environ.get("ENV_TYPE") or os.environ.get("BEABA_ENV") or "dev").strip().lower()
    if raw in ("production", "prod", "main"):
        return "prod"
    if raw in ("staging", "stg"):
        return "stg"
    if raw in ("develop", "dev", "development", "local"):
        return "dev"
    return "dev"


def _default_upload_prefix(*, env_slug: str, backup_kind: str) -> str:
    # Ex.: prod/hourly/, stg/daily/, dev/hourly/
    kind = (backup_kind or "hourly").strip().lower()
    if kind not in ("hourly", "daily", "weekly"):
        kind = "hourly"
    return f"{env_slug}/{kind}/"


def _prefix_norm(prefix: str) -> str:
    p = (prefix or "").strip().replace("\\", "/")
    if not p:
        return ""
    if not p.endswith("/"):
        return p + "/"
    return p


def boto3_client():
    """Cliente S3 (AWS ou endpoint compatível)."""
    import boto3
    from botocore.config import Config

    endpoint = os.environ.get("S3_ENDPOINT_URL") or None
    region = os.environ.get("S3_REGION") or ("auto" if endpoint else "us-east-1")
    key_id = os.environ.get("S3_ACCESS_KEY") or os.environ.get("AWS_ACCESS_KEY_ID")
    secret = os.environ.get("S3_SECRET_KEY") or os.environ.get("AWS_SECRET_ACCESS_KEY")
    if not key_id or not secret:
        raise ValueError("S3_ACCESS_KEY e S3_SECRET_KEY são obrigatórios.")

    cfg = Config(s3={"addressing_style": "path"}) if endpoint else None
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=key_id,
        aws_secret_access_key=secret,
        region_name=region,
        config=cfg,
    )


def _load_manifest(root: Path) -> dict:
    env_slug = _env_folder_slug()
    path = root / "backups" / env_slug / "cloud_sync_manifest.json"
    if not path.is_file():
        return {"version": 1, "uploaded": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    uploaded = data.get("uploaded")
    data["version"] = int(data.get("version", 1))
    data["uploaded"] = uploaded if isinstance(uploaded, dict) else {}
    return data


def _save_manifest(root: Path, data: dict) -> None:
    env_slug = _env_folder_slug()
    path = root / "backups" / env_slug / "cloud_sync_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _mtime_ns(stat: os.stat_result) -> int:
    raw = getattr(stat, "st_mtime_ns", None)
    if isinstance(raw, int):
        return raw
    return int(stat.st_mtime * 1_000_000_000)


def _needs_upload(stat: os.stat_result, entry: dict | None) -> bool:
    if not entry:
        return True
    try:
        if int(entry.get("mtime_ns", -2)) != _mtime_ns(stat):
            return True
        if int(entry.get("size", -2)) != int(stat.st_size):
            return True
    except (TypeError, ValueError):
        return True
    return False


def run_sync(root: Path | None = None, *, dry_run: bool = False, force_all: bool = False) -> int:
    root = root or repo_root()
    load_dotenv(root / ".env", override=False)
    env_slug = _env_folder_slug()
    hourly = root / "backups" / env_slug / "hourly"
    hourly.mkdir(parents=True, exist_ok=True)
    manifest = _load_manifest(root)
    uploaded_raw = manifest.setdefault("uploaded", {})
    uploaded: dict[str, object] = uploaded_raw if isinstance(uploaded_raw, dict) else {}

    manifest["uploaded"] = uploaded

    bucket = os.environ.get("S3_BUCKET_NAME", "").strip()
    if not bucket and not dry_run:
        print("Erro: S3_BUCKET_NAME ausente.", file=sys.stderr)
        return 2

    prefix = _prefix_norm(os.environ.get("S3_UPLOAD_PREFIX", ""))
    if not prefix:
        prefix = _prefix_norm(_default_upload_prefix(env_slug=env_slug, backup_kind="hourly"))

    bkey = None
    if not dry_run:
        try:
            bkey = parse_backup_key()
        except ValueError:
            print("Erro: BEABA_BACKUP_KEY obrigatório para encriptar cópias.", file=sys.stderr)
            return 2

    client = None
    if not dry_run:
        try:
            client = boto3_client()
        except Exception as exc:
            print(f"Erro boto3/cliente S3: {exc}", file=sys.stderr)
            return 1

    dbs = sorted(hourly.glob("beaba_gestao_*.db"))
    if not dbs:
        print("Sem ficheiros beaba_gestao_*.db em backups/hourly/.")
        return 0

    for db_path in dbs:
        name = db_path.name
        stat = db_path.stat()
        entry_raw = uploaded.get(name)
        entry = entry_raw if isinstance(entry_raw, dict) else None
        if isinstance(entry, dict) and force_all:
            entry = None
        if isinstance(entry, dict) and not _needs_upload(stat, entry):
            continue

        stem = db_path.stem
        remote_key = f"{prefix}{stem}.beaba.enc"

        if dry_run:
            print(f"[dry-run] {db_path.name} -> s3://{bucket or '<bucket>'}/{remote_key}")
            continue

        assert bkey is not None and client is not None

        fd, tmp_raw = tempfile.mkstemp(suffix=".beaba.enc")
        os.close(fd)
        tmp_path = Path(tmp_raw)
        try:
            encrypt_file(db_path, tmp_path, bkey)
            rsp = client.put_object(Bucket=bucket, Key=remote_key, Body=tmp_path.read_bytes())
            raw_etag = rsp.get("ETag")
            if isinstance(raw_etag, bytes):
                raw_etag = raw_etag.decode("utf-8", errors="replace")
            etag = str(raw_etag or "").strip('"')
            uploaded[name] = {
                "key": remote_key,
                "mtime_ns": _mtime_ns(stat),
                "size": int(stat.st_size),
                "etag": etag,
                "hostname": socket.gethostname(),
            }
            print(f"OK uploaded {remote_key} etag={etag}")
        except Exception as exc:
            print(f"Erro ao enviar {name}: {exc}", file=sys.stderr)
            _save_manifest(root, manifest)
            return 1
        finally:
            tmp_path.unlink(missing_ok=True)

    if dry_run:
        return 0
    _save_manifest(root, manifest)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Sincronizar backups/hourly/*.db para S3 (encriptados).")
    ap.add_argument("--dry-run", action="store_true", help="Planejar apenas; sem rede.")
    ap.add_argument("--force-all", action="store_true", help="Re-enviar todas as cópias .db mesmo que já registadas.")
    args = ap.parse_args()
    return run_sync(dry_run=args.dry_run, force_all=args.force_all)


if __name__ == "__main__":
    raise SystemExit(main())
