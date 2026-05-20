"""MFA — TTL 1 minuto, normalização de código, reenvio e mensagens de erro."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.modules.auth_db import (
    auth_code_ttl_seconds,
    issue_mfa_token,
    normalize_mfa_code,
    resend_mfa_code,
    reset_password_to_temp,
    try_login_credentials,
    validate_mfa_token,
)
from src.modules.auth_utils import hash_password


@pytest.fixture()
def auth_mfa_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db = tmp_path / "mfa.db"
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
            must_change_password INTEGER NOT NULL DEFAULT 0,
            credencial_temp_expira_em TEXT,
            data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE mfa_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL,
            expira_em TEXT NOT NULL,
            usado INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
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
    conn.execute(
        "INSERT INTO usuarios (nome, email, senha_hash, perfil, ativo, must_change_password) "
        "VALUES ('D','d@test.com',?, 'admin', 1, 0)",
        (hash_password("Secret123!"),),
    )
    conn.commit()
    conn.close()
    return db


def test_auth_code_ttl_is_sixty_seconds() -> None:
    assert auth_code_ttl_seconds() == 60


def test_normalize_mfa_code_accepts_spaced_digits() -> None:
    assert normalize_mfa_code("12 34 56") == "123456"
    assert normalize_mfa_code("000042") == "000042"


def test_validate_mfa_success_and_resend_invalidates_old(
    auth_mfa_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(auth_mfa_db))
    assert issue_mfa_token(1, "111111") is None
    assert validate_mfa_token(1, "111111") is None
    assert validate_mfa_token(1, "111111") == "Código expirado."

    code2, err = resend_mfa_code(1, "d@test.com")
    assert err is None and code2
    assert validate_mfa_token(1, code2) is None


def test_validate_mfa_expired_message(auth_mfa_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(auth_mfa_db))
    past = (datetime.now(timezone.utc) - timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn = sqlite3.connect(str(auth_mfa_db))
    conn.execute(
        "INSERT INTO mfa_tokens (user_id, token, expira_em, usado) VALUES (1,'999999',?,0)",
        (past,),
    )
    conn.commit()
    conn.close()
    assert validate_mfa_token(1, "999999") == "Código expirado."


def test_temp_password_expires_after_one_minute(auth_mfa_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(auth_mfa_db))
    temp = reset_password_to_temp("d@test.com")
    assert temp
    user, msg = try_login_credentials("d@test.com", temp)
    assert user is not None

    past = (datetime.now(timezone.utc) - timedelta(seconds=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn = sqlite3.connect(str(auth_mfa_db))
    conn.execute("UPDATE usuarios SET credencial_temp_expira_em = ? WHERE id = 1", (past,))
    conn.commit()
    conn.close()

    user2, msg2 = try_login_credentials("d@test.com", temp)
    assert user2 is None
    assert msg2 and "expirada" in msg2.lower()
