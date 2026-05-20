"""
Arranque Web (Streamlit Cloud / local): garante ``data/beaba_gestao.db`` e artefactos de governança.

Se o SQLite operacional não existir, descarrega o backup encriptado mais recente do R2/S3,
decripta e repõe ``cloud_sync_manifest.json`` e ``staging_restore_drill_state.json`` quando
disponíveis no bucket (prefixo ``{env}/state/``).

Credenciais: ``st.secrets`` no Streamlit Cloud (chaves planas) ou ``.env`` local.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.backup_sync_cloud import (  # noqa: E402
    _default_upload_prefix,
    _env_folder_slug,
    _prefix_norm,
    boto3_client,
    repo_root,
)
from scripts.e17_1_crypto import decrypt_file, parse_backup_key  # noqa: E402
from scripts.sqlite_backup_verify import verify_backup_destination  # noqa: E402

DRILL_REL = Path("docs") / "governanca" / "telemetry" / "staging_restore_drill_state.json"
MANIFEST_NAME = "cloud_sync_manifest.json"

ALERT_NETWORK_NO_BOOT_BLOCK = (
    "⚠️ [WEB STARTUP] Sem ligação à nuvem — o sistema arranca com base vazia. "
    "Quando a rede voltar, restaure a cópia mais recente ou aguarde o próximo sync."
)

ALERT_NO_REMOTE_BACKUP_YET = (
    "⚠️ Ainda não há cópia encriptada no R2/S3 (ou o prefixo está incorrecto). "
    "A app arranca com base vazia; após login e alterações, o backup automático guardará na nuvem."
)

_REQUIRED_CLOUD_KEYS = (
    "S3_BUCKET_NAME",
    "S3_ACCESS_KEY",
    "S3_SECRET_KEY",
    "S3_ENDPOINT_URL",
    "BEABA_BACKUP_KEY",
)

_SECRET_KEYS = (
    "S3_ACCESS_KEY",
    "S3_SECRET_KEY",
    "S3_ENDPOINT_URL",
    "S3_BUCKET_NAME",
    "S3_REGION",
    "S3_UPLOAD_PREFIX",
    "BEABA_BACKUP_KEY",
    "ENV_TYPE",
    "BEABA_ENV",
)


def _emit(message: str, *, err: bool = False) -> None:
    stream = sys.stderr if err else sys.stdout
    try:
        print(message, file=stream, flush=True)
    except UnicodeEncodeError:
        buf = getattr(stream, "buffer", None)
        line = message + "\n"
        if buf is not None:
            buf.write(line.encode("utf-8", errors="replace"))
            buf.flush()


def _is_streamlit_runtime() -> bool:
    return bool(os.environ.get("STREAMLIT_RUNTIME_ENV") or os.environ.get("STREAMLIT_SERVER_PORT"))


def missing_cloud_secret_keys() -> list[str]:
    """Chaves planas em falta (Secrets Streamlit ou ``.env``) para arranque cloud."""
    _hydrate_config()
    try:
        from src.database.connection import hydrate_beaba_runtime_env

        hydrate_beaba_runtime_env(force=True)
    except Exception:
        pass
    return [k for k in _REQUIRED_CLOUD_KEYS if not (os.environ.get(k) or "").strip()]


def _hydrate_config() -> None:
    """Carrega ``.env`` local e, no Cloud, ``st.secrets`` por cima."""
    from dotenv import load_dotenv

    root = repo_root()
    load_dotenv(root / ".env", override=False)
    if not _is_streamlit_runtime():
        return
    try:
        import streamlit as st

        secrets = getattr(st, "secrets", None)
        if secrets is None:
            return
        for key in _SECRET_KEYS:
            try:
                val = secrets[key]
            except (KeyError, TypeError):
                continue
            if val is not None and str(val).strip():
                os.environ[key] = str(val).strip()
    except Exception:
        pass


def _upload_prefix() -> str:
    env_slug = _env_folder_slug()
    prefix = _prefix_norm(os.environ.get("S3_UPLOAD_PREFIX", ""))
    if not prefix:
        prefix = _prefix_norm(_default_upload_prefix(env_slug=env_slug, backup_kind="hourly"))
    return prefix


def _state_keys(env_slug: str) -> tuple[str, str]:
    return (
        f"{env_slug}/state/{MANIFEST_NAME}",
        f"{env_slug}/state/staging_restore_drill_state.json",
    )


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


def _download_object(client, bucket: str, key: str, dest: Path) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=key)
    except Exception:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    client.download_file(bucket, key, str(dest))
    return dest.is_file()


def _restore_state_files(repo: Path, client, bucket: str, env_slug: str) -> None:
    manifest_key, drill_key = _state_keys(env_slug)
    local_manifest = repo / "backups" / env_slug / MANIFEST_NAME
    local_drill = repo / DRILL_REL
    if _download_object(client, bucket, manifest_key, local_manifest):
        _emit(f"ℹ️ [WEB STARTUP] Manifesto cloud reposto ({local_manifest.name}).")
    if _download_object(client, bucket, drill_key, local_drill):
        _emit(f"ℹ️ [WEB STARTUP] Estado do drill reposto ({local_drill.name}).")


def _is_network_error(exc: BaseException) -> bool:
    if isinstance(exc, (OSError, ConnectionError)):
        return True
    name = type(exc).__name__
    return name in (
        "EndpointConnectionError",
        "ConnectTimeoutError",
        "ReadTimeoutError",
        "ConnectionClosedError",
        "NewConnectionError",
    )


def _sqlite_operational_data_missing(db_path: Path) -> bool:
    """True quando o SQLite não tem dados utilizáveis (precisa restore da nuvem).

    Ambientes de teste pós-wipe têm ``clientes=0`` mas ``usuarios`` activos — **não**
    devem ser substituídos no arranque/re-run do Streamlit (apagaria tokens MFA e senhas).
    """
    if not db_path.is_file():
        return True
    try:
        if db_path.stat().st_size == 0:
            return True
    except OSError:
        return True
    import sqlite3

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.Error:
        return True
    try:
        cur = conn.cursor()
        tabs = {
            r[0]
            for r in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "usuarios" in tabs:
            cur.execute("SELECT COUNT(*) FROM usuarios WHERE ativo = 1")
            if int(cur.fetchone()[0] or 0) > 0:
                return False
        if "mfa_tokens" in tabs:
            cur.execute(
                "SELECT COUNT(*) FROM mfa_tokens WHERE usado = 0"
            )
            if int(cur.fetchone()[0] or 0) > 0:
                return False
        if "clientes" not in tabs:
            return True
        cur.execute("SELECT COUNT(*) FROM clientes")
        row = cur.fetchone()
        return int(row[0] if row else 0) == 0
    except sqlite3.Error:
        return True
    finally:
        conn.close()


def _local_db_ready(db_path: Path) -> bool:
    return db_path.is_file() and db_path.stat().st_size > 0 and not _sqlite_operational_data_missing(
        db_path
    )


def ensure_web_environment_status(repo: Path | None = None) -> tuple[bool, str | None]:
    """
    Garante ambiente para ``create_tables()`` / UI.

    Retorna ``(ready, alerta_gestor)``. ``ready=False`` bloqueia arranque; ``alerta`` é aviso não fatal.
    """
    root = repo or repo_root()
    os.environ.setdefault("BEABA_REPO_ROOT", str(root))
    _hydrate_config()
    try:
        from src.database.connection import hydrate_beaba_runtime_env

        hydrate_beaba_runtime_env(force=True)
    except Exception:
        pass

    db_path = root / "data" / "beaba_gestao.db"

    if _local_db_ready(db_path):
        return True, None

    if _sqlite_operational_data_missing(db_path) and _is_streamlit_runtime():
        _emit(
            "ℹ️ [WEB STARTUP] Base local vazia ou só bootstrap — a tentar cópia na nuvem..."
        )

    bucket = (os.environ.get("S3_BUCKET_NAME") or "").strip()
    if not bucket:
        if _is_streamlit_runtime():
            _emit(
                "❌ [WEB STARTUP] Base de dados ausente e credenciais cloud não configuradas "
                "(defina Secrets no Streamlit Cloud).",
                err=True,
            )
            return False, None
        _emit(
            "ℹ️ [WEB STARTUP] Sem credenciais cloud — o sistema criará uma base local vazia."
        )
        return True, None

    _emit(
        "🛠️ [WEB STARTUP] Restaurando ambiente a partir da cópia mais recente na nuvem..."
    )

    try:
        client = boto3_client()
        key = parse_backup_key()
    except Exception as exc:
        if _is_network_error(exc):
            _emit(f"❌ [WEB STARTUP] {exc}", err=True)
            return True, ALERT_NETWORK_NO_BOOT_BLOCK
        _emit(f"❌ [WEB STARTUP] Configuração inválida: {exc}", err=True)
        return False, None

    prefix = _upload_prefix()
    try:
        remote_key = _latest_enc_key(bucket, prefix, client)
    except Exception as exc:
        if _is_network_error(exc):
            _emit(f"❌ [WEB STARTUP] {exc}", err=True)
            return True, ALERT_NETWORK_NO_BOOT_BLOCK
        raise

    if not remote_key:
        _emit(
            f"❌ [WEB STARTUP] Nenhum backup encriptado em s3://{bucket}/{prefix}",
            err=True,
        )
        if _is_streamlit_runtime():
            return True, ALERT_NO_REMOTE_BACKUP_YET
        return False, None

    env_slug = _env_folder_slug()
    work = root / "backups" / env_slug / "web_startup"
    work.mkdir(parents=True, exist_ok=True)
    enc_local = work / "latest.beaba.enc"
    dec_local = work / "restored.db"

    try:
        client.download_file(bucket, remote_key, str(enc_local))
        decrypt_file(enc_local, dec_local, key)
        ok, msg = verify_backup_destination(dec_local)
        if not ok:
            _emit(f"❌ [WEB STARTUP] Cópia inválida após decriptação: {msg}", err=True)
            return False, None

        db_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = db_path.parent / f".beaba_web_startup_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.db"
        shutil.copy2(dec_local, tmp)
        os.replace(tmp, db_path)

        hourly = root / "backups" / env_slug / "hourly"
        hourly.mkdir(parents=True, exist_ok=True)
        shutil.copy2(
            dec_local,
            hourly
            / f"beaba_gestao_web_startup_{remote_key.split('/')[-1].replace('.beaba.enc', '')}.db",
        )

        _restore_state_files(root, client, bucket, env_slug)
    except Exception as exc:
        _emit(f"❌ [WEB STARTUP] Falha na restauração: {exc}", err=True)
        if _is_network_error(exc):
            return True, ALERT_NETWORK_NO_BOOT_BLOCK
        return False, None
    finally:
        shutil.rmtree(work, ignore_errors=True)

    _emit("✅ [WEB STARTUP] Pronto.")
    return True, None


def ensure_web_environment(repo: Path | None = None) -> bool:
    """Compatibilidade CLI — apenas o booleano ``ready``."""
    ready, _ = ensure_web_environment_status(repo)
    return ready


def main() -> int:
    return 0 if ensure_web_environment() else 1


if __name__ == "__main__":
    raise SystemExit(main())
