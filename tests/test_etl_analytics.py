"""E19 — smoke do ETL dw_* (sem Streamlit)."""

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.etl_analytics import (  # noqa: E402
    carga_horaria_decimal,
    run_etl,
)


def test_carga_horaria_decimal():
    assert carga_horaria_decimal("09:00", "10:30") == 1.5
    assert carga_horaria_decimal("09:00", "09:00") is None
    assert carga_horaria_decimal("bad", "10:00") is None


def test_run_etl_dw_tables_and_ltv_rules():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            whatsapp TEXT NOT NULL UNIQUE
        );
        INSERT INTO clientes (id, nome, whatsapp) VALUES (1, 'A', '+351900000001');

        CREATE TABLE servicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            natureza TEXT DEFAULT 'Sessão'
        );
        INSERT INTO servicos (id, nome) VALUES (1, 'Sessão teste');

        CREATE TABLE vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            data_registo TEXT DEFAULT CURRENT_TIMESTAMP,
            estado_pagamento TEXT NOT NULL,
            total_final_centavos INTEGER NOT NULL,
            credito_abatido_centavos INTEGER NOT NULL DEFAULT 0,
            observacoes TEXT DEFAULT ''
        );
        INSERT INTO vendas (id, cliente_id, estado_pagamento, total_final_centavos, credito_abatido_centavos)
        VALUES
            (1, 1, 'integral', 10000, 0),
            (2, 1, 'pendente', 5000, 0),
            (3, 1, 'integral', 10000, 3000);

        CREATE TABLE venda_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER NOT NULL,
            servico_id INTEGER NOT NULL,
            ordem INTEGER NOT NULL,
            quantidade INTEGER NOT NULL,
            preco_unitario_centavos INTEGER NOT NULL,
            nome_snapshot TEXT NOT NULL,
            subtotal_bruto_centavos INTEGER NOT NULL,
            total_linha_centavos INTEGER NOT NULL
        );
        INSERT INTO venda_itens (id, venda_id, servico_id, ordem, quantidade, preco_unitario_centavos,
            nome_snapshot, subtotal_bruto_centavos, total_linha_centavos)
        VALUES (1, 1, 1, 1, 1, 10000, 'x', 10000, 10000);

        CREATE TABLE venda_pagamento_linhas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER NOT NULL,
            ordem INTEGER NOT NULL,
            tipo_meio TEXT NOT NULL,
            valor_centavos INTEGER NOT NULL,
            UNIQUE (venda_id, ordem)
        );
        INSERT INTO venda_pagamento_linhas (venda_id, ordem, tipo_meio, valor_centavos)
        VALUES
            (1, 0, 'DINHEIRO_MBWAY', 10000),
            (3, 0, 'IBAN', 7000);

        CREATE TABLE venda_pagamentos (id INTEGER PRIMARY KEY, venda_id INTEGER, ordem INTEGER, meio TEXT, valor_centavos INTEGER);

        CREATE TABLE agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER,
            venda_item_id INTEGER,
            cliente_id INTEGER NOT NULL,
            servico_id INTEGER NOT NULL,
            pacote_sessao_id INTEGER,
            tipo_origem TEXT NOT NULL,
            data_agendamento TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fim TEXT NOT NULL,
            status TEXT NOT NULL,
            devolver_ao_buffer INTEGER NOT NULL DEFAULT 0,
            observacoes TEXT DEFAULT '',
            modo_origem TEXT NOT NULL DEFAULT 'pre_venda',
            preco_referencia_centavos INTEGER
        );
        INSERT INTO agendamentos (
            venda_id, venda_item_id, cliente_id, servico_id, tipo_origem,
            data_agendamento, hora_inicio, hora_fim, status, modo_origem
        ) VALUES (NULL, NULL, 1, 1, 'sessao_avulsa', '2026-01-10', '09:00', '10:30', 'CONCLUIDO', 'pre_venda');
        """
    )
    conn.commit()

    stats = run_etl(conn)
    assert stats["dw_fact_agendamento"] == 1
    assert stats["dw_fact_venda"] == 3

    row = conn.execute(
        "SELECT carga_horaria_h, is_cancelado FROM dw_fact_agendamento WHERE agendamento_id = 1"
    ).fetchone()
    assert row[0] == 1.5
    assert row[1] == 0

    r1 = conn.execute(
        "SELECT receita_ltv_real_centavos, totalmente_liquidada FROM dw_fact_venda WHERE venda_id = 1"
    ).fetchone()
    assert r1[0] == 10000
    assert r1[1] == 1

    r2 = conn.execute(
        "SELECT receita_ltv_real_centavos FROM dw_fact_venda WHERE venda_id = 2"
    ).fetchone()
    assert r2[0] == 0

    r3 = conn.execute(
        "SELECT esperado_liquidacao_centavos, receita_ltv_real_centavos FROM dw_fact_venda WHERE venda_id = 3"
    ).fetchone()
    assert r3[0] == 7000
    assert r3[1] == 7000

    kpi = conn.execute(
        "SELECT visitas_nao_canceladas, receita_ltv_real_total_centavos FROM dw_cliente_kpi WHERE cliente_id = 1"
    ).fetchone()
    assert kpi[0] == 1
    assert kpi[1] == 17000

    conn.close()
