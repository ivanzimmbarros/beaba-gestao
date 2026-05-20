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
            senha_anterior_hash TEXT,
            perfil TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1,
            must_change_password INTEGER NOT NULL DEFAULT 1,
            data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    c.execute(
        """
        CREATE TABLE mfa_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL,
            expira_em TIMESTAMP NOT NULL,
            usado INTEGER NOT NULL DEFAULT 0 CHECK (usado IN (0, 1)),
            FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE
        )
        """
    )
    c.execute(
        """
        CREATE TABLE auditoria_sistema (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ator_email TEXT,
            acao TEXT NOT NULL,
            modulo TEXT NOT NULL,
            registro_id TEXT,
            dados_antigos TEXT,
            dados_novos TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            senha_anterior_hash TEXT,
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

    assert auth_db.create_usuario("U", "u@u.com", "firstpwd1", "usuario") is None
    conn = sqlite3.connect(str(db))
    mcp, h = conn.execute(
        "SELECT must_change_password, senha_hash FROM usuarios WHERE email='u@u.com'"
    ).fetchone()
    conn.close()
    assert int(mcp) == 1
    assert verify_password("firstpwd1", h)


def test_update_password_rejeita_reutilizar_ultima_senha(auth_db_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(auth_db_path))
    from src.modules import auth_db

    assert auth_db.update_password_clear_must_change(1, "newpass999", current_password="initial123") is None
    msg = auth_db.update_password_clear_must_change(1, "initial123", current_password="newpass999")
    assert msg is not None
    assert "coincidir" in (msg or "").lower()

    assert auth_db.update_password_clear_must_change(1, "another999", current_password="newpass999") is None
    msg2 = auth_db.update_password_clear_must_change(1, "newpass999", current_password="another999")
    assert msg2 is not None


def test_update_password_trusted_post_mfa_sem_senha_actual(
    auth_db_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(auth_db_path))
    from src.modules import auth_db

    err = auth_db.update_password_clear_must_change(
        1, "trustedmfa888", trusted_post_mfa_must_change=True
    )
    assert err is None
    conn = sqlite3.connect(str(auth_db_path))
    row = conn.execute("SELECT senha_hash, must_change_password FROM usuarios WHERE id=1").fetchone()
    conn.close()
    assert row is not None
    assert int(row[1]) == 0
    assert verify_password("trustedmfa888", row[0])


def test_reset_password_to_temp_defines_must_change_and_audit(
    auth_db_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(auth_db_path))
    conn = sqlite3.connect(str(auth_db_path))
    conn.execute(
        "INSERT INTO usuarios (nome, email, senha_hash, perfil, ativo, must_change_password) "
        "VALUES (?,?,?,?,1,0)",
        ("R", "r@r.com", hash_password("beforeReset9"), "usuario"),
    )
    conn.commit()
    conn.close()

    from src.modules import auth_db

    plain = auth_db.reset_password_to_temp("r@r.com")
    assert plain is not None
    assert len(plain) == 12

    conn = sqlite3.connect(str(auth_db_path))
    mcp = int(conn.execute("SELECT must_change_password FROM usuarios WHERE email='r@r.com'").fetchone()[0])
    h = conn.execute("SELECT senha_hash FROM usuarios WHERE email='r@r.com'").fetchone()[0]
    aud = conn.execute(
        "SELECT acao, ator_email, registro_id FROM auditoria_sistema WHERE acao='PASSWORD_RESET_REQUESTED'"
    ).fetchone()
    conn.close()

    assert mcp == 1
    assert verify_password(plain, h)
    assert aud is not None
    assert aud[0] == "PASSWORD_RESET_REQUESTED"
    assert aud[1] == "sistema"


def test_reset_password_to_temp_email_desconhecido_retorna_sem_audit(
    auth_db_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(auth_db_path))
    from src.modules import auth_db

    assert auth_db.reset_password_to_temp("no-one@ghost.test") is None
    conn = sqlite3.connect(str(auth_db_path))
    n = conn.execute(
        "SELECT COUNT(*) FROM auditoria_sistema WHERE acao='PASSWORD_RESET_REQUESTED'"
    ).fetchone()[0]
    conn.close()
    assert int(n) == 0


def test_try_login_auditoria_login_success_e_falha(
    auth_db_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(auth_db_path))
    from src.modules import auth_db

    auth_db.try_login_credentials("t@t.com", "errada999")
    auth_db.try_login_credentials("t@t.com", "initial123")

    conn = sqlite3.connect(str(auth_db_path))
    rows = list(
        conn.execute(
            "SELECT acao FROM auditoria_sistema WHERE modulo='auth' AND ator_email='t@t.com' ORDER BY id"
        ).fetchall()
    )
    conn.close()
    assert len(rows) >= 2
    assert rows[-2][0] == "LOGIN_FAILED"
    assert rows[-1][0] == "LOGIN_SUCCESS"
