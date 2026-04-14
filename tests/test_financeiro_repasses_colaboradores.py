"""Gestão de repasses (Financeiro) — consulta sobre repasse_linhas + agendamentos."""

from __future__ import annotations

import sqlite3

import pytest

from src.database.connection import create_tables, get_connection
from src.modules.colaborador import cadastrar_colaborador
from src.modules.financeiro_repasses_colaboradores import listar_linhas_gestao_repasses


@pytest.fixture()
def rep_conn(tmp_path, monkeypatch):
    db = tmp_path / "fin_repasse.db"
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(db))
    create_tables()
    c = get_connection()
    assert c is not None
    yield c
    c.close()


def _seed_repasse_row(conn: sqlite3.Connection) -> tuple[int, int]:
    """Devolve (colaborador_id, servico_id) após inserir venda + agendamento CONCLUIDO + repasse_linhas."""
    cur = conn.cursor()
    cur.execute("SELECT id, nome, natureza FROM servicos ORDER BY id LIMIT 1")
    srow = cur.fetchone()
    assert srow is not None
    sid = int(srow[0])

    ok, _ = cadastrar_colaborador(
        nome="Colab Repasse Fin",
        sexo="Feminino",
        data_nascimento="1990-05-10",
        endereco_rua="Rua X",
        endereco_numero="10",
        endereco_complemento="",
        codigo_postal="4700-223",
        concelho="Braga",
        freguesia="Sé",
        distrito="",
        pais="Portugal",
        email="colab.rep.fin@beaba.test",
        numero_contato="11977665544",
        observacoes="",
        servicos_repasse=[(sid, 25.0, "2026-01-01")],
    )
    assert ok
    cur.execute("SELECT id FROM colaboradores WHERE nome = ?", ("Colab Repasse Fin",))
    cid = int(cur.fetchone()[0])

    cur.execute(
        "INSERT INTO clientes (nome, whatsapp) VALUES (?, ?)",
        ("Cliente Rep Fin", "+351919001199"),
    )
    cli_id = int(cur.lastrowid)

    cur.execute(
        """
        INSERT INTO vendas (
            cliente_id, estado_pagamento,
            subtotal_bruto_centavos, subtotal_apos_descontos_linha_centavos,
            desconto_global_centavos_aplicado, total_final_centavos, observacoes
        ) VALUES (?, 'integral', 10000, 10000, 0, 10000, '')
        """,
        (cli_id,),
    )
    vid = int(cur.lastrowid)

    cur.execute(
        """
        INSERT INTO venda_itens (
            venda_id, servico_id, ordem, quantidade, preco_unitario_centavos,
            nome_snapshot, descricao_snapshot, unidade_medida_snapshot,
            subtotal_bruto_centavos, total_linha_centavos
        ) VALUES (?, ?, 1, 1, 10000, 'Snap', '', 'un', 10000, 10000)
        """,
        (vid, sid),
    )
    viid = int(cur.lastrowid)

    cur.execute(
        """
        INSERT INTO agendamentos (
            venda_id, venda_item_id, cliente_id, servico_id, pacote_sessao_id,
            tipo_origem, data_agendamento, hora_inicio, hora_fim, status,
            devolver_ao_buffer, observacoes, modo_origem
        ) VALUES (?, ?, ?, ?, NULL, 'sessao_avulsa', '2026-03-20', '09:00', '10:00',
            'CONCLUIDO', 0, '', 'credito_venda')
        """,
        (vid, viid, cli_id, sid),
    )
    ag_id = int(cur.lastrowid)

    cur.execute(
        "INSERT INTO agendamento_colaboradores (agendamento_id, colaborador_id, ordem) VALUES (?, ?, 1)",
        (ag_id, cid),
    )

    cur.execute(
        """
        INSERT INTO repasse_linhas (
            agendamento_id, colaborador_id, base_calculo_centavos,
            percentual_bp, valor_repasse_centavos, status_repasse
        ) VALUES (?, ?, 10000, 2500, 2500, 'PENDENTE_REPASSE')
        """,
        (ag_id, cid),
    )
    conn.commit()
    return cid, sid


def test_listar_repasses_vazio(rep_conn: sqlite3.Connection) -> None:
    assert listar_linhas_gestao_repasses(rep_conn) == []


def test_listar_repasses_concluido_e_filtros(rep_conn: sqlite3.Connection) -> None:
    cid, sid = _seed_repasse_row(rep_conn)
    rows = listar_linhas_gestao_repasses(rep_conn)
    assert len(rows) == 1
    assert rows[0]["colaborador_nome"] == "Colab Repasse Fin"
    assert int(rows[0]["base_calculo_centavos"]) == 10000
    assert int(rows[0]["valor_repasse_centavos"]) == 2500
    assert rows[0]["data_execucao_dm"] == "20/03/2026"

    rows_m = listar_linhas_gestao_repasses(rep_conn, mes=3, ano=2026)
    assert len(rows_m) == 1

    rows_m2 = listar_linhas_gestao_repasses(rep_conn, mes=4, ano=2026)
    assert rows_m2 == []

    rows_c = listar_linhas_gestao_repasses(rep_conn, colaborador_ids=[cid])
    assert len(rows_c) == 1

    rows_x = listar_linhas_gestao_repasses(rep_conn, colaborador_ids=[cid + 9999])
    assert rows_x == []

    rows_s = listar_linhas_gestao_repasses(rep_conn, servico_ids=[sid])
    assert len(rows_s) == 1


def test_listar_repasses_filtro_natureza(rep_conn: sqlite3.Connection) -> None:
    _cid, sid = _seed_repasse_row(rep_conn)
    cur = rep_conn.cursor()
    nat = str(cur.execute("SELECT natureza FROM servicos WHERE id = ?", (sid,)).fetchone()[0] or "")
    assert nat
    rows_ok = listar_linhas_gestao_repasses(rep_conn, naturezas=[nat])
    assert len(rows_ok) == 1
    rows_bad = listar_linhas_gestao_repasses(rep_conn, naturezas=["__natureza_inexistente__"])
    assert rows_bad == []


def test_realizado_pendente_pgto_incluido(rep_conn: sqlite3.Connection) -> None:
    cid, sid = _seed_repasse_row(rep_conn)
    cur = rep_conn.cursor()
    cur.execute("UPDATE agendamentos SET status = 'REALIZADO_PENDENTE_PGTO' WHERE id = (SELECT MAX(id) FROM agendamentos)")
    rep_conn.commit()
    rows = listar_linhas_gestao_repasses(rep_conn)
    assert len(rows) == 1
