"""E18 — ledger, mapeamento de meios, idempotência de crédito."""

from __future__ import annotations

import sqlite3

from src.database.connection import create_tables, get_connection
from src.modules.credito_ledger import (
    listar_pagamento_linhas_venda,
    meio_legacy_para_tipo_linha,
    obter_data_ultimo_pagamento_venda_dd_mm_yyyy,
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


def test_listar_pagamento_linhas_e_data_ultimo(tmp_path, monkeypatch):
    db = tmp_path / "e18_lij.db"
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(db))
    create_tables()
    conn = get_connection()
    assert conn is not None
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO clientes (nome, whatsapp) VALUES (?, ?)",
            ("Cli Lij", "+351910000001"),
        )
        cid = int(cur.lastrowid)
        cur.execute(
            """
            INSERT INTO vendas (
                cliente_id, estado_pagamento,
                subtotal_bruto_centavos, subtotal_apos_descontos_linha_centavos,
                desconto_global_centavos_aplicado, total_final_centavos, observacoes
            ) VALUES (?, 'parcial', 5000, 5000, 0, 5000, '')
            """,
            (cid,),
        )
        vid = int(cur.lastrowid)
        cur.execute(
            """
            INSERT INTO venda_pagamento_linhas
                (venda_id, ordem, tipo_meio, valor_centavos, criado_em)
            VALUES
                (?, 1, 'DINHEIRO_MBWAY', 2000, '2026-03-19 10:00:00'),
                (?, 2, 'DINHEIRO_MBWAY', 2000, '2026-03-20 15:30:00')
            """,
            (vid, vid),
        )
        conn.commit()
    finally:
        conn.close()

    rows = listar_pagamento_linhas_venda(vid)
    assert len(rows) == 2
    assert rows[0]["valor_centavos"] == 2000
    assert rows[1]["valor_centavos"] == 2000
    assert obter_data_ultimo_pagamento_venda_dd_mm_yyyy(vid) == "20-03-2026"
