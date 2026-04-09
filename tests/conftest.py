"""Isolar SQLite em cada teste: não apagar nem usar `data/beaba_gestao.db` do ambiente local."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _pytest_sqlite_isolado(tmp_path, monkeypatch):
    db = tmp_path / "pytest_beaba.db"
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(db))
    from src.database.connection import create_tables

    create_tables()
