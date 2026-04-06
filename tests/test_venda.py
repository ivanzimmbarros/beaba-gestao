import os

import pytest

from src.database.connection import create_tables
from src.modules.catalogo import cadastrar_servico_fase1, resolver_snapshot_venda
from src.modules.cliente import buscar_cliente_por_whatsapp, cadastrar_cliente
from src.modules.venda import calcular_totais_venda, registrar_venda


@pytest.fixture(autouse=True)
def setup_db():
    if os.path.exists("data/beaba_gestao.db"):
        os.remove("data/beaba_gestao.db")
    create_tables()


def _cliente_min():
    ok, _ = cadastrar_cliente(
        nome="Cliente Venda QA",
        numero_contato="91234567890",
        endereco_rua="Rua A",
        endereco_numero="1",
        endereco_complemento="",
        codigo_postal="4000-001",
        concelho="Porto",
        freguesia="Centro",
        distrito="",
        pais="Portugal",
        email="venda@example.com",
        sexo="Outro",
        tem_filhos=False,
        filhos=[],
        gravida=None,
        data_parto_prevista=None,
        observacoes="",
        contatos_emergencia=[],
    )
    assert ok
    return buscar_cliente_por_whatsapp("91234567890")


def test_resolver_bonus_ligado_servico():
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão Bónus Cat",
        "Descritivo.",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=50.0,
    )
    conn = __import__("src.database.connection", fromlist=["get_connection"]).get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão Bónus Cat",))
    sid = int(cur.fetchone()[0])
    conn.close()
    ok, _, snap = resolver_snapshot_venda(sid, is_bonus=True)
    assert ok
    assert snap["preco_unitario_centavos"] == 0


def test_calcular_totais_desconto_linha_e_global():
    linhas = [
        {
            "quantidade": 2,
            "preco_unitario_centavos": 1000,
            "desconto_linha_tipo": "percent",
            "desconto_linha_valor": 1000,
        }
    ]
    ok, _, t = calcular_totais_venda(linhas)
    assert ok
    assert t["subtotal_bruto_centavos"] == 2000
    assert t["subtotal_apos_descontos_linha_centavos"] == 1800
    ok2, _, t2 = calcular_totais_venda(
        linhas, desconto_global_tipo="fixed", desconto_global_valor=300
    )
    assert t2["total_final_centavos"] == 1500


def test_registrar_venda_integral_split_meios():
    cid = _cliente_min()
    assert cid is not None
    cadastrar_servico_fase1(
        "Produto",
        "Produto Venda T",
        "Óleo.",
        True,
        produto_tipo="x",
        produto_descricao="",
        produto_valor_euros=40.0,
        produto_origem="proprio",
    )
    conn = __import__("src.database.connection", fromlist=["get_connection"]).get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Produto Venda T",))
    sid = int(cur.fetchone()[0])
    conn.close()

    ok, msg = registrar_venda(
        int(cid),
        "integral",
        [
            {
                "servico_id": sid,
                "quantidade": 1,
                "is_bonus": False,
                "evento_preco": None,
                "desconto_linha_tipo": "none",
                "desconto_linha_valor": None,
            }
        ],
        None,
        None,
        [("dinheiro", 2000), ("mbway", 2000)],
        [],
        "",
    )
    assert ok, msg

    conn = __import__("src.database.connection", fromlist=["get_connection"]).get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM venda_pagamentos")
    assert cur.fetchone()[0] == 2
    conn.close()


def test_registrar_pendente_previsto():
    cid = _cliente_min()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão Pendente T",
        "D.",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=30.0,
    )
    conn = __import__("src.database.connection", fromlist=["get_connection"]).get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão Pendente T",))
    sid = int(cur.fetchone()[0])
    conn.close()

    ok, msg = registrar_venda(
        int(cid),
        "pendente",
        [
            {
                "servico_id": sid,
                "quantidade": 1,
                "is_bonus": False,
                "evento_preco": None,
                "desconto_linha_tipo": "none",
                "desconto_linha_valor": None,
            }
        ],
        None,
        None,
        [],
        [("2026-12-01", 3000)],
        "teste",
    )
    assert ok, msg


def test_integral_soma_errada_falha():
    cid = _cliente_min()
    cadastrar_servico_fase1(
        "Coworking",
        "Sala V",
        "Sala.",
        True,
        cowork_sala_nome="S1",
        cowork_cobranca="hora",
        cowork_valor_euros=10.0,
    )
    conn = __import__("src.database.connection", fromlist=["get_connection"]).get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sala V",))
    sid = int(cur.fetchone()[0])
    conn.close()

    ok, msg = registrar_venda(
        int(cid),
        "integral",
        [
            {
                "servico_id": sid,
                "quantidade": 1,
                "is_bonus": False,
                "evento_preco": None,
                "desconto_linha_tipo": "none",
                "desconto_linha_valor": None,
            }
        ],
        None,
        None,
        [("dinheiro", 500)],
        [],
        "",
    )
    assert ok is False
    assert "Soma" in msg or "igualar" in msg
