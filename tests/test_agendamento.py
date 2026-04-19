from datetime import date

import pytest

from src.database.connection import get_connection
from src.modules.agendamento import (
    agendamento_elegivel_conversao_para_pacote_hoje,
    alterar_status,
    analisar_sessoes_pacote_pendentes_cag,
    associar_agendamento_pre_venda_a_item,
    cancelar_agendamento,
    contar_pre_venda_futuros,
    contar_total_sessoes_pacote_pendentes_agendamento,
    converter_agendamento_avulso_para_consumo_pacote,
    criar_agendamento,
    criar_agendamento_pre_venda,
    listar_agendamentos_elegiveis_associacao_linha_venda,
    listar_agendamentos_realizado_pendente_liquidacao_cliente,
    listar_buckets_credito_cliente,
    listar_buckets_pacote_com_saldo_disponivel,
    listar_opcoes_servicos_adquiridos_pendente_pre_agendamento,
    obter_agendamento,
    pos_venda_associar_agendamentos_por_linha,
    saldo_bucket,
    validar_intervalo_horario,
    validar_tipo_atendimento_e_sala,
)
from src.modules.catalogo import cadastrar_pacote, cadastrar_servico_fase1
from src.modules.cliente import buscar_cliente_por_whatsapp, cadastrar_cliente
from src.modules.colaborador import cadastrar_colaborador
from src.modules.credito_ledger import obter_saldo_credito_cliente
from src.modules.venda import listar_venda_item_ids_em_ordem, registrar_venda


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
        nif="123456789",
        documento_identificacao_internacional=False,
        data_nascimento="1990-05-15",
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

    ok, msg, _vid = registrar_venda(
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

    ok, msg, _ = registrar_venda(
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
    conn.close()
    ok_a1, msg1 = criar_agendamento(
        vi_id, psid, "2026-06-01", "08:00", "09:00", [], ""
    )
    assert ok_a1, msg1
    conn = get_connection()
    cur = conn.cursor()
    assert saldo_bucket(cur, vi_id, psid) == 1
    conn.close()
    ok_a2, msg2 = criar_agendamento(
        vi_id, psid, "2026-06-02", "08:00", "09:00", [], ""
    )
    assert ok_a2, msg2
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


def test_alterar_status_agendado_para_pre_agendado():
    """CAG permite «Pré-agendado» a partir de Agendado (reversão administrativa)."""
    cid = _cliente()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão PRE",
        "D",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=25.0,
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão PRE",))
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
        [("dinheiro", 2500)],
        [],
        "",
    )[0]
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM venda_itens ORDER BY id DESC LIMIT 1")
    vi_id = int(cur.fetchone()[0])
    conn.close()
    criar_agendamento(vi_id, None, "2026-08-01", "09:00", "10:00", [], "")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM agendamentos ORDER BY id DESC LIMIT 1")
    ag_id = int(cur.fetchone()[0])
    cur.execute("SELECT status FROM agendamentos WHERE id = ?", (ag_id,))
    assert str(cur.fetchone()[0]) == "AGENDADO"
    conn.close()
    ok, msg = alterar_status(ag_id, "PRE_AGENDADO")
    assert ok, msg
    ag = obter_agendamento(ag_id)
    assert ag is not None
    assert ag["status"] == "PRE_AGENDADO"


def test_schema_agendamentos_tem_modo_origem():
    conn = get_connection()
    assert conn
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(agendamentos)")
    cols = {row[1] for row in cur.fetchall()}
    conn.close()
    assert "modo_origem" in cols
    assert "preco_referencia_centavos" in cols
    assert "tipo_atendimento" in cols
    assert "sala_virtual_disponibilizada" in cols


def test_pre_venda_sessao_concluir_bloqueado():
    cid = _cliente()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão PV",
        "D",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=35.0,
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão PV",))
    sid = int(cur.fetchone()[0])
    conn.close()
    ok, msg = criar_agendamento_pre_venda(
        int(cid),
        sid,
        "2030-01-15",
        "10:00",
        "11:00",
        [],
        "",
        None,
    )
    assert ok, msg
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM agendamentos ORDER BY id DESC LIMIT 1")
    ag_id = int(cur.fetchone()[0])
    cur.execute("SELECT modo_origem, venda_id FROM agendamentos WHERE id = ?", (ag_id,))
    m, v = cur.fetchone()
    conn.close()
    assert str(m) == "pre_venda"
    assert v is None
    assert contar_pre_venda_futuros("2030-01-01") >= 1
    assert alterar_status(ag_id, "CONFIRMADO")[0]
    ok_done, msg_done = alterar_status(ag_id, "CONCLUIDO")
    assert not ok_done
    assert "pré-venda" in msg_done.lower() or "venda" in msg_done.lower()


def test_pre_venda_associar_apos_venda():
    cid = _cliente()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão ASC",
        "D",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=22.0,
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão ASC",))
    sid = int(cur.fetchone()[0])
    conn.close()
    ok, msg = criar_agendamento_pre_venda(
        int(cid), sid, "2030-02-01", "14:00", "15:00", [], "", None
    )
    assert ok, msg
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM agendamentos ORDER BY id DESC LIMIT 1")
    ag_id = int(cur.fetchone()[0])
    conn.close()
    ok_v, msg_v, vid = registrar_venda(
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
        [("dinheiro", 2200)],
        [],
        "",
        agendamento_contexto_id=ag_id,
    )
    assert ok_v, msg_v
    assert vid is not None
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM venda_itens WHERE venda_id = ? AND servico_id = ?",
        (int(vid), sid),
    )
    vi_row = cur.fetchone()
    conn.close()
    assert vi_row
    vi_id = int(vi_row[0])
    ok_a, msg_a = associar_agendamento_pre_venda_a_item(ag_id, vi_id)
    assert ok_a, msg_a
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT modo_origem, venda_id FROM agendamentos WHERE id = ?", (ag_id,)
    )
    mo, vid2 = cur.fetchone()
    conn.close()
    assert str(mo) == "credito_venda"
    assert int(vid2) == int(vid)
    assert alterar_status(ag_id, "CONCLUIDO")[0]


