"""Gestão de utilizadores (épico E23 — ``usuarios_db``)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.modules.auth_utils import hash_password, verify_password


def _schema_base() -> str:
    return """
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
        );
        CREATE TABLE auditoria_sistema (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ator_email TEXT,
            acao TEXT NOT NULL,
            modulo TEXT NOT NULL,
            registro_id TEXT,
            dados_antigos TEXT,
            dados_novos TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """


@pytest.fixture()
def uso_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db = tmp_path / "uso.db"
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(db))
    conn = sqlite3.connect(str(db))
    conn.executescript(_schema_base())
    conn.execute(
        "INSERT INTO usuarios (nome, email, senha_hash, perfil, ativo, must_change_password) "
        "VALUES (?,?,?,?,1,0), (?,?,?,?,1,1)",
        (
            "Alpha",
            "alfa@bea.pt",
            hash_password("seed12ab"),
            "admin",
            "Beta",
            "beta@bea.pt",
            hash_password("seed12bb"),
            "usuario",
        ),
    )
    conn.commit()
    conn.close()
    return db


def test_listar_sem_senha_hash(uso_db: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(uso_db))
    from src.modules import usuarios_db

    rows = usuarios_db.listar_usuarios()
    assert len(rows) == 2
    for r in rows:
        assert "senha_hash" not in r


def test_cria_com_senha_padrao_audit_e_duplicidade(
    uso_db: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(uso_db))
    from src.modules import usuarios_db

    nid = usuarios_db.criar_usuario("Novo", " novo@bea.pt ", "usuario", "alfa@bea.pt")
    assert nid == 3
    pwd = usuarios_db.senha_padrao_inicial()
    conn = sqlite3.connect(str(uso_db))
    h = conn.execute("SELECT senha_hash, must_change_password FROM usuarios WHERE id=3").fetchone()
    n_aud = conn.execute(
        "SELECT COUNT(*) FROM auditoria_sistema WHERE acao='CREATE' AND modulo='usuarios'"
    ).fetchone()[0]
    conn.close()
    assert verify_password(pwd, h[0])
    assert int(h[1]) == 1
    assert int(n_aud) >= 1

    with pytest.raises(ValueError, match="já está cadastrado"):
        usuarios_db.criar_usuario("X", "novo@bea.pt", "admin", "alfa@bea.pt")


def test_atualizar_perfil_audit(uso_db: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(uso_db))
    from src.modules import usuarios_db

    assert usuarios_db.atualizar_perfil(2, "admin", "alfa@bea.pt")
    conn = sqlite3.connect(str(uso_db))
    assert conn.execute("SELECT perfil FROM usuarios WHERE id=2").fetchone()[0] == "admin"
    n_up = conn.execute(
        "SELECT COUNT(*) FROM auditoria_sistema WHERE acao='UPDATE' AND modulo='usuarios'"
    ).fetchone()[0]
    conn.close()
    assert int(n_up) >= 1


def test_alternar_ativo_audit(uso_db: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(uso_db))
    from src.modules import usuarios_db

    assert usuarios_db.alternar_status_ativo(2, 0, "alfa@bea.pt")
    conn = sqlite3.connect(str(uso_db))
    assert int(conn.execute("SELECT ativo FROM usuarios WHERE id=2").fetchone()[0]) == 0
    conn.close()
