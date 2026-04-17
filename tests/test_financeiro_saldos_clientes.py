"""Financeiro — saldos activos de clientes (FIFO crédito vs uso em venda)."""

from __future__ import annotations

import sqlite3

import pytest

from src.database.connection import create_tables, get_connection
from src.modules.financeiro_saldos_clientes import (
    listar_linhas_gestao_saldos_clientes_ativos,
    listar_vendas_com_consumo_credito_loja,
    totais_saldos_ativos_por_antiguidade_cancelamento,
)


@pytest.fixture()
def saldo_conn(tmp_path, monkeypatch):
    db = tmp_path / "fin_saldo.db"
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(db))
    create_tables()
    c = get_connection()
    assert c is not None
    yield c
    c.close()


def _seed_servico_cliente_ag_venda(cur: sqlite3.Cursor) -> tuple[int, int, int, int, int]:
    cur.execute(
        "INSERT INTO especialidades (natureza, nome, descritivo) VALUES (?, ?, ?)",
        ("Sessão", "EspSaldo", ""),
    )
    eid = int(cur.lastrowid)
    cur.execute(
        """
        INSERT INTO servicos (nome, natureza, especialidade_id)
        VALUES (?, 'Sessão', ?)
        """,
        ("SrvSaldo", eid),
    )
    sid = int(cur.lastrowid)
    cur.execute(
        "INSERT INTO clientes (nome, whatsapp) VALUES (?, ?)",
        ("Cli Saldo", "+351910000099"),
    )
    cid = int(cur.lastrowid)
    cur.execute(
        """
        INSERT INTO vendas (
            cliente_id, estado_pagamento,
            subtotal_bruto_centavos, subtotal_apos_descontos_linha_centavos,
            desconto_global_centavos_aplicado, total_final_centavos, observacoes
        ) VALUES (?, 'integral', 10000, 10000, 0, 10000, '')
        """,
        (cid,),
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
    vi_id = int(cur.lastrowid)
    cur.execute(
        """
        INSERT INTO agendamentos (
            venda_id, venda_item_id, cliente_id, servico_id, pacote_sessao_id,
            tipo_origem, data_agendamento, hora_inicio, hora_fim, status,
            devolver_ao_buffer, observacoes, modo_origem, data_criacao_registo, data_alteracao
        ) VALUES (?, ?, ?, ?, NULL, 'sessao_avulsa', '2026-06-01', '10:00', '11:00', 'CANCELADO',
            0, '', 'credito_venda', '2026-01-10', '2026-01-20 15:00:00')
        """,
        (vid, vi_id, cid, sid),
    )
    aid = int(cur.lastrowid)
    return cid, sid, vid, vi_id, aid


def test_fifo_saldo_restante_apos_uso_venda(saldo_conn: sqlite3.Connection) -> None:
    cur = saldo_conn.cursor()
    cid, sid, vid, _vi, aid = _seed_servico_cliente_ag_venda(cur)
    cur.execute(
        """
        INSERT INTO credito_movimentos (
            cliente_id, tipo_movimento, valor_centavos,
            referencia_tipo, referencia_id, observacoes, criado_em
        ) VALUES (?, 'CREDITO_CANCELAMENTO', ?, 'agendamento', ?, 'test', '2026-01-21 10:00:00')
        """,
        (cid, 10_000, aid),
    )
    cur.execute(
        """
        INSERT INTO credito_movimentos (
            cliente_id, tipo_movimento, valor_centavos,
            referencia_tipo, referencia_id, observacoes, criado_em
        ) VALUES (?, 'USO_VENDA', ?, 'venda', ?, 'test', '2026-01-22 10:00:00')
        """,
        (cid, -3_000, vid),
    )
    cur.execute(
        "UPDATE vendas SET credito_abatido_centavos = 3000 WHERE id = ?",
        (vid,),
    )
    saldo_conn.commit()

    linhas = listar_linhas_gestao_saldos_clientes_ativos(
        saldo_conn, cliente_ids=[cid], naturezas=None, servico_ids=None, mes=None, ano=None
    )
    assert len(linhas) == 1
    assert int(linhas[0]["saldo_restante_centavos"]) == 7_000
    assert linhas[0]["referente_a_pacote"] == "Não"
    assert str(linhas[0].get("nome_pacote") or "") == ""

    tot, r15, o15 = totais_saldos_ativos_por_antiguidade_cancelamento(linhas)
    assert tot == 7_000
    assert tot == r15 + o15

    usos = listar_vendas_com_consumo_credito_loja(
        saldo_conn, cliente_ids=[cid], naturezas=None, servico_ids=None, mes=None, ano=None
    )
    assert len(usos) == 1
    assert int(usos[0]["valor_saldo_utilizado_centavos"]) == 3_000
    assert int(usos[0]["valor_original_sem_saldo_centavos"]) == 10_000
    assert int(usos[0]["valor_final_com_saldo_abatido_centavos"]) == 7_000

    linhas_so_pacote = listar_linhas_gestao_saldos_clientes_ativos(
        saldo_conn, cliente_ids=[cid], naturezas=["Pacote"], servico_ids=None, mes=None, ano=None
    )
    assert len(linhas_so_pacote) == 0


def test_linha_saldo_cancelamento_pacote_referente_e_nome(saldo_conn: sqlite3.Connection) -> None:
    cur = saldo_conn.cursor()
    cur.execute(
        "INSERT INTO especialidades (natureza, nome, descritivo) VALUES (?, ?, ?)",
        ("Sessão", "EspPacFin", ""),
    )
    e_sess = int(cur.lastrowid)
    cur.execute(
        "INSERT INTO especialidades (natureza, nome, descritivo) VALUES (?, ?, ?)",
        ("Pacote", "EspPacoteFin", ""),
    )
    e_pac = int(cur.lastrowid)
    cur.execute(
        """
        INSERT INTO servicos (nome, natureza, especialidade_id)
        VALUES (?, 'Sessão', ?)
        """,
        ("Sessão do Pacote Fin", e_sess),
    )
    sid_sess = int(cur.lastrowid)
    cur.execute(
        """
        INSERT INTO servicos (nome, natureza, especialidade_id)
        VALUES (?, 'Pacote', ?)
        """,
        ("Pacote Catálogo Fin", e_pac),
    )
    sid_pac = int(cur.lastrowid)
    cur.execute(
        """
        INSERT INTO servico_pacote_sessoes (
            pacote_servico_id, sessao_servico_id, quantidade, duracao_horas, ordem
        ) VALUES (?, ?, 3, 1.0, 1)
        """,
        (sid_pac, sid_sess),
    )
    psid = int(cur.lastrowid)
    cur.execute(
        "INSERT INTO clientes (nome, whatsapp) VALUES (?, ?)",
        ("Cli Pac Fin", "+351910000088"),
    )
    cid = int(cur.lastrowid)
    cur.execute(
        """
        INSERT INTO vendas (
            cliente_id, estado_pagamento,
            subtotal_bruto_centavos, subtotal_apos_descontos_linha_centavos,
            desconto_global_centavos_aplicado, total_final_centavos, observacoes
        ) VALUES (?, 'integral', 12000, 12000, 0, 12000, '')
        """,
        (cid,),
    )
    vid = int(cur.lastrowid)
    cur.execute(
        """
        INSERT INTO venda_itens (
            venda_id, servico_id, ordem, quantidade, preco_unitario_centavos,
            nome_snapshot, descricao_snapshot, unidade_medida_snapshot,
            subtotal_bruto_centavos, total_linha_centavos
        ) VALUES (?, ?, 1, 1, 12000, 'Nome Snap Pacote Fin', '', 'un', 12000, 12000)
        """,
        (vid, sid_pac),
    )
    vi_pkg = int(cur.lastrowid)
    cur.execute(
        """
        INSERT INTO agendamentos (
            venda_id, venda_item_id, cliente_id, servico_id, pacote_sessao_id,
            tipo_origem, data_agendamento, hora_inicio, hora_fim, status,
            devolver_ao_buffer, observacoes, modo_origem, data_criacao_registo, data_alteracao
        ) VALUES (?, ?, ?, ?, ?, 'pacote', '2026-07-01', '10:00', '11:00', 'CANCELADO',
            0, '', 'credito_venda', '2026-02-10', '2026-02-20 15:00:00')
        """,
        (vid, vi_pkg, cid, sid_sess, psid),
    )
    aid = int(cur.lastrowid)
    cur.execute(
        """
        INSERT INTO credito_movimentos (
            cliente_id, tipo_movimento, valor_centavos,
            referencia_tipo, referencia_id, observacoes, criado_em
        ) VALUES (?, 'CREDITO_CANCELAMENTO', ?, 'agendamento', ?, 'test', '2026-02-21 10:00:00')
        """,
        (cid, 4_000, aid),
    )
    saldo_conn.commit()

    linhas = listar_linhas_gestao_saldos_clientes_ativos(
        saldo_conn, cliente_ids=[cid], naturezas=None, servico_ids=None, mes=None, ano=None
    )
    assert len(linhas) == 1
    assert linhas[0]["referente_a_pacote"] == "Sim"
    assert linhas[0]["nome_pacote"] == "Nome Snap Pacote Fin"

    # Filtro «Nome do serviço» com ID do **Pacote** (catálogo) → coluna Nome do Pacote / vi_pkg.
    por_pac = listar_linhas_gestao_saldos_clientes_ativos(
        saldo_conn, cliente_ids=[cid], naturezas=None, servico_ids=[sid_pac], mes=None, ano=None
    )
    assert len(por_pac) == 1
    cur.execute(
        """
        INSERT INTO servicos (nome, natureza, especialidade_id)
        VALUES (?, 'Pacote', ?)
        """,
        ("Outro Pacote Só Filtro", e_pac),
    )
    sid_outro = int(cur.lastrowid)
    saldo_conn.commit()
    por_outro = listar_linhas_gestao_saldos_clientes_ativos(
        saldo_conn, cliente_ids=[cid], naturezas=None, servico_ids=[sid_outro], mes=None, ano=None
    )
    assert len(por_outro) == 0

    # Cancelamento em Fevereiro/2026 (data_alteracao) — mês/ano afectam totais derivados das linhas.
    lm_fev = listar_linhas_gestao_saldos_clientes_ativos(
        saldo_conn, cliente_ids=[cid], naturezas=None, servico_ids=None, mes=2, ano=2026
    )
    assert len(lm_fev) == 1
    assert totais_saldos_ativos_por_antiguidade_cancelamento(lm_fev)[0] == 4_000
    lm_jan = listar_linhas_gestao_saldos_clientes_ativos(
        saldo_conn, cliente_ids=[cid], naturezas=None, servico_ids=None, mes=1, ano=2026
    )
    assert len(lm_jan) == 0
    assert totais_saldos_ativos_por_antiguidade_cancelamento(lm_jan)[0] == 0

    # Natureza «Pacote» no filtro = linhas com «Referente a Pacote?» = Sim (não s.natureza da sessão).
    por_nat_pac = listar_linhas_gestao_saldos_clientes_ativos(
        saldo_conn, cliente_ids=[cid], naturezas=["Pacote"], servico_ids=None, mes=None, ano=None
    )
    assert len(por_nat_pac) == 1
