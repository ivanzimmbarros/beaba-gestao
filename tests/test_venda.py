import pytest

from src.modules.catalogo import cadastrar_servico_fase1, resolver_snapshot_venda
from src.modules.cliente import (
    buscar_cliente_por_whatsapp,
    cadastrar_cliente,
)
from src.modules.agendamento import criar_agendamento_pre_venda
from src.modules.venda import calcular_totais_venda, listar_venda_item_ids_em_ordem, registrar_venda


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
        nif="123456789",
        documento_identificacao_internacional=False,
        data_nascimento="1990-05-15",
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

    ok, msg, _ = registrar_venda(
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

    ok, msg, _ = registrar_venda(
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

    ok, msg, _ = registrar_venda(
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


def test_registrar_venda_contexto_agendamento_cliente_diferente_falha():
    cid1 = _cliente_min()
    assert cid1
    ok2, _ = cadastrar_cliente(
        nome="Outro Cliente",
        numero_contato="91333333333",
        endereco_rua="Rua B",
        endereco_numero="2",
        endereco_complemento="",
        codigo_postal="4000-002",
        concelho="Porto",
        freguesia="Centro",
        distrito="",
        pais="Portugal",
        email="o@example.com",
        sexo="Outro",
        tem_filhos=False,
        filhos=[],
        gravida=None,
        data_parto_prevista=None,
        observacoes="",
        contatos_emergencia=[],
        nif="286303850",
        documento_identificacao_internacional=False,
        data_nascimento="1991-06-20",
    )
    assert ok2
    cid2 = buscar_cliente_por_whatsapp("91333333333")
    assert cid2
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão CTX",
        "D.",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=25.0,
    )
    conn = __import__("src.database.connection", fromlist=["get_connection"]).get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão CTX",))
    sid = int(cur.fetchone()[0])
    conn.close()
    ok_ag, _ = criar_agendamento_pre_venda(
        int(cid1), sid, "2030-05-01", "09:00", "10:00", [], "", None
    )
    assert ok_ag
    conn = __import__("src.database.connection", fromlist=["get_connection"]).get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM agendamentos ORDER BY id DESC LIMIT 1")
    ag_id = int(cur.fetchone()[0])
    conn.close()
    ok, msg, vid = registrar_venda(
        int(cid2),
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
        [("dinheiro", 2500)],
        [],
        "",
        agendamento_contexto_id=ag_id,
    )
    assert not ok
    assert vid is None
    assert "coincidir" in msg.lower() or "cliente" in msg.lower()


def test_listar_venda_item_ids_em_ordem():
    cid = _cliente_min()
    assert cid
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão Ord VI",
        "D",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=15.0,
    )
    conn = __import__("src.database.connection", fromlist=["get_connection"]).get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão Ord VI",))
    sid = int(cur.fetchone()[0])
    conn.close()
    ok, msg, vid = registrar_venda(
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
        [("dinheiro", 1500)],
        [],
        "",
    )
    assert ok and vid is not None
    ids = listar_venda_item_ids_em_ordem(int(vid))
    assert len(ids) == 1
    assert ids[0] >= 1