def test_pre_venda_pacote_natureza_rejeita():
    cid = _cliente()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão PXP",
        "D",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=10.0,
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão PXP",))
    s1 = int(cur.fetchone()[0])
    conn.close()
    ok_p, _ = cadastrar_pacote(
        "Pacote PXP", "D", True, [(s1, 1, None)], None, 20.0, 50.0
    )
    assert ok_p
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Pacote PXP",))
    pid = int(cur.fetchone()[0])
    conn.close()
    ok, msg = criar_agendamento_pre_venda(
        int(cid), pid, "2030-03-01", "09:00", "10:00", [], "", None
    )
    assert not ok
    assert "pré-venda" in msg.lower() or "mvp" in msg.lower() or "sessão" in msg.lower()


def test_cancelar_pre_venda():
    cid = _cliente()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão CAN",
        "D",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=15.0,
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão CAN",))
    sid = int(cur.fetchone()[0])
    conn.close()
    ok, _ = criar_agendamento_pre_venda(
        int(cid), sid, "2030-04-01", "08:00", "09:00", [], "", None
    )
    assert ok
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM agendamentos ORDER BY id DESC LIMIT 1")
    ag_id = int(cur.fetchone()[0])
    conn.close()
    ok_c, msg_c = cancelar_agendamento(ag_id, devolver_ao_buffer=True)
    assert ok_c
    assert "pré-venda" in msg_c.lower()


def test_ui_cag_setor4_lista_dentro_expander_agendamentos():
    from tests.cag_setor4_ui_contract import assert_cag_setor4_lista_dentro_expander_agendamentos

    assert_cag_setor4_lista_dentro_expander_agendamentos()


def test_ui_cag_conversao_pacote_hoje_no_form_dados_agendamento():
    from tests.cag_setor4_ui_contract import assert_cag_conversao_pacote_hoje_no_form_dados_agendamento

    assert_cag_conversao_pacote_hoje_no_form_dados_agendamento()


def test_validar_tipo_atendimento_e_sala():
    ok, _, t, s = validar_tipo_atendimento_e_sala("presencial", None)
    assert ok and t == "presencial" and s is None
    ok2, msg2, _, _ = validar_tipo_atendimento_e_sala("virtual", None)
    assert not ok2 and msg2
    ok3, _, _, s3 = validar_tipo_atendimento_e_sala("virtual", 1)
    assert ok3 and s3 == 1
    ok4, _, _, s4 = validar_tipo_atendimento_e_sala("virtual", 0)
    assert ok4 and s4 == 0


def test_pre_venda_virtual_sem_sala_falha():
    cid = _cliente()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão Virt X",
        "D",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=33.0,
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão Virt X",))
    sid = int(cur.fetchone()[0])
    conn.close()
    ok, msg = criar_agendamento_pre_venda(
        int(cid),
        sid,
        "2031-03-01",
        "10:00",
        "11:00",
        [],
        "",
        None,
        tipo_atendimento="virtual",
        sala_virtual_disponibilizada=None,
    )
    assert not ok
    assert "sala virtual" in msg.lower()


