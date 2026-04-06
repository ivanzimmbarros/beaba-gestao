import os

import pytest

from src.database.connection import create_tables, get_connection
from src.modules.agendamento import (
    alterar_status,
    cancelar_agendamento,
    criar_agendamento,
    listar_buckets_credito_cliente,
    saldo_bucket,
    validar_intervalo_horario,
)
from src.modules.catalogo import cadastrar_pacote, cadastrar_servico_fase1
from src.modules.cliente import buscar_cliente_por_whatsapp, cadastrar_cliente
from src.modules.venda import registrar_venda


@pytest.fixture(autouse=True)
def setup_db():
    if os.path.exists("data/beaba_gestao.db"):
        os.remove("data/beaba_gestao.db")
    create_tables()


def _cliente():
    ok, _ = cadastrar_cliente(
        nome="Cliente Agenda",
        numero_contato="91211111111",
        endereco_rua="Rua A",
        endereco_numero="1",
        endereco_complemento="",
        codigo_postal="4000-001",
        concelho="Porto",
        freguesia="Centro",
        distrito="",
        pais="Portugal",
        email="a@example.com",
        sexo="Outro",
        tem_filhos=False,
        filhos=[],
        gravida=None,
        data_parto_prevista=None,
        observacoes="",
        contatos_emergencia=[],
    )
    assert ok
    return buscar_cliente_por_whatsapp("91211111111")


def test_validar_intervalo_horario():
    ok, _ = validar_intervalo_horario("09:00", "10:00")
    assert ok
    ok2, msg = validar_intervalo_horario("10:00", "09:00")
    assert not ok2
    assert "hora_fim" in msg


def test_sessao_avulsa_criar_cancelar_buffer():
    cid = _cliente()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão Agenda T",
        "Desc.",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=40.0,
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão Agenda T",))
    sid = int(cur.fetchone()[0])
    conn.close()

    ok, msg = registrar_venda(
        int(cid),
        "integral",
        [
            {
                "servico_id": sid,
                "quantidade": 2,
                "is_bonus": False,
                "evento_preco": None,
                "desconto_linha_tipo": "none",
                "desconto_linha_valor": None,
            }
        ],
        None,
        None,
        [("dinheiro", 8000)],
        [],
        "",
    )
    assert ok, msg

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM venda_itens ORDER BY id DESC LIMIT 1")
    vi_id = int(cur.fetchone()[0])
    conn.close()

    buf = listar_buckets_credito_cliente(int(cid))
    assert len(buf) == 1
    assert buf[0]["saldo"] == 2

    ok, msg = criar_agendamento(
        vi_id, None, "2026-05-10", "09:00", "10:00", [], ""
    )
    assert ok, msg
    buf2 = listar_buckets_credito_cliente(int(cid))
    assert buf2[0]["saldo"] == 1

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM agendamentos ORDER BY id DESC LIMIT 1")
    ag_id = int(cur.fetchone()[0])
    conn.close()

    ok_c, _ = cancelar_agendamento(ag_id, devolver_ao_buffer=True)
    assert ok_c
    buf3 = listar_buckets_credito_cliente(int(cid))
    assert buf3[0]["saldo"] == 2

    ok2, _ = criar_agendamento(
        vi_id, None, "2026-05-11", "11:00", "12:00", [], ""
    )
    assert ok2
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM agendamentos ORDER BY id DESC LIMIT 1")
    ag2 = int(cur.fetchone()[0])
    conn.close()
    ok_c2, _ = cancelar_agendamento(ag2, devolver_ao_buffer=False)
    assert ok_c2
    buf4 = listar_buckets_credito_cliente(int(cid))
    assert buf4[0]["saldo"] == 1


def test_pacote_saldo_por_componente():
    cid = _cliente()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão P1",
        "D1",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=30.0,
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão P1",))
    s1 = int(cur.fetchone()[0])
    conn.close()
    ok_p, msg_p = cadastrar_pacote(
        "Pacote Agenda T",
        "Desc pacote.",
        True,
        [(s1, 2, None)],
        None,
        50.0,
        100.0,
    )
    assert ok_p, msg_p
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Pacote Agenda T",))
    pid = int(cur.fetchone()[0])
    cur.execute(
        "SELECT id FROM servico_pacote_sessoes WHERE pacote_servico_id = ?", (pid,)
    )
    ps_row = cur.fetchone()
    assert ps_row
    psid = int(ps_row[0])
    conn.close()

    ok, msg = registrar_venda(
        int(cid),
        "integral",
        [
            {
                "servico_id": pid,
                "quantidade": 1,
                "is_bonus": False,
                "evento_preco": None,
                "desconto_linha_tipo": "none",
                "desconto_linha_valor": None,
            }
        ],
        None,
        None,
        [("dinheiro", 10000)],
        [],
        "",
    )
    assert ok, msg
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM venda_itens ORDER BY id DESC LIMIT 1")
    vi_id = int(cur.fetchone()[0])
    assert saldo_bucket(cur, vi_id, psid) == 2
    assert saldo_bucket(cur, vi_id, None) == 0
    conn.close()

    ok_a1, _ = criar_agendamento(
        vi_id, psid, "2026-06-01", "08:00", "09:00", [], ""
    )
    assert ok_a1
    conn = get_connection()
    cur = conn.cursor()
    assert saldo_bucket(cur, vi_id, psid) == 1
    conn.close()
    ok_a2, _ = criar_agendamento(
        vi_id, psid, "2026-06-02", "08:00", "09:00", [], ""
    )
    assert ok_a2
    conn = get_connection()
    cur = conn.cursor()
    assert saldo_bucket(cur, vi_id, psid) == 0
    conn.close()
    ok_a3, msg3 = criar_agendamento(
        vi_id, psid, "2026-06-03", "08:00", "09:00", [], ""
    )
    assert not ok_a3
    assert "saldo" in msg3.lower()


def test_maquina_estados():
    cid = _cliente()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão ST",
        "D",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=20.0,
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão ST",))
    sid = int(cur.fetchone()[0])
    conn.close()
    assert registrar_venda(
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
        [("dinheiro", 2000)],
        [],
        "",
    )[0]
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM venda_itens ORDER BY id DESC LIMIT 1")
    vi_id = int(cur.fetchone()[0])
    conn.close()
    criar_agendamento(vi_id, None, "2026-07-01", "10:00", "11:00", [], "")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM agendamentos ORDER BY id DESC LIMIT 1")
    ag_id = int(cur.fetchone()[0])
    conn.close()

    assert alterar_status(ag_id, "CONFIRMADO")[0]
    assert alterar_status(ag_id, "CONCLUIDO")[0]
    assert not alterar_status(ag_id, "CONFIRMADO")[0]
