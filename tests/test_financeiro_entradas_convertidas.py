"""Financeiro — entradas convertidas (linhas de venda)."""

from __future__ import annotations

import sqlite3

import pytest

from src.database.connection import create_tables, get_connection
from src.modules.financeiro_entradas_convertidas import (
    listar_clientes_com_venda_para_filtro_entradas,
    listar_linhas_gestao_entradas_convertidas_vendas,
)


@pytest.fixture()
def ent_conn(tmp_path, monkeypatch):
    db = tmp_path / "fin_ent.db"
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(db))
    create_tables()
    c = get_connection()
    assert c is not None
    yield c
    c.close()


def _seed_venda_simples(cur: sqlite3.Cursor) -> tuple[int, int]:
    cur.execute(
        "INSERT INTO especialidades (natureza, nome, descritivo) VALUES (?, ?, ?)",
        ("Sessão", "EspEnt", ""),
    )
    eid = int(cur.lastrowid)
    cur.execute(
        """
        INSERT INTO servicos (nome, natureza, especialidade_id)
        VALUES (?, 'Sessão', ?)
        """,
        ("SrvEnt", eid),
    )
    sid = int(cur.lastrowid)
    cur.execute(
        """
        INSERT INTO colaboradores (
            nome, sexo, data_nascimento, email, whatsapp,
            endereco_rua, endereco_numero, codigo_postal, concelho, freguesia
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "Col Ent",
            "Feminino",
            "1990-05-01",
            "col-ent@test.local",
            "+351910000099",
            "Rua",
            "1",
            "4000-001",
            "Porto",
            "Centro",
        ),
    )
    col_id = int(cur.lastrowid)
    cur.execute(
        """
        INSERT INTO colaborador_servicos (
            colaborador_id, servico_id, percentual_centesimos, ordem, data_insercao_linha
        ) VALUES (?, ?, 2500, 1, '2026-01-01')
        """,
        (col_id, sid),
    )
    cur.execute(
        "INSERT INTO clientes (nome, whatsapp) VALUES (?, ?)",
        ("Cli Ent", "+351910000011"),
    )
    cid = int(cur.lastrowid)
    cur.execute(
        """
        INSERT INTO vendas (
            cliente_id, estado_pagamento,
            subtotal_bruto_centavos, subtotal_apos_descontos_linha_centavos,
            desconto_global_tipo, desconto_global_valor, desconto_global_centavos_aplicado,
            total_final_centavos, observacoes, credito_abatido_centavos
        ) VALUES (?, 'integral', 10000, 10000, NULL, NULL, 0, 10000, '', 0)
        """,
        (cid,),
    )
    vid = int(cur.lastrowid)
    cur.execute(
        """
        INSERT INTO venda_itens (
            venda_id, servico_id, ordem, quantidade, preco_unitario_centavos,
            nome_snapshot, descricao_snapshot, unidade_medida_snapshot,
            is_bonus, desconto_linha_tipo, desconto_linha_valor,
            subtotal_bruto_centavos, desconto_linha_centavos, total_linha_centavos,
            colaborador_id, pagamento_parcial
        ) VALUES (?, ?, 1, 1, 10000, 'Snap', '', 'un', 0, NULL, NULL, 10000, 0, 10000, ?, 0)
        """,
        (vid, sid, col_id),
    )
    vi = int(cur.lastrowid)
    return cid, vi


def test_listar_entradas_linha_e_repasse(ent_conn: sqlite3.Connection) -> None:
    cur = ent_conn.cursor()
    _seed_venda_simples(cur)
    ent_conn.commit()
    cli = listar_clientes_com_venda_para_filtro_entradas(ent_conn)
    assert len(cli) == 1
    rows = listar_linhas_gestao_entradas_convertidas_vendas(
        ent_conn, cliente_ids=None, naturezas=None, servico_ids=None, mes=None, ano=None
    )
    assert len(rows) == 1
    r = rows[0]
    assert int(r["valor_bruto_centavos"]) == 10_000
    assert int(r["valor_final_venda_centavos"]) == 10_000
    assert int(r["repasse_colaborador_centavos"]) == 2_500
    assert int(r["resultado_final_apurado_centavos"]) == 7_500
    assert int(r["total_valor_recebido_centavos"]) == 10_000


def test_total_valor_recebido_parcial_cartao(ent_conn: sqlite3.Connection) -> None:
    cur = ent_conn.cursor()
    _seed_venda_simples(cur)
    cur.execute("UPDATE vendas SET estado_pagamento = 'parcial' WHERE id = (SELECT MAX(id) FROM vendas)")
    vid = int(cur.execute("SELECT MAX(id) FROM vendas").fetchone()[0])
    cur.execute(
        """
        INSERT INTO venda_pagamento_linhas (venda_id, ordem, tipo_meio, valor_centavos)
        VALUES (?, 1, 'CARTAO_CREDITO', 4000)
        """,
        (vid,),
    )
    ent_conn.commit()
    rows = listar_linhas_gestao_entradas_convertidas_vendas(ent_conn)
    assert len(rows) == 1
    assert int(rows[0]["total_valor_recebido_centavos"]) == 4_000


def test_filtro_estado_pagamento(ent_conn: sqlite3.Connection) -> None:
    cur = ent_conn.cursor()
    _seed_venda_simples(cur)
    cur.execute(
        "UPDATE vendas SET estado_pagamento = 'pendente' WHERE id = (SELECT MAX(id) FROM vendas)"
    )
    ent_conn.commit()
    z = listar_linhas_gestao_entradas_convertidas_vendas(
        ent_conn,
        estados_pagamento=["integral"],
    )
    assert len(z) == 0
    p = listar_linhas_gestao_entradas_convertidas_vendas(
        ent_conn,
        estados_pagamento=["pendente"],
    )
    assert len(p) == 1
