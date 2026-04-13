"""
E17 — Verificação semanal: copia a última cópia horária para staging, PRAGMA integrity_check
e foreign_key_check, remove staging. Não altera data/beaba_gestao.db.

Variáveis de ambiente (opcionais):
  BEABA_REPO_ROOT — raiz do repositório (defeito: pai de scripts/)

Arquitectura UI (2026-04-12): decomissionamento de `page_clientes.py` e `page_agendamentos.py`;
UI consolidada em `page_clientes_agendamentos.py` (PAINEL / JSON). Setor 4 CAG (lista no expander
«Agendamentos»): regressão em `tests/cag_setor4_ui_contract.py` e suites pytest associadas.
Painel de Vendas: `tests/vnd_ui_contract.py` / `tests/test_vnd_visual_sereno.py`.
"""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

_logger = logging.getLogger("beaba.verify_restore_weekly")


def repo_root() -> Path:
    override = os.environ.get("BEABA_REPO_ROOT")
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parents[1]


def _configure_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "restore_weekly.log"
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


def run_verify(root: Path | None = None) -> int:
    root = root or repo_root()
    hourly = root / "backups" / "hourly"
    staging_dir = root / "backups" / "restore_verify"
    log_dir = root / "backups" / "logs"
    staging_dir.mkdir(parents=True, exist_ok=True)
    _configure_logging(log_dir)

    candidates = sorted(hourly.glob("beaba_gestao_*.db"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        _logger.error("Nenhum backup em %s", hourly)
        return 1

    latest = candidates[-1]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    staging = staging_dir / f"staging_{ts}.db"

    try:
        shutil.copy2(latest, staging)
    except OSError as exc:
        _logger.error("Cópia para staging falhou: %s", exc)
        return 1

    code = 1
    try:
        conn = sqlite3.connect(staging)
        try:
            ic_row = conn.execute("PRAGMA integrity_check").fetchone()
            ic = ic_row[0] if ic_row else ""
            fk_bad = conn.execute("PRAGMA foreign_key_check").fetchall()
        finally:
            conn.close()

        if ic != "ok":
            _logger.error("integrity_check falhou: %s", ic)
        elif fk_bad:
            _logger.error("foreign_key_check: %s linhas com violação", len(fk_bad))
        else:
            _logger.info("OK — verificada cópia %s (staging removido após teste)", latest.name)
            code = 0
    except sqlite3.Error as exc:
        _logger.error("SQLite ao verificar staging: %s", exc)
    finally:
        staging.unlink(missing_ok=True)

    return code


def main() -> int:
    return run_verify()


if __name__ == "__main__":
    sys.exit(main())
