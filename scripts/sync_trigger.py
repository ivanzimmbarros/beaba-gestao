"""
Gatilho pós-escrita: backup horário + sync cloud em produção (com debounce).

Chamado pelos módulos de domínio após save/update/delete bem-sucedidos.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

_DEBOUNCE_SECONDS = 120
_STAMP_NAME = ".last_cloud_sync_trigger"


def repo_root() -> Path:
    raw = os.environ.get("BEABA_REPO_ROOT", "").strip()
    if raw:
        return Path(raw).resolve()
    return Path(__file__).resolve().parents[1]


def _stamp_path(root: Path) -> Path:
    return root / "data" / _STAMP_NAME


def _is_streamlit_runtime() -> bool:
    return bool(os.environ.get("STREAMLIT_RUNTIME_ENV") or os.environ.get("STREAMLIT_SERVER_PORT"))


def _cloud_bucket_configured() -> bool:
    return bool((os.environ.get("S3_BUCKET_NAME") or "").strip())


def _should_sync_to_cloud() -> bool:
    """Produção/staging ou qualquer deploy Streamlit com bucket S3 configurado."""
    if not _cloud_bucket_configured():
        return False
    try:
        from src.database.connection import hydrate_beaba_runtime_env

        hydrate_beaba_runtime_env()
    except Exception:
        pass
    raw = (os.environ.get("BEABA_ENV") or os.environ.get("ENV_TYPE") or "").strip().lower()
    if raw in ("production", "prod", "main", "staging", "stg"):
        return True
    return _is_streamlit_runtime()


def _within_debounce(root: Path) -> bool:
    stamp = _stamp_path(root)
    if not stamp.is_file():
        return False
    try:
        age = time.time() - stamp.stat().st_mtime
    except OSError:
        return False
    return age < _DEBOUNCE_SECONDS


def _touch_stamp(root: Path) -> None:
    stamp = _stamp_path(root)
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text(str(time.time()), encoding="utf-8")


def _run_backup_cycle(repo: str, py: str) -> int:
    hourly = subprocess.run(
        [py, str(Path(repo) / "scripts" / "backup_sqlite_hourly.py")],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if hourly.returncode != 0:
        return hourly.returncode
    sync = subprocess.run(
        [py, str(Path(repo) / "scripts" / "backup_sync_cloud.py")],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return sync.returncode


def sync_to_cloud_after_change(*, force: bool = False) -> None:
    """
    Com bucket S3 configurado (prod/staging/Streamlit Cloud), backup SQLite + sync R2/S3.

    ``force=True`` ignora o debounce de 120s (senhas e utilizadores).
    """
    if not _should_sync_to_cloud():
        return
    root = repo_root()
    if not force and _within_debounce(root):
        return
    repo = str(root)
    py = sys.executable
    rc = _run_backup_cycle(repo, py)
    if rc == 0:
        _touch_stamp(root)


def notify_data_changed() -> None:
    """Alias para hooks nos módulos de domínio."""
    sync_to_cloud_after_change()


def notify_auth_data_changed() -> None:
    """Credenciais/utilizadores — backup imediato para sobreviver a reboot do Streamlit Cloud."""
    sync_to_cloud_after_change(force=True)
