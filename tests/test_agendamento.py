import pytest

from src.database.connection import get_connection
from src.modules.agendamento import (
    alterar_status,
    associar_agendamento_pre_venda_a_item,
    cancelar_agendamento,
    contar_pre_venda_futuros,
    criar_agendamento,
    criar_agendamento_pre_venda,
    listar_agendamentos_elegiveis_associacao_linha_venda,
    listar_buckets_credito_cliente,
    obter_agendamento,
    pos_venda_associar_agendamentos_por_linha,
    saldo_bucket,
    validar_intervalo_horario,
    validar_tipo_atendimento_e_sala,
)
from src.modules.catalogo import cadastrar_pacote, cadastrar_servico_fase1
from src.modules.cliente import buscar_cliente_por_whatsapp, cadastrar_cliente
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