def test_pre_venda_virtual_com_sala_persistido():
    cid = _cliente()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão Virt Y",
        "D",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=34.0,
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão Virt Y",))
    sid = int(cur.fetchone()[0])
    conn.close()
    ok, msg = criar_agendamento_pre_venda(
        int(cid),
        sid,
        "2031-03-02",
        "12:00",
        "13:00",
        [],
        "",
        None,
        tipo_atendimento="virtual",
        sala_virtual_disponibilizada=0,
    )
    assert ok, msg
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM agendamentos ORDER BY id DESC LIMIT 1")
    ag_id = int(cur.fetchone()[0])
    conn.close()
    ag = obter_agendamento(ag_id)
    assert ag is not None
    assert ag["tipo_atendimento"] == "virtual"
    assert ag["sala_virtual_disponibilizada"] == 0


def test_listar_agendamentos_elegiveis_associacao_inclui_pre_venda():
    cid = _cliente()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão Eleg Combo",
        "D",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=18.0,
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão Eleg Combo",))
    sid = int(cur.fetchone()[0])
    conn.close()
    ok, msg = criar_agendamento_pre_venda(
        int(cid), sid, "2032-04-10", "08:00", "09:00", [], "", None
    )
    assert ok, msg
    lst = listar_agendamentos_elegiveis_associacao_linha_venda(
        cliente_id=int(cid), servico_id=sid
    )
    assert any(int(a["id"]) > 0 and str(a["modo_origem"]) == "pre_venda" for a in lst)


def test_pos_venda_associar_integra_pre_venda_e_conclui():
    cid = _cliente()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão POSV",
        "D",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=30.0,
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão POSV",))
    sid = int(cur.fetchone()[0])
    conn.close()
    ok, msg = criar_agendamento_pre_venda(
        int(cid), sid, "2032-05-11", "10:00", "11:00", [], "", None
    )
    assert ok, msg
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM agendamentos ORDER BY id DESC LIMIT 1")
    ag_id = int(cur.fetchone()[0])
    conn.close()
    ok_v, msg_v, vid = registrar_venda(
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
        [("dinheiro", 3000)],
        [],
        "pos_venda test",
    )
    assert ok_v, msg_v
    assert vid is not None
    vi_ids = listar_venda_item_ids_em_ordem(int(vid))
    assert len(vi_ids) == 1
    msgs = pos_venda_associar_agendamentos_por_linha(
        venda_id=int(vid),
        cliente_id=int(cid),
        agendamento_ids_por_linha=[ag_id],
    )
    assert any("associada" in m.lower() or "✅" in m for m in msgs)
    ag2 = obter_agendamento(ag_id)
    assert ag2 is not None
    assert str(ag2.get("modo_origem")) == "credito_venda"
    assert str(ag2.get("status")) == "CONCLUIDO"


def test_pos_venda_associacao_parcial_venda_vai_para_rpp():
    cid = _cliente()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão POSV Parc",
        "D",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=44.0,
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão POSV Parc",))
    sid = int(cur.fetchone()[0])
    conn.close()
    ok, msg = criar_agendamento_pre_venda(
        int(cid), sid, "2032-06-01", "14:00", "15:00", [], "", None
    )
    assert ok, msg
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM agendamentos ORDER BY id DESC LIMIT 1")
    ag_id = int(cur.fetchone()[0])
    conn.close()
    ok_v, msg_v, vid = registrar_venda(
        int(cid),
        "parcial",
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
        [("dinheiro", 2200)],
        [("2033-01-15", 2200)],
        "parc test",
    )
    assert ok_v, msg_v
    assert vid is not None
    msgs = pos_venda_associar_agendamentos_por_linha(
        venda_id=int(vid),
        cliente_id=int(cid),
        agendamento_ids_por_linha=[ag_id],
    )
    assert any("associada" in m.lower() or "✅" in m for m in msgs)
    ag2 = obter_agendamento(ag_id)
    assert ag2 is not None
    assert str(ag2.get("status")) == "REALIZADO_PENDENTE_PGTO"


def test_listar_pendente_liquidacao_inclui_modo_pagamento_parcial_sem_previsto():
    cid = _cliente()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão Lista Pend ModoParc",
        "D",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=60.0,
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão Lista Pend ModoParc",))
    sid = int(cur.fetchone()[0])
    conn.close()
    ok, msg = criar_agendamento_pre_venda(
        int(cid), sid, "2033-03-10", "09:00", "10:00", [], "", None
    )
    assert ok, msg
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM agendamentos ORDER BY id DESC LIMIT 1")
    ag_id = int(cur.fetchone()[0])
    conn.close()
    ok_v, msg_v, vid = registrar_venda(
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
        [("dinheiro", 3000)],
        [],
        "lista pend modo parc",
        modo_pagamento_parcial_sem_previsto=True,
    )
    assert ok_v, msg_v
    assert vid is not None
    msgs = pos_venda_associar_agendamentos_por_linha(
        venda_id=int(vid),
        cliente_id=int(cid),
        agendamento_ids_por_linha=[ag_id],
    )
    assert any("associada" in m.lower() or "✅" in m for m in msgs)
    pend = listar_agendamentos_realizado_pendente_liquidacao_cliente(int(cid))
    ids = {int(p["agendamento_id"]) for p in pend}
    assert ag_id in ids
    assert any(int(p["aberto_venda_centavos"]) > 0 for p in pend if int(p["agendamento_id"]) == ag_id)


