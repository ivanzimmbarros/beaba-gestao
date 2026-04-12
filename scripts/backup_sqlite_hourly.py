"""
E17 / E19.1 — Hot-backup horário SQLite: Backup API (cópia integral do ficheiro, todas as
tabelas incluindo E18 ledger/repasse e E19 `dw_*`), verificação de integridade no destino,
rotação.

Variáveis de ambiente (opcionais):
  BEABA_REPO_ROOT      — raiz do repositório (defeito: pai de scripts/)
  BEABA_BACKUP_KEEP    — máximo de ficheiros em backups/hourly (defeito: 168)
  BEABA_BACKUP_CLOUD_QUEUE — "0" / "false" desliga cópia para backups/cloud_queue/
  BEABA_BACKUP_INTEGRITY_FULL — "1" / "true" para PRAGMA integrity_check no destino (mais lento)

Arquitectura UI (2026-04-12): removidos `src/ui/page_clientes.py` e `page_agendamentos.py`;
a área operacional única é `page_clientes_agendamentos.py` (registo de governação / PAINEL).
"""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.sqlite_backup_verify import verify_backup_destination  # noqa: E402

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

    ok_v, msg_v = verify_backup_destination(dest)
    if not ok_v:
        _logger.error("Verificação pós-backup falhou: %s", msg_v)
        dest.unlink(missing_ok=True)
        return 1

    _logger.info("Backup criado e verificado (header + pragma): %s", dest.name)
    _rotate_hourly(hourly, keep)

    if copy_to_cloud_queue:
        cloud_queue.mkdir(parents=True, exist_ok=True)
        try:
            cq_dest = cloud_queue / dest.name
            shutil.copy2(dest, cq_dest)
            ok_cq, msg_cq = verify_backup_destination(cq_dest)
            if not ok_cq:
                _logger.error("cloud_queue: cópia corrompida ou inválida — removida: %s", msg_cq)
                cq_dest.unlink(missing_ok=True)
            else:
                _logger.info("Cópia para cloud_queue verificada: %s", cq_dest.name)
        except OSError as exc:
            _logger.warning("cloud_queue: cópia falhou: %s", exc)

    return 0


def main() -> int:
    return run_backup()


if __name__ == "__main__":
    sys.exit(main())
