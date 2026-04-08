"""
E17 — Hot-backup horário SQLite: Backup API, PRAGMA quick_check no destino, rotação.

Variáveis de ambiente (opcionais):
  BEABA_REPO_ROOT      — raiz do repositório (defeito: pai de scripts/)
  BEABA_BACKUP_KEEP    — máximo de ficheiros em backups/hourly (defeito: 168)
  BEABA_BACKUP_CLOUD_QUEUE — "0" / "false" desliga cópia para backups/cloud_queue/
"""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_KEEP = 168

_logger = logging.getLogger("beaba.backup_hourly")


def repo_root() -> Path:
    override = os.environ.get("BEABA_REPO_ROOT")
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parents[1]


def _configure_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "backup_hourly.log"
    fmt = logging.Formatter("%(asctime)sZ %(levelname)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.INFO)
    root.addHandler(fh)
    root.addHandler(sh)


def _rotate_hourly(hourly: Path, keep: int) -> None:
    files = sorted(hourly.glob("beaba_gestao_*.db"), key=lambda p: p.name)
    while len(files) > keep:
        oldest = files.pop(0)
        try:
            oldest.unlink()
            _logger.info("Rotação: removido %s", oldest.name)
        except OSError as exc:
            _logger.warning("Rotação: não removido %s: %s", oldest, exc)


def run_backup(
    root: Path | None = None,
    keep: int | None = None,
    *,
    copy_to_cloud_queue: bool | None = None,
) -> int:
    root = root or repo_root()
    env_keep = os.environ.get("BEABA_BACKUP_KEEP")
    keep = int(env_keep) if env_keep is not None else (keep if keep is not None else DEFAULT_KEEP)

    if copy_to_cloud_queue is None:
        flag = os.environ.get("BEABA_BACKUP_CLOUD_QUEUE", "1").lower()
        copy_to_cloud_queue = flag not in ("0", "false", "no")

    data_db = root / "data" / "beaba_gestao.db"
    hourly = root / "backups" / "hourly"
    log_dir = root / "backups" / "logs"
    cloud_queue = root / "backups" / "cloud_queue"
    hourly.mkdir(parents=True, exist_ok=True)
    _configure_logging(log_dir)

    if not data_db.is_file():
        _logger.error("Fonte inexistente: %s", data_db)
        return 1

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    dest = hourly / f"beaba_gestao_{ts}.db"

    try:
        src_uri = f"file:{data_db.resolve().as_posix()}?mode=ro"
        source = sqlite3.connect(src_uri, uri=True, timeout=60.0)
    except sqlite3.Error as exc:
        _logger.error("Abrir origem RO falhou: %s", exc)
        return 1

    try:
        dest_conn = sqlite3.connect(dest)
        try:
            source.backup(dest_conn)
        finally:
            dest_conn.close()
    except sqlite3.Error as exc:
        _logger.error("Backup API falhou: %s", exc)
        dest.unlink(missing_ok=True)
        return 1
    finally:
        source.close()

    try:
        qc_conn = sqlite3.connect(dest)
        try:
            row = qc_conn.execute("PRAGMA quick_check").fetchone()
            qresult = row[0] if row else ""
        finally:
            qc_conn.close()
    except sqlite3.Error as exc:
        _logger.error("quick_check falhou: %s", exc)
        dest.unlink(missing_ok=True)
        return 1

    if qresult != "ok":
        _logger.error("quick_check não ok: %s", qresult)
        dest.unlink(missing_ok=True)
        return 1

    _logger.info("Backup criado: %s", dest.name)
    _rotate_hourly(hourly, keep)

    if copy_to_cloud_queue:
        cloud_queue.mkdir(parents=True, exist_ok=True)
        try:
            cq_dest = cloud_queue / dest.name
            shutil.copy2(dest, cq_dest)
            _logger.info("Cópia para cloud_queue: %s", cq_dest.name)
        except OSError as exc:
            _logger.warning("cloud_queue: cópia falhou: %s", exc)

    return 0


def main() -> int:
    return run_backup()


if __name__ == "__main__":
    sys.exit(main())