def test_listar_pendente_liquidacao_inclui_concluido_com_linha_pagamento_parcial():
    cid = _cliente()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão Lista Pend Conc",
        "D",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=50.0,
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão Lista Pend Conc",))
    sid = int(cur.fetchone()[0])
    conn.close()
    ok, msg = criar_agendamento_pre_venda(
        int(cid), sid, "2033-04-05", "11:00", "12:00", [], "", None
    )
    assert ok, msg
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM agendamentos ORDER BY id DESC LIMIT 1")
    ag_id = int(cur.fetchone()[0])
    conn.close()
    ok_v, msg_v, vid = registrar_venda(
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
        "lista conc parc",
        modo_pagamento_parcial_sem_previsto=True,
    )
    assert ok_v, msg_v
    assert vid is not None
    pos_venda_associar_agendamentos_por_linha(
        venda_id=int(vid),
        cliente_id=int(cid),
        agendamento_ids_por_linha=[ag_id],
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE agendamentos SET status = 'CONCLUIDO', data_alteracao = CURRENT_TIMESTAMP WHERE id = ?",
        (int(ag_id),),
    )
    conn.commit()
    conn.close()
    pend = listar_agendamentos_realizado_pendente_liquidacao_cliente(int(cid))
    ids = {int(p["agendamento_id"]) for p in pend}
    assert ag_id in ids


def _hoje_iso() -> str:
    return date.today().isoformat()[:10]


def test_elegivel_conversao_pacote_hoje_rejeita_data_nao_hoje():
    ref = date(2026, 4, 14)
    ag = {
        "status": "AGENDADO",
        "data_agendamento": "2026-04-13",
        "tipo_origem": "sessao_avulsa",
    }
    ok, msg = agendamento_elegivel_conversao_para_pacote_hoje(ag, data_referencia=ref)
    assert not ok
    assert "hoje" in msg.lower()


def test_elegivel_conversao_pacote_hoje_rejeita_rpp_e_concluido():
    ref = date(2026, 5, 1)
    ag_rpp = {
        "status": "REALIZADO_PENDENTE_PGTO",
        "data_agendamento": "2026-05-01",
        "tipo_origem": "sessao_avulsa",
    }
    ok_r, msg_r = agendamento_elegivel_conversao_para_pacote_hoje(ag_rpp, data_referencia=ref)
    assert not ok_r
    assert "estado" in msg_r.lower() or "pendente" in msg_r.lower()

    ag_conc = {
        "status": "CONCLUIDO",
        "data_agendamento": "2026-05-01",
        "tipo_origem": "sessao_avulsa",
    }
    ok_x, msg_x = agendamento_elegivel_conversao_para_pacote_hoje(ag_conc, data_referencia=ref)
    assert not ok_x
    assert "estado" in msg_x.lower() or "concluído" in msg_x.lower()

    ag_ok = {
        "status": "AGENDADO",
        "data_agendamento": "2026-05-01",
        "tipo_origem": "sessao_avulsa",
    }
    ok_o, msg_o = agendamento_elegivel_conversao_para_pacote_hoje(ag_ok, data_referencia=ref)
    assert ok_o, msg_o


def test_elegivel_conversao_pacote_hoje_rejeita_ja_pacote():
    ref = date(2026, 6, 10)
    ag = {
        "status": "AGENDADO",
        "data_agendamento": "2026-06-10",
        "tipo_origem": "pacote",
    }
    ok, msg = agendamento_elegivel_conversao_para_pacote_hoje(ag, data_referencia=ref)
    assert not ok
    assert "pacote" in msg.lower()


