"""Consulta ``listar_auditoria`` (Épico 23 Fase 4)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.database.connection import create_tables


def _insert_row(
    conn: sqlite3.Connection,
    *,
    modulo: str,
    acao: str,
    criado_em: str,
    registro_id: str = "1",
) -> None:
    conn.execute(
        """
        INSERT INTO auditoria_sistema (
            ator_email, acao, modulo, registro_id, dados_antigos, dados_novos, criado_em
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "chef@bea.ba",
            acao,
            modulo,
            registro_id,
            '{"old": true}',
            '{"new": false}',
            criado_em,
        ),
    )
    conn.commit()


def test_listar_auditoria_ordem_desc_e_modulo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db = tmp_path / "aud_list.db"
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(db))
    create_tables()

    conn = sqlite3.connect(str(db))
    _insert_row(conn, modulo="usuarios", acao="FIRST", criado_em="2025-06-01 12:00:00")
    _insert_row(conn, modulo="auth", acao="NEWER_AUTH", criado_em="2025-06-03 09:30:05")
    _insert_row(conn, modulo="usuarios", acao="MID", criado_em="2025-06-02 15:00:00")
    conn.close()

    from src.modules.audit import listar_auditoria

    all_rows = listar_auditoria(limite=100)
    assert [r["acao"] for r in all_rows][:3] == ["NEWER_AUTH", "MID", "FIRST"]

    auth_only = listar_auditoria(limite=50, modulo_filtro="auth")
    assert len(auth_only) == 1 and auth_only[0]["acao"] == "NEWER_AUTH" and auth_only[0]["modulo"] == "auth"

    u_only = listar_auditoria(limite=50, modulo_filtro="usuarios")
    assert len(u_only) == 2


def test_listar_auditoria_dados_antigos_e_novos_sao_strings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db = tmp_path / "aud_str.db"
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(db))
    create_tables()
    conn = sqlite3.connect(str(db))
    _insert_row(conn, modulo="usuarios", acao="X", criado_em="2025-01-01 00:00:00")
    conn.close()

    from src.modules.audit import listar_auditoria

    r = listar_auditoria(limite=1)[0]
    assert isinstance(r["dados_antigos"], str) and '{"old": true}' in r["dados_antigos"]
    assert isinstance(r["dados_novos"], str)


def test_criado_em_exibicao_pt_format(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db = tmp_path / "aud_fmt.db"
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(db))
    create_tables()
    conn = sqlite3.connect(str(db))
    _insert_row(conn, modulo="auth", acao="L", criado_em="2025-11-08 07:41:59")
    conn.close()

    from src.modules.audit import listar_auditoria

    r = listar_auditoria(limite=1)[0]
    assert r["criado_em_exibicao_pt"] == "08/11/2025 07:41"
