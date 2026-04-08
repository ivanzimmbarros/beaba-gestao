"""E18 — ledger, mapeamento de meios, idempotência de crédito."""

from __future__ import annotations

import sqlite3

from src.modules.credito_ledger import (
    meio_legacy_para_tipo_linha,
    registrar_credito_por_cancelamento_agendamento,
    saldo_credito_cliente_centavos,
    total_esperado_liquidacao_venda_centavos,
    total_liquidado_venda_centavos,
)


def test_meio_legacy_para_tipo_linha():
    assert meio_legacy_para_tipo_linha("iban") == "IBAN"
    assert meio_legacy_para_tipo_linha("dinheiro") == "DINHEIRO_MBWAY"


def test_credito_cancelamento_idempotente():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE clientes (id INTEGER PRIMARY KEY)")
    cur.execute("INSERT INTO clientes (id) VALUES (1)")
    cur.execute(
        """
        CREATE TABLE credito_movimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            tipo_movimento TEXT NOT NULL,
            valor_centavos INTEGER NOT NULL,
            referencia_tipo TEXT NOT NULL DEFAULT '',
            referencia_id INTEGER,
            observacoes TEXT,
            actor TEXT,
            criado_em TEXT,
            UNIQUE (referencia_tipo, referencia_id, tipo_movimento)
        )
        """
    )
    cur.execute(
        """
        CREATE VIEW vw_cliente_saldo_credito AS
        SELECT cliente_id, COALESCE(SUM(valor_centavos), 0) AS saldo_credito_centavos
        FROM credito_movimentos GROUP BY cliente_id
        """
    )
    assert registrar_credito_por_cancelamento_agendamento(
        cur,
        cliente_id=1,
        agendamento_id=42,
        valor_centavos=500,
    )
    assert not registrar_credito_por_cancelamento_agendamento(
        cur,
        cliente_id=1,
        agendamento_id=42,
        valor_centavos=500,
    )
    assert saldo_credito_cliente_centavos(cur, 1) == 500


def test_gate_total_liquidado_vs_esperado():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE vendas (
            id INTEGER PRIMARY KEY,
            total_final_centavos INTEGER NOT NULL,
            credito_abatido_centavos INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    cur.execute("INSERT INTO vendas (id, total_final_centavos, credito_abatido_centavos) VALUES (1, 10000, 2500)")
    cur.execute(
        """
        CREATE TABLE venda_pagamento_linhas (
            id INTEGER PRIMARY KEY,
            venda_id INTEGER NOT NULL,
            ordem INTEGER NOT NULL,
            tipo_meio TEXT NOT NULL,
            valor_centavos INTEGER NOT NULL
        )
        """
    )
    cur.execute(
        "INSERT INTO venda_pagamento_linhas VALUES (1, 1, 1, 'DINHEIRO_MBWAY', 7500)"
    )
    assert total_esperado_liquidacao_venda_centavos(cur, 1) == 7500
    assert total_liquidado_venda_centavos(cur, 1) == 7500