def test_listar_buckets_pacote_com_saldo_disponivel_filtra():
    cid = _cliente()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão LstPacFil",
        "D",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=35.0,
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão LstPacFil",))
    sid = int(cur.fetchone()[0])
    conn.close()
    ok_p, msg_p = cadastrar_pacote(
        "Pacote LstPacFil",
        "D.",
        True,
        [(sid, 1, None)],
        None,
        30.0,
        60.0,
    )
    assert ok_p, msg_p
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Pacote LstPacFil",))
    pid = int(cur.fetchone()[0])
    cur.execute(
        "SELECT id FROM servico_pacote_sessoes WHERE pacote_servico_id = ?",
        (pid,),
    )
    psid = int(cur.fetchone()[0])
    conn.close()
    ok_v, msg_v, _ = registrar_venda(
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
        [("dinheiro", 6000)],
        [],
        "",
    )
    assert ok_v, msg_v
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM venda_itens ORDER BY id DESC LIMIT 1")
    vi_pac = int(cur.fetchone()[0])
    conn.close()
    ok_vs, msg_vs, _ = registrar_venda(
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
        [("dinheiro", 3500)],
        [],
        "",
    )
    assert ok_vs, msg_vs
    buckets = listar_buckets_pacote_com_saldo_disponivel(int(cid))
    assert len(buckets) >= 1
    assert all(str(b.get("tipo_origem") or "") == "pacote" for b in buckets)
    assert all(int(b.get("saldo") or 0) >= 1 for b in buckets)
    assert any(int(b["venda_item_id"]) == vi_pac and int(b["pacote_sessao_id"]) == psid for b in buckets)


def test_converter_sessao_avulsa_para_pacote_hoje_ok():
    cid = _cliente()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão ConvPacOk",
        "D",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=40.0,
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão ConvPacOk",))
    sid = int(cur.fetchone()[0])
    conn.close()
    ok_p, msg_p = cadastrar_pacote(
        "Pacote ConvPacOk",
        "D.",
        True,
        [(sid, 2, None)],
        None,
        50.0,
        100.0,
    )
    assert ok_p, msg_p
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Pacote ConvPacOk",))
    pid = int(cur.fetchone()[0])
    cur.execute(
        "SELECT id FROM servico_pacote_sessoes WHERE pacote_servico_id = ?",
        (pid,),
    )
    psid = int(cur.fetchone()[0])
    conn.close()

    ok_vp, msg_vp, _ = registrar_venda(
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
    assert ok_vp, msg_vp
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM venda_itens ORDER BY id DESC LIMIT 1")
    vi_pac = int(cur.fetchone()[0])
    assert saldo_bucket(cur, vi_pac, psid) == 2
    conn.close()

    ok_vs, msg_vs, _ = registrar_venda(
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
        [("dinheiro", 4000)],
        [],
        "",
    )
    assert ok_vs, msg_vs
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM venda_itens ORDER BY id DESC LIMIT 1")
    vi_sess = int(cur.fetchone()[0])
    conn.close()

    hoje = _hoje_iso()
    ok_a, msg_a = criar_agendamento(
        vi_sess, None, hoje, "09:00", "10:00", [], ""
    )
    assert ok_a, msg_a
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM agendamentos ORDER BY id DESC LIMIT 1")
    ag_id = int(cur.fetchone()[0])
    conn.close()

    ok_c, msg_c = converter_agendamento_avulso_para_consumo_pacote(
        ag_id, vi_pac, psid, actor="pytest"
    )
    assert ok_c, msg_c
    conn = get_connection()
    cur = conn.cursor()
    assert saldo_bucket(cur, vi_pac, psid) == 1
    conn.close()
    ag2 = obter_agendamento(ag_id)
    assert ag2 is not None
    assert str(ag2.get("tipo_origem")) == "pacote"
    assert str(ag2.get("modo_origem")) == "credito_venda"
    assert int(ag2.get("venda_item_id") or 0) == vi_pac
    assert int(ag2.get("pacote_sessao_id") or 0) == psid
    assert ag2.get("preco_referencia_centavos") is None


def test_converter_rejeita_servico_diferente_do_componente_pacote():
    cid = _cliente()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão ConvPacA",
        "D",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=30.0,
    )
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão ConvPacB",
        "D",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=31.0,
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão ConvPacA",))
    sid_a = int(cur.fetchone()[0])
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão ConvPacB",))
    sid_b = int(cur.fetchone()[0])
    conn.close()
    ok_p, _ = cadastrar_pacote(
        "Pacote SóA",
        "D.",
        True,
        [(sid_a, 1, None)],
        None,
        20.0,
        40.0,
    )
    assert ok_p
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Pacote SóA",))
    pid = int(cur.fetchone()[0])
    cur.execute(
        "SELECT id FROM servico_pacote_sessoes WHERE pacote_servico_id = ?",
        (pid,),
    )
    psid = int(cur.fetchone()[0])
    conn.close()
    ok_vp, msg_vp, _ = registrar_venda(
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
        [("dinheiro", 4000)],
        [],
        "",
    )
    assert ok_vp, msg_vp
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM venda_itens ORDER BY id DESC LIMIT 1")
    vi_pac = int(cur.fetchone()[0])
    conn.close()
    ok_vs, msg_vs, _ = registrar_venda(
        int(cid),
        "integral",
        [
            {
                "servico_id": sid_b,
                "quantidade": 1,
                "is_bonus": False,
                "evento_preco": None,
                "desconto_linha_tipo": "none",
                "desconto_linha_valor": None,
            }
        ],
        None,
        None,
        [("dinheiro", 3100)],
        [],
        "",
    )
    assert ok_vs, msg_vs
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM venda_itens ORDER BY id DESC LIMIT 1")
    vi_b = int(cur.fetchone()[0])
    conn.close()
    hoje = _hoje_iso()
    ok_a, _ = criar_agendamento(vi_b, None, hoje, "11:00", "12:00", [], "")
    assert ok_a
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM agendamentos ORDER BY id DESC LIMIT 1")
    ag_id = int(cur.fetchone()[0])
    conn.close()
    ok_c, msg_c = converter_agendamento_avulso_para_consumo_pacote(ag_id, vi_pac, psid)
    assert not ok_c
    assert "coincide" in msg_c.lower() or "componente" in msg_c.lower()


