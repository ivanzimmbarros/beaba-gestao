"""must_change_password + troca obrigatória (auth_db / esquema)."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from src.modules.auth_utils import hash_password, verify_password


@pytest.fixture()
def auth_db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db = tmp_path / "auth_t.db"
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(db))
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL,
            perfil TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1,
            must_change_password INTEGER NOT NULL DEFAULT 1,
            data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    c.execute(
        "INSERT INTO usuarios (nome, email, senha_hash, perfil, ativo, must_change_password) VALUES (?,?,?,?,1,1)",
        ("T", "t@t.com", hash_password("initial123"), "admin"),
    )
    conn.commit()
    conn.close()
    return db


def test_update_password_clear_must_change_requires_current_when_flag_set(
    auth_db_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(auth_db_path))
    from src.modules import auth_db

    err = auth_db.update_password_clear_must_change(1, "newpass999", current_password=None)
    assert err is not None

    err2 = auth_db.update_password_clear_must_change(1, "short", current_password="initial123")
    assert err2 is not None

    err3 = auth_db.update_password_clear_must_change(1, "initial123", current_password="initial123")
    assert err3 is not None

    assert auth_db.update_password_clear_must_change(1, "newpass999", current_password="initial123") is None

    conn = sqlite3.connect(str(auth_db_path))
    row = conn.execute("SELECT senha_hash, must_change_password FROM usuarios WHERE id=1").fetchone()
    conn.close()
    assert row is not None
    assert int(row[1]) == 0
    assert verify_password("newpass999", row[0])


def test_create_usuario_sets_must_change(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    db = tmp_path / "c.db"
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(db))
    conn = sqlite3.connect(str(db))
    conn.execute(
        """
        CREATE TABLE usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL,
            perfil TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1,
            must_change_password INTEGER NOT NULL DEFAULT 1,
            data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()

    from src.modules import auth_db

    assert auth_db.create_usuario("U", "u@u.com", "firstpwd1", "colaborador") is None
    conn = sqlite3.connect(str(db))
    mcp, h = conn.execute(
        "SELECT must_change_password, senha_hash FROM usuarios WHERE email='u@u.com'"
    ).fetchone()
    conn.close()
    assert int(mcp) == 1
    assert verify_password("firstpwd1", h)
