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


def _is_prod_env() -> bool:
    raw = (os.environ.get("BEABA_ENV") or os.environ.get("ENV_TYPE") or "").strip().lower()
    return raw in ("production", "prod", "main")


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


def sync_to_cloud_after_change() -> None:
    """
    Em ``BEABA_ENV=prod``, executa backup SQLite + sync S3 se passaram ≥120s desde o último envio.
    """
    if not _is_prod_env():
        return
    root = repo_root()
    if _within_debounce(root):
        return
    repo = str(root)
    py = sys.executable
    rc = _run_backup_cycle(repo, py)
    if rc == 0:
        _touch_stamp(root)


def notify_data_changed() -> None:
    """Alias para hooks nos módulos de domínio."""
    sync_to_cloud_after_change()