def test_converter_rejeita_repasse_fora_de_pendente():
    cid = _cliente()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão ConvPacRep",
        "D",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=40.0,
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão ConvPacRep",))
    sid = int(cur.fetchone()[0])
    conn.close()
    ok_col, _ = cadastrar_colaborador(
        nome="Colab ConvPacRep",
        sexo="Feminino",
        data_nascimento="1990-05-10",
        endereco_rua="Rua R",
        endereco_numero="1",
        endereco_complemento="",
        codigo_postal="4000-001",
        concelho="Porto",
        freguesia="Centro",
        distrito="",
        pais="Portugal",
        email="colab.convpac@beaba.test",
        nif_ou_documento="123456789",
        identificacao_internacional=False,
        numero_contato="91222222222",
        observacoes="",
        servicos_repasse=[(sid, 20.0, "2026-01-01")],
        iban_dados_bancarios="PT50000201231234567890152",
    )
    assert ok_col
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM colaboradores WHERE nome = ?", ("Colab ConvPacRep",))
    colab_id = int(cur.fetchone()[0])
    conn.close()

    ok_p, _ = cadastrar_pacote(
        "Pacote ConvPacRep",
        "D.",
        True,
        [(sid, 1, None)],
        None,
        25.0,
        50.0,
    )
    assert ok_p
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Pacote ConvPacRep",))
    pid = int(cur.fetchone()[0])
    cur.execute(
        "SELECT id FROM servico_pacote_sessoes WHERE pacote_servico_id = ?",
        (pid,),
    )
    psid = int(cur.fetchone()[0])
    conn.close()
    ok_vp, msg_vp, _ = registrar_venda(
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
        [("dinheiro", 5000)],
        [],
        "",
    )
    assert ok_vp, msg_vp
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM venda_itens ORDER BY id DESC LIMIT 1")
    vi_pac = int(cur.fetchone()[0])
    conn.close()
    ok_vs, msg_vs, _ = registrar_venda(
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
        [("dinheiro", 4000)],
        [],
        "",
    )
    assert ok_vs, msg_vs
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM venda_itens ORDER BY id DESC LIMIT 1")
    vi_sess = int(cur.fetchone()[0])
    conn.close()
    hoje = _hoje_iso()
    ok_a, _ = criar_agendamento(vi_sess, None, hoje, "14:00", "15:00", [], "")
    assert ok_a
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM agendamentos ORDER BY id DESC LIMIT 1")
    ag_id = int(cur.fetchone()[0])
    cur.execute(
        """
        INSERT INTO repasse_linhas (
            agendamento_id, colaborador_id, base_calculo_centavos,
            percentual_bp, valor_repasse_centavos, status_repasse
        ) VALUES (?, ?, 4000, 2000, 800, 'REPASSE_PAGO')
        """,
        (ag_id, colab_id),
    )
    conn.commit()
    conn.close()
    ok_c, msg_c = converter_agendamento_avulso_para_consumo_pacote(ag_id, vi_pac, psid)
    assert not ok_c
    assert "repasse" in msg_c.lower()


