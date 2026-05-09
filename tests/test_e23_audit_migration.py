"""Épico 23 Fase 1 — ``auditoria_sistema``, ``log_audit``, migração perfil ``colaborador`` → ``usuario``.

Também contrato mínimo de navegação para o perfil ``usuario`` (least privilege).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.database.connection import create_tables
from src.ui.shell_sidebar import _nav_items_para_perfil


def test_nav_usuario_mostra_so_home_vendas_cag_e_alias_colaborador() -> None:
    keys_u = [k for k, _ in _nav_items_para_perfil("usuario")]
    keys_c = [k for k, _ in _nav_items_para_perfil("colaborador")]
    assert keys_u == keys_c
    assert set(keys_u) == {"home", "vendas", "clientes_agendamentos"}
    adm = [k for k, _ in _nav_items_para_perfil("admin")]
    assert "governanca" in adm
    assert "catalogo" in adm


def test_log_audit_insere_auditoria_sistema(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db = tmp_path / "aud.db"
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(db))
    create_tables()
    from src.modules.audit import log_audit

    assert log_audit(
        "chef@bea.ba",
        "CREATE",
        "usuarios",
        registro_id="42",
        dados_novos={"email": "x@y.com"},
    )

    conn = sqlite3.connect(str(db))
    row = conn.execute(
        "SELECT ator_email, acao, modulo, registro_id, dados_novos FROM auditoria_sistema WHERE id = 1"
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "chef@bea.ba"
    assert row[1] == "CREATE"
    assert row[2] == "usuarios"
    assert row[3] == "42"
    assert '"x@y.com"' in str(row[4])


@pytest.mark.parametrize(
    ("has_prev_col",),
    [(True,), (False,)],
)
def test_migrate_usuarios_perfil_colaborador_para_usuario(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    has_prev_col: bool,
) -> None:
    db = tmp_path / "mig.db"
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(db))
    prev_line = ", senha_anterior_hash TEXT" if has_prev_col else ""
    cur_prev_ins = "'x'" if has_prev_col else ""

    conn = sqlite3.connect(str(db))
    c = conn.cursor()
    cols = """id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL{prev_line},
            perfil TEXT NOT NULL CHECK (perfil IN ('admin', 'colaborador')),
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            must_change_password INTEGER NOT NULL DEFAULT 1 CHECK (must_change_password IN (0, 1)),
            data_cadastro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"""

    cols = cols.format(prev_line=(prev_line or ""))
    c.execute(f"CREATE TABLE usuarios (\n            {cols}\n        )")
    ins_cols = (
        "nome, email, senha_hash, perfil, ativo, must_change_password"
        + (", senha_anterior_hash" if has_prev_col else "")
    )
    ins_vals = "('U', 'u@legacy.com', 'h', 'colaborador', 1, 1"
    ins_vals += (", " + cur_prev_ins) if has_prev_col else ""
    ins_vals += ")"
    c.execute(f"INSERT INTO usuarios ({ins_cols}) VALUES {ins_vals}")
    conn.commit()
    conn.close()

    create_tables()

    conn = sqlite3.connect(str(db))
    perfil = conn.execute("SELECT perfil FROM usuarios WHERE email='u@legacy.com'").fetchone()[0]
    ddl = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='usuarios'").fetchone()[0]
    info = [r[1] for r in conn.execute("PRAGMA table_info(usuarios)").fetchall()]
    has_anterior = int("senha_anterior_hash" in info)
    conn.close()

    assert str(perfil) == "usuario"
    assert has_anterior == 1
    assert "'usuario'" in (ddl or "")
    assert "'colaborador'" not in (ddl or "")
