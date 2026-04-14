"""Lançamentos operacionais — parsing e intersecção hierárquica."""

from __future__ import annotations

import sqlite3

import pytest

from src.database.connection import create_tables, get_connection
from src.modules.financeiro_categorias_gasto import salvar_linha1_tres_textos
from src.modules.financeiro_lancamentos_gasto import (
    inserir_lancamentos_operacionais,
    listar_lancamentos_controle,
    parse_data_dd_mm_yyyy,
    parse_valor_euro,
    tipos_gasto_coerentes_com_seleccao,
)


@pytest.fixture()
def fin_conn(tmp_path, monkeypatch):
    db = tmp_path / "fin_lanc.db"
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(db))
    create_tables()
    c = get_connection()
    assert c is not None
    yield c
    c.close()


def test_parse_valor_euro() -> None:
    assert parse_valor_euro("12,50") == 1250
    assert parse_valor_euro("  1.234,56 €") == 123456
    assert parse_valor_euro("") is None


def test_parse_data_dd_mm_yyyy() -> None:
    assert parse_data_dd_mm_yyyy("31/01/2026") == "2026-01-31"
    assert parse_data_dd_mm_yyyy("32/01/2026") is None
    assert parse_data_dd_mm_yyyy("") is None


def test_tipos_coerentes_vazio_se_eixo_falta(fin_conn: sqlite3.Connection) -> None:
    salvar_linha1_tres_textos(fin_conn, "C", "N", "T")
    fin_conn.commit()
    cur = fin_conn.execute(
        "SELECT c.id, n.id, t.id FROM financeiro_tipo_gasto t "
        "JOIN financeiro_natureza n ON n.id = t.natureza_id "
        "JOIN financeiro_centro_custo c ON c.id = n.centro_custo_id WHERE t.ativo = 1"
    ).fetchone()
    assert cur is not None
    cid, nid, tid = int(cur[0]), int(cur[1]), int(cur[2])
    assert tipos_gasto_coerentes_com_seleccao(fin_conn, centro_ids=[], natureza_ids=[nid], tipo_ids=[tid]) == []
    assert tipos_gasto_coerentes_com_seleccao(fin_conn, centro_ids=[cid], natureza_ids=[nid], tipo_ids=[tid]) == [tid]


def test_inserir_um_mes(fin_conn: sqlite3.Connection) -> None:
    salvar_linha1_tres_textos(fin_conn, "C2", "N2", "T2")
    fin_conn.commit()
    cur = fin_conn.execute(
        "SELECT t.id FROM financeiro_tipo_gasto t "
        "JOIN financeiro_natureza n ON n.id = t.natureza_id "
        "JOIN financeiro_centro_custo c ON c.id = n.centro_custo_id WHERE t.nome = 'T2'"
    ).fetchone()
    assert cur is not None
    tid = int(cur[0])
    n, err = inserir_lancamentos_operacionais(
        fin_conn,
        [tid],
        valor_centavos=500,
        data_competencia_iso="2026-04-15",
        status_lancamento="Agendado",
        classe_lancamento="real",
        replicar=False,
        meses_duracao=3,
    )
    assert not err
    assert n == 1
    fin_conn.commit()
    cnt = fin_conn.execute("SELECT COUNT(*) FROM financeiro_gasto_lancamentos WHERE tipo_gasto_id = ?", (tid,)).fetchone()[0]
    assert int(cnt) == 1
    row = fin_conn.execute(
        "SELECT data_competencia, data_pagamento, data_criacao_registo FROM financeiro_gasto_lancamentos WHERE tipo_gasto_id = ?",
        (tid,),
    ).fetchone()
    assert row is not None
    assert row[0] == "2026-04-15"
    assert row[1] == "2026-04-15"
    assert isinstance(row[2], str) and len(str(row[2])) >= 10


def test_listar_lancamentos_controle(fin_conn: sqlite3.Connection) -> None:
    salvar_linha1_tres_textos(fin_conn, "Cx", "Nx", "Tx")
    fin_conn.commit()
    tid = int(
        fin_conn.execute(
            "SELECT t.id FROM financeiro_tipo_gasto t JOIN financeiro_natureza n ON n.id = t.natureza_id WHERE t.nome = 'Tx'"
        ).fetchone()[0]
    )
    inserir_lancamentos_operacionais(
        fin_conn,
        [tid],
        valor_centavos=200,
        data_competencia_iso="2026-06-10",
        status_lancamento="Agendado",
        classe_lancamento="meta",
        replicar=False,
        meses_duracao=1,
    )
    fin_conn.commit()
    rows = listar_lancamentos_controle(fin_conn)
    assert len(rows) >= 1
    assert rows[0]["tipo_registo"] == "Meta"
    assert "€" in rows[0]["valor"]
    assert int(rows[0]["lancamento_id"]) >= 1
    assert int(rows[0]["centro_custo_id"]) >= 1
    assert rows[0]["data_competencia_iso"] == "2026-06-10"


def test_inserir_replica_tres_meses(fin_conn: sqlite3.Connection) -> None:
    salvar_linha1_tres_textos(fin_conn, "C3", "N3", "T3")
    fin_conn.commit()
    tid = int(
        fin_conn.execute(
            "SELECT t.id FROM financeiro_tipo_gasto t "
            "JOIN financeiro_natureza n ON n.id = t.natureza_id WHERE t.nome = 'T3'"
        ).fetchone()[0]
    )
    n, err = inserir_lancamentos_operacionais(
        fin_conn,
        [tid],
        valor_centavos=100,
        data_competencia_iso="2026-01-31",
        status_lancamento="Pago",
        classe_lancamento="meta",
        replicar=True,
        meses_duracao=3,
    )
    assert not err
    assert n == 3
    fin_conn.commit()
    cnt = fin_conn.execute("SELECT COUNT(*) FROM financeiro_gasto_lancamentos WHERE tipo_gasto_id = ?", (tid,)).fetchone()[0]
    assert int(cnt) == 3
    cri = fin_conn.execute(
        "SELECT DISTINCT data_criacao_registo FROM financeiro_gasto_lancamentos WHERE tipo_gasto_id = ?",
        (tid,),
    ).fetchall()
    assert len(cri) == 1