def test_converter_apaga_repasse_pendente_e_converte():
    cid = _cliente()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão ConvPacPen",
        "D",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=40.0,
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão ConvPacPen",))
    sid = int(cur.fetchone()[0])
    conn.close()
    ok_col, _ = cadastrar_colaborador(
        nome="Colab ConvPacPen",
        sexo="Masculino",
        data_nascimento="1991-06-11",
        endereco_rua="Rua P",
        endereco_numero="2",
        endereco_complemento="",
        codigo_postal="4100-002",
        concelho="Porto",
        freguesia="Paranhos",
        distrito="",
        pais="Portugal",
        email="colab.pen@beaba.test",
        nif_ou_documento="123456789",
        identificacao_internacional=False,
        numero_contato="91333333333",
        observacoes="",
        servicos_repasse=[(sid, 15.0, "2026-01-01")],
        iban_dados_bancarios="PT50000201231234567890152",
    )
    assert ok_col
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM colaboradores WHERE nome = ?", ("Colab ConvPacPen",))
    colab_id = int(cur.fetchone()[0])
    conn.close()

    ok_p, _ = cadastrar_pacote(
        "Pacote ConvPacPen",
        "D.",
        True,
        [(sid, 1, None)],
        None,
        25.0,
        50.0,
    )
    assert ok_p
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Pacote ConvPacPen",))
    pid = int(cur.fetchone()[0])
    cur.execute(
        "SELECT id FROM servico_pacote_sessoes WHERE pacote_servico_id = ?",
        (pid,),
    )
    psid = int(cur.fetchone()[0])
    conn.close()
    ok_vp, msg_vp, _ = registrar_venda(
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
        [("dinheiro", 5000)],
        [],
        "",
    )
    assert ok_vp, msg_vp
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM venda_itens ORDER BY id DESC LIMIT 1")
    vi_pac = int(cur.fetchone()[0])
    conn.close()
    ok_vs, msg_vs, _ = registrar_venda(
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
        [("dinheiro", 4000)],
        [],
        "",
    )
    assert ok_vs, msg_vs
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM venda_itens ORDER BY id DESC LIMIT 1")
    vi_sess = int(cur.fetchone()[0])
    conn.close()
    hoje = _hoje_iso()
    ok_a, _ = criar_agendamento(vi_sess, None, hoje, "16:00", "17:00", [], "")
    assert ok_a
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM agendamentos ORDER BY id DESC LIMIT 1")
    ag_id = int(cur.fetchone()[0])
    cur.execute(
        """
        INSERT INTO repasse_linhas (
            agendamento_id, colaborador_id, base_calculo_centavos,
            percentual_bp, valor_repasse_centavos, status_repasse
        ) VALUES (?, ?, 4000, 1500, 600, 'PENDENTE_REPASSE')
        """,
        (ag_id, colab_id),
    )
    conn.commit()
    assert int(
        cur.execute(
            "SELECT COUNT(*) FROM repasse_linhas WHERE agendamento_id = ?",
            (ag_id,),
        ).fetchone()[0]
    ) == 1
    conn.close()

    ok_c, msg_c = converter_agendamento_avulso_para_consumo_pacote(ag_id, vi_pac, psid)
    assert ok_c, msg_c
    conn = get_connection()
    cur = conn.cursor()
    assert (
        int(
            cur.execute(
                "SELECT COUNT(*) FROM repasse_linhas WHERE agendamento_id = ?",
                (ag_id,),
            ).fetchone()[0]
        )
        == 0
    )
    conn.close()


def test_analisar_sessoes_pacote_pendentes_cag_quatro_unidades_e_cancelamento():
    """Uma opção por unidade (sem «×4»); cancelamento repõe pendência."""
    cid = _cliente()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão Psy CAG Pend",
        "d",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=40.0,
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão Psy CAG Pend",))
    s1 = int(cur.fetchone()[0])
    conn.close()
    ok_p, msg_p = cadastrar_pacote(
        "Pacote Psy 4x CAG",
        "d",
        True,
        [(s1, 4, None)],
        None,
        40.0,
        200.0,
    )
    assert ok_p, msg_p
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Pacote Psy 4x CAG",))
    pid = int(cur.fetchone()[0])
    cur.execute("SELECT id FROM servico_pacote_sessoes WHERE pacote_servico_id = ?", (pid,))
    psid = int(cur.fetchone()[0])
    conn.close()

    tot, opts = analisar_sessoes_pacote_pendentes_cag(int(cid), pid)
    assert tot == 4
    assert len(opts) == 4
    assert all(lab == "Sessão Psy CAG Pend" for _v, lab in opts)
    assert contar_total_sessoes_pacote_pendentes_agendamento(int(cid), pid) == 4

    ok, msg = criar_agendamento_pre_venda(
        int(cid),
        s1,
        "2031-03-10",
        "09:00",
        "10:00",
        [],
        "",
        None,
        tipo_atendimento="presencial",
        sala_virtual_disponibilizada=None,
        pacote_sessao_id=psid,
    )
    assert ok, msg
    tot2, opts2 = analisar_sessoes_pacote_pendentes_cag(int(cid), pid)
    assert tot2 == 3
    assert len(opts2) == 3

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM agendamentos ORDER BY id DESC LIMIT 1")
    ag = int(cur.fetchone()[0])
    conn.close()
    ok_c, _ = cancelar_agendamento(ag, devolver_ao_buffer=False)
    assert ok_c
    tot3, opts3 = analisar_sessoes_pacote_pendentes_cag(int(cid), pid)
    assert tot3 == 4
    assert len(opts3) == 4


