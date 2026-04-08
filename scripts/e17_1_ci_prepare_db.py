"""E17.1 — Garante SQLite mínimo em CI (runner sem data/ pré-existente)."""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path


def prepare(repo: Path) -> bool:
    """
    Se GITHUB_ACTIONS e BEABA_CI_PREPARE_EMPTY_DB=1 e não existe data/beaba_gestao.db,
    cria base mínima (_ci_placeholder).
    Retorna True se criou ou já existia fonte utilizável.
    """
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return True
    if os.environ.get("BEABA_CI_PREPARE_EMPTY_DB", "1") != "1":
        return True
    db = repo / "data" / "beaba_gestao.db"
    if db.is_file():
        return True
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE IF NOT EXISTS _ci_placeholder (x INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()
    return True


def main() -> int:
    root = Path(os.environ.get("GITHUB_WORKSPACE") or os.environ.get("BEABA_REPO_ROOT", ".")).resolve()
    prepare(root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
