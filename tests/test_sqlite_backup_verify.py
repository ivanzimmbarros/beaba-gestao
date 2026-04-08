"""Smoke: verificação de header e PRAGMA pós-backup (E19.1)."""

import sqlite3
import tempfile
from pathlib import Path

from scripts.sqlite_backup_verify import (
    verify_backup_destination,
    verify_sqlite_magic_header,
)


def test_header_rejects_garbage():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as fh:
        fh.write(b"not sqlite")
        bad = Path(fh.name)
    try:
        ok, msg = verify_sqlite_magic_header(bad)
        assert ok is False
        assert "inválido" in msg or "SQLite" in msg
    finally:
        bad.unlink(missing_ok=True)


def test_verify_backup_destination_on_minimal_db():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.db"
        conn = sqlite3.connect(p)
        conn.execute("CREATE TABLE x(i INTEGER)")
        conn.commit()
        conn.close()
        ok, msg = verify_backup_destination(p)
        assert ok is True
        assert msg == "ok"