def test_listar_opcoes_servicos_adquiridos_pendente_pre_agendamento_smoke():
    cid = _cliente()
    assert cid is not None
    opts = listar_opcoes_servicos_adquiridos_pendente_pre_agendamento(int(cid))
    assert isinstance(opts, list)
    for row in opts:
        assert "token" in row and "rotulo" in row and "venda_item_id" in row


def test_listar_opcoes_sap_pacote_uma_entrada_por_venda_item_tres_cancelamentos():
    """Três créditos devolvidos do mesmo pacote → 1 linha SAP (`…|pkg`), não 3."""
    cid = _cliente()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão SapPkg1",
        "D",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=40.0,
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão SapPkg1",))
    s1 = int(cur.fetchone()[0])
    conn.close()
    ok_p, msg_p = cadastrar_pacote(
        "Pacote SapPkg1",
        "D.",
        True,
        [(s1, 3, None)],
        None,
        50.0,
        100.0,
    )
    assert ok_p, msg_p
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Pacote SapPkg1",))
    pid = int(cur.fetchone()[0])
    cur.execute(
        "SELECT id FROM servico_pacote_sessoes WHERE pacote_servico_id = ?",
        (pid,),
    )
    psid = int(cur.fetchone()[0])
    conn.close()
    ok_v, msg_v, _ = registrar_venda(
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
    assert ok_v, msg_v
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM venda_itens ORDER BY id DESC LIMIT 1")
    vi_id = int(cur.fetchone()[0])
    conn.close()
    for d_off in range(3):
        ok_a, _ = criar_agendamento(
            vi_id,
            psid,
            f"2026-07-{10 + d_off:02d}",
            "09:00",
            "10:00",
            [],
            "",
        )
        assert ok_a
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM agendamentos WHERE venda_item_id = ? ORDER BY id ASC",
        (vi_id,),
    )
    aids = [int(r[0]) for r in cur.fetchall()]
    conn.close()
    assert len(aids) == 3
    for aid in aids:
        ok_c, _ = cancelar_agendamento(aid, devolver_ao_buffer=True)
        assert ok_c
    opts = listar_opcoes_servicos_adquiridos_pendente_pre_agendamento(int(cid))
    pkg_opts = [o for o in opts if str(o.get("token") or "").endswith("|pkg")]
    assert len(pkg_opts) == 1
    assert int(pkg_opts[0]["venda_item_id"]) == vi_id
    assert pkg_opts[0].get("pacote_sessao_esc") is None
    tot, op_l = analisar_sessoes_pacote_pendentes_cag(int(cid), pid)
    assert tot == 3
    assert len(op_l) == 3


def test_credito_cancelamento_pacote_prorata_tres_sessoes_nao_triplica_valor_pacote():
    """Crédito por cancelamento = total_linha / sessões oficiais do catálogo (× qty linha)."""
    cid = _cliente()
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão CredProrata",
        "D",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=50.0,
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Sessão CredProrata",))
    s1 = int(cur.fetchone()[0])
    conn.close()
    ok_p, msg_p = cadastrar_pacote(
        "Pacote CredProrata",
        "D.",
        True,
        [(s1, 3, None)],
        None,
        40.0,
        100.0,
    )
    assert ok_p, msg_p
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Pacote CredProrata",))
    pid = int(cur.fetchone()[0])
    cur.execute(
        "SELECT id FROM servico_pacote_sessoes WHERE pacote_servico_id = ?",
        (pid,),
    )
    psid = int(cur.fetchone()[0])
    conn.close()
    ok_v, msg_v, _ = registrar_venda(
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
    assert ok_v, msg_v
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM venda_itens ORDER BY id DESC LIMIT 1")
    vi_id = int(cur.fetchone()[0])
    conn.close()
    aids = []
    for d_off in range(3):
        ok_a, _ = criar_agendamento(
            vi_id,
            psid,
            f"2026-08-{10 + d_off:02d}",
            "09:00",
            "10:00",
            [],
            "",
        )
        assert ok_a
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM agendamentos ORDER BY id DESC LIMIT 1")
        aids.append(int(cur.fetchone()[0]))
        conn.close()
    for aid in aids:
        ok_c, _ = cancelar_agendamento(
            aid,
            devolver_ao_buffer=True,
            converter_valor_pago_em_credito_loja=True,
        )
        assert ok_c
    # 10000 // 3 = 3333 por sessão; 3 cancelamentos → 9999 (1 cêntimo de resto em divisão inteira)
    assert obter_saldo_credito_cliente(int(cid)) == 9999
