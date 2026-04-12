"""Fase 2 — métricas SQL do cockpit Home (donuts + cards)."""

from __future__ import annotations

import uuid
from datetime import date

from src.database.connection import get_connection
from src.modules.catalogo import cadastrar_servico_fase1
from src.modules.cliente import buscar_cliente_por_whatsapp, cadastrar_cliente
from src.modules.home_cockpit_metrics import (
    HomeCockpitSnapshot,
    _week_sunday_to_saturday,
    obter_home_cockpit_snapshot,
    obter_home_evolucao_atendimentos,
)
from src.ui.fmt_euro_constituicao import fmt_euro_centavos


def _seed_cliente_servico() -> tuple[int, int]:
    suf = uuid.uuid4().hex[:8]
    phone = f"912{(int(suf, 16) % 10**6):06d}"
    nif = "123456789"
    ok, _ = cadastrar_cliente(
        nome="Cliente Home Cockpit",
        numero_contato=phone,
        endereco_rua="Rua H",
        endereco_numero="1",
        endereco_complemento="",
        codigo_postal="4000-002",
        concelho="Porto",
        freguesia="Centro",
        distrito="",
        pais="Portugal",
        email=f"homecockpit_{suf}@example.com",
        sexo="Outro",
        tem_filhos=False,
        filhos=[],
        gravida=None,
        data_parto_prevista=None,
        observacoes="",
        contatos_emergencia=[],
        nif=nif,
        documento_identificacao_internacional=False,
        data_nascimento="1991-06-01",
    )
    assert ok
    cid = int(buscar_cliente_por_whatsapp(phone))
    nome_srv = f"Sessão Home Cockpit T {suf}"
    cadastrar_servico_fase1(
        "Sessão",
        nome_srv,
        "Desc.",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=42.0,
    )
    conn = get_connection()
    assert conn
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM servicos WHERE nome = ?", (nome_srv,))
        sid = int(cur.fetchone()[0])
        return cid, sid
    finally:
        conn.close()


def _insert_pre(
    cur,
    *,
    cid: int,
    sid: int,
    d: str,
    status: str,
    preco_ref: int | None = 6000,
) -> None:
    cur.execute(
        """
        INSERT INTO agendamentos (
            cliente_id, servico_id, tipo_origem, data_agendamento,
            hora_inicio, hora_fim, status, devolver_ao_buffer, observacoes,
            modo_origem, preco_referencia_centavos
        ) VALUES (?, ?, 'sessao_avulsa', ?, '09:00', '10:00', ?, 0, '', 'pre_venda', ?)
        """,
        (cid, sid, d, status, preco_ref),
    )


def test_week_sunday_to_saturday_contains_ref():
    ref = date(2026, 6, 11)
    sun, sat = _week_sunday_to_saturday(ref)
    assert sun == date(2026, 6, 7)
    assert sat == date(2026, 6, 13)
    assert sun <= ref <= sat


def test_obter_home_evolucao_atendimentos_base_vazia():
    e = obter_home_evolucao_atendimentos(ref=date(2099, 1, 15))
    assert e is not None
    assert e.variacao_semanal_delta == 0
    assert e.desempenho_mensal_pct is None
    assert "—" in e.desempenho_pct_label()


def test_obter_home_cockpit_snapshot_base_vazia():
    s = obter_home_cockpit_snapshot(ref=date(2099, 1, 15))
    assert s is not None
    assert isinstance(s, HomeCockpitSnapshot)
    assert s.donut1_confirmados_hoje == 0
    assert s.donut3_taxa_cancelamento_pct is None
    assert s.donut3_pct_label() == "- %"
    assert s.card1_valor_fmt() == fmt_euro_centavos(0)
    assert s.card4_valor_fmt() == fmt_euro_centavos(0)


def test_obter_home_cockpit_snapshot_com_dados():
    cid, sid = _seed_cliente_servico()
    ref = date(2026, 6, 11)
    d_today = ref.isoformat()
    d_week = "2026-06-09"
    d_month_other = "2026-06-20"

    conn = get_connection()
    assert conn
    try:
        cur = conn.cursor()
        _insert_pre(cur, cid=cid, sid=sid, d=d_today, status="CONFIRMADO", preco_ref=5000)
        _insert_pre(cur, cid=cid, sid=sid, d=d_week, status="AGENDADO", preco_ref=4000)
        _insert_pre(cur, cid=cid, sid=sid, d=d_month_other, status="CANCELADO", preco_ref=3000)
        for _ in range(3):
            _insert_pre(cur, cid=cid, sid=sid, d=d_month_other, status="CONFIRMADO", preco_ref=2000)
        _insert_pre(cur, cid=cid, sid=sid, d=d_month_other, status="PRE_AGENDADO", preco_ref=1000)
        _insert_pre(cur, cid=cid, sid=sid, d=d_month_other, status="AGENDADO", preco_ref=7000)
        cur.execute(
            """
            INSERT INTO credito_movimentos (
                cliente_id, tipo_movimento, valor_centavos,
                referencia_tipo, referencia_id, observacoes
            ) VALUES (?, 'CREDITO_CANCELAMENTO', 15000, 'agendamento', 999001, 'teste')
            """,
            (cid,),
        )
        conn.commit()
    finally:
        conn.close()

    s = obter_home_cockpit_snapshot(ref=ref)
    assert s is not None
    assert s.donut1_confirmados_hoje == 1
    assert s.donut1_previstos_semana >= 2
    assert s.donut2_agendados_e_confirmados_semana >= 2
    assert s.donut3_cancelados_mes == 1
    assert s.donut3_confirmados_mes == 4
    assert s.donut3_taxa_cancelamento_pct is not None
    assert abs(s.donut3_taxa_cancelamento_pct - 25.0) < 0.01
    assert s.card2_total_nao_confirmados_mes == 3
    assert s.card3_pre_agendados_mes == 1
    assert s.card1_estimativa_nao_confirmados_centavos == 12000
    assert s.card1_valor_fmt() == fmt_euro_centavos(12000)
    assert s.card4_saldo_credito_pos_cancel_sim_centavos >= 15000
