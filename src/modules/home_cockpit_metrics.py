"""
Métricas do cockpit da Página de Boas-vindas (Fase 2 — dados).

Regras de cálculo alinhadas a `Pagina de Boas-vindas.txt` e ao schema SQLite actual.
Valores monetários em centavos internamente; formatação para UI com `fmt_euro_centavos`.

Sem novas tabelas: E17 continua a copiar o `.db` integral (agendamentos, credito_movimentos, vw_cliente_saldo_credito).
"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any

from src.database.connection import get_connection
from src.ui.fmt_euro_constituicao import fmt_euro_centavos


def _week_sunday_to_saturday(d: date) -> tuple[date, date]:
    """Semana corrente: Domingo → Sábado (inclusive), contendo `d`."""
    days_since_sun = (d.weekday() + 1) % 7
    sun = d - timedelta(days=days_since_sun)
    sat = sun + timedelta(days=6)
    return sun, sat


def _month_bounds(d: date) -> tuple[str, str]:
    """(primeiro_dia, último_dia) ISO para filtros `data_agendamento`."""
    first = date(d.year, d.month, 1)
    _, last_day = monthrange(d.year, d.month)
    last = date(d.year, d.month, last_day)
    return first.isoformat(), last.isoformat()


@dataclass(frozen=True)
class HomeCockpitSnapshot:
    """Valores brutos + etiquetas formatadas (€ via Master)."""

    referencia_data_iso: str

    donut1_confirmados_hoje: int
    donut1_previstos_semana: int

    donut2_agendados_e_confirmados_semana: int

    donut3_cancelados_mes: int
    donut3_confirmados_mes: int
    donut3_taxa_cancelamento_pct: float | None

    card1_estimativa_nao_confirmados_centavos: int
    card2_total_nao_confirmados_mes: int
    card3_pre_agendados_mes: int
    card4_saldo_credito_pos_cancel_sim_centavos: int

    def donut3_pct_label(self) -> str:
        if self.donut3_taxa_cancelamento_pct is None:
            return "- %"
        return f"{self.donut3_taxa_cancelamento_pct:.1f} %"

    def card1_valor_fmt(self) -> str:
        return fmt_euro_centavos(int(self.card1_estimativa_nao_confirmados_centavos))

    def card4_valor_fmt(self) -> str:
        return fmt_euro_centavos(int(self.card4_saldo_credito_pos_cancel_sim_centavos))

    def to_raw_dict(self) -> dict[str, Any]:
        """Serialização para conferência (script / relatório)."""
        d = asdict(self)
        d["donut3_pct_label"] = self.donut3_pct_label()
        d["card1_valor_fmt"] = self.card1_valor_fmt()
        d["card4_valor_fmt"] = self.card4_valor_fmt()
        return d


def _estimativa_centavos_row(
    cur,
    *,
    data_inicio_mes: str,
    data_fim_mes: str,
) -> int:
    """
    Soma estimativa em centavos: agendamentos do mês com status ≠ CONFIRMADO e ≠ CANCELADO.
    pre_venda: COALESCE(preco_referencia_centavos, fallback catálogo).
    credito_venda: preco_unitario_centavos da linha de venda (fallback total_linha).
    """
    cur.execute(
        """
        SELECT COALESCE(SUM(
            CASE
                WHEN a.modo_origem = 'pre_venda' THEN
                    COALESCE(
                        a.preco_referencia_centavos,
                        CASE s.natureza
                            WHEN 'Sessão' THEN COALESCE(s.sessao_valor_centavos, 0)
                            WHEN 'Coworking' THEN COALESCE(s.cowork_valor_centavos, 0)
                            WHEN 'Evento' THEN COALESCE(
                                NULLIF(s.evento_preco_adulto_centavos, 0),
                                s.evento_preco_crianca_centavos,
                                0
                            )
                            ELSE 0
                        END
                    )
                ELSE COALESCE(vi.preco_unitario_centavos, vi.total_linha_centavos, 0)
            END
        ), 0)
        FROM agendamentos a
        JOIN servicos s ON s.id = a.servico_id
        LEFT JOIN venda_itens vi ON vi.id = a.venda_item_id
        WHERE a.data_agendamento >= ? AND a.data_agendamento <= ?
          AND a.status NOT IN ('CONFIRMADO', 'CANCELADO')
        """,
        (data_inicio_mes, data_fim_mes),
    )
    row = cur.fetchone()
    return int(row[0] or 0)


def obter_home_cockpit_snapshot(ref: date | None = None) -> HomeCockpitSnapshot | None:
    """
    Calcula todas as métricas para `ref` (defeito: hoje, timezone local da app).
    Retorna None apenas se não houver ligação à base.
    """
    d = ref or date.today()
    conn = get_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        today_iso = d.isoformat()
        w0, w1 = _week_sunday_to_saturday(d)
        w_start, w_end = w0.isoformat(), w1.isoformat()
        m_start, m_end = _month_bounds(d)

        cur.execute(
            """
            SELECT COUNT(*) FROM agendamentos
            WHERE status = 'CONFIRMADO'
              AND substr(data_agendamento, 1, 10) = ?
            """,
            (today_iso,),
        )
        donut1_conf_hoje = int(cur.fetchone()[0])

        cur.execute(
            """
            SELECT COUNT(*) FROM agendamentos
            WHERE status != 'CANCELADO'
              AND data_agendamento >= ? AND data_agendamento <= ?
            """,
            (w_start, w_end),
        )
        donut1_prev_sem = int(cur.fetchone()[0])

        cur.execute(
            """
            SELECT COUNT(*) FROM agendamentos
            WHERE status IN ('AGENDADO', 'CONFIRMADO')
              AND data_agendamento >= ? AND data_agendamento <= ?
            """,
            (w_start, w_end),
        )
        donut2 = int(cur.fetchone()[0])

        cur.execute(
            """
            SELECT COUNT(*) FROM agendamentos
            WHERE status = 'CANCELADO'
              AND data_agendamento >= ? AND data_agendamento <= ?
            """,
            (m_start, m_end),
        )
        c_cancel = int(cur.fetchone()[0])

        cur.execute(
            """
            SELECT COUNT(*) FROM agendamentos
            WHERE status = 'CONFIRMADO'
              AND data_agendamento >= ? AND data_agendamento <= ?
            """,
            (m_start, m_end),
        )
        c_conf_mes = int(cur.fetchone()[0])

        if c_conf_mes == 0:
            taxa: float | None = None
        else:
            taxa = 100.0 * (c_cancel / c_conf_mes)

        c1_cent = _estimativa_centavos_row(cur, data_inicio_mes=m_start, data_fim_mes=m_end)

        cur.execute(
            """
            SELECT COUNT(*) FROM agendamentos
            WHERE data_agendamento >= ? AND data_agendamento <= ?
              AND status NOT IN ('CONFIRMADO', 'CANCELADO')
            """,
            (m_start, m_end),
        )
        c2 = int(cur.fetchone()[0])

        cur.execute(
            """
            SELECT COUNT(*) FROM agendamentos
            WHERE status = 'PRE_AGENDADO'
              AND data_agendamento >= ? AND data_agendamento <= ?
            """,
            (m_start, m_end),
        )
        c3 = int(cur.fetchone()[0])

        # Card 4: saldo positivo actual de clientes que alguma vez receberam CREDITO_CANCELAMENTO
        # (fluxo «SIM» em «Saldo de Pagamento Encontrado» ao cancelar).
        cur.execute(
            """
            SELECT COALESCE(SUM(v.saldo_credito_centavos), 0)
            FROM vw_cliente_saldo_credito v
            WHERE v.saldo_credito_centavos > 0
              AND EXISTS (
                SELECT 1 FROM credito_movimentos m
                WHERE m.cliente_id = v.cliente_id
                  AND m.tipo_movimento = 'CREDITO_CANCELAMENTO'
              )
            """
        )
        c4 = int(cur.fetchone()[0])

        return HomeCockpitSnapshot(
            referencia_data_iso=today_iso,
            donut1_confirmados_hoje=donut1_conf_hoje,
            donut1_previstos_semana=donut1_prev_sem,
            donut2_agendados_e_confirmados_semana=donut2,
            donut3_cancelados_mes=c_cancel,
            donut3_confirmados_mes=c_conf_mes,
            donut3_taxa_cancelamento_pct=taxa,
            card1_estimativa_nao_confirmados_centavos=c1_cent,
            card2_total_nao_confirmados_mes=c2,
            card3_pre_agendados_mes=c3,
            card4_saldo_credito_pos_cancel_sim_centavos=c4,
        )
    finally:
        conn.close()


@dataclass(frozen=True)
class HomeEvolucaoMetrics:
    """Secção «Evolução de Atendimentos» (Boas-vindas)."""

    ref_data_iso: str
    semana_confirmados_atual: int
    semana_confirmados_anterior: int
    variacao_semanal_delta: int
    mes_concluidos_atual: int
    mes_concluidos_anterior: int
    desempenho_mensal_pct: float | None

    def desempenho_pct_label(self) -> str:
        if self.desempenho_mensal_pct is None:
            return "—"
        v = self.desempenho_mensal_pct
        sign = "+" if v > 0 else ""
        return f"{sign}{v:.1f} %"


def obter_home_evolucao_atendimentos(ref: date | None = None) -> HomeEvolucaoMetrics | None:
    """CONFIRMADOS por semana (dom–sáb) vs semana anterior; CONCLUÍDOS mês vs mês anterior."""
    d = ref or date.today()
    conn = get_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        w0, w1 = _week_sunday_to_saturday(d)
        p1_end = w0 - timedelta(days=1)
        p0 = p1_end - timedelta(days=6)
        cur.execute(
            """
            SELECT COUNT(*) FROM agendamentos
            WHERE status = 'CONFIRMADO'
              AND data_agendamento >= ? AND data_agendamento <= ?
            """,
            (w0.isoformat(), w1.isoformat()),
        )
        s_atual = int(cur.fetchone()[0])
        cur.execute(
            """
            SELECT COUNT(*) FROM agendamentos
            WHERE status = 'CONFIRMADO'
              AND data_agendamento >= ? AND data_agendamento <= ?
            """,
            (p0.isoformat(), p1_end.isoformat()),
        )
        s_ant = int(cur.fetchone()[0])

        m_start, m_end = _month_bounds(d)
        if d.month == 1:
            pm_last = date(d.year - 1, 12, 31)
        else:
            pm_last = date(d.year, d.month, 1) - timedelta(days=1)
        pm_first = date(pm_last.year, pm_last.month, 1)
        cur.execute(
            """
            SELECT COUNT(*) FROM agendamentos
            WHERE status = 'CONCLUIDO'
              AND data_agendamento >= ? AND data_agendamento <= ?
            """,
            (m_start, m_end),
        )
        c_atual = int(cur.fetchone()[0])
        cur.execute(
            """
            SELECT COUNT(*) FROM agendamentos
            WHERE status = 'CONCLUIDO'
              AND data_agendamento >= ? AND data_agendamento <= ?
            """,
            (pm_first.isoformat(), pm_last.isoformat()),
        )
        c_ant = int(cur.fetchone()[0])
        if c_ant == 0:
            pct: float | None = None
        else:
            pct = 100.0 * (c_atual - c_ant) / c_ant

        return HomeEvolucaoMetrics(
            ref_data_iso=d.isoformat(),
            semana_confirmados_atual=s_atual,
            semana_confirmados_anterior=s_ant,
            variacao_semanal_delta=s_atual - s_ant,
            mes_concluidos_atual=c_atual,
            mes_concluidos_anterior=c_ant,
            desempenho_mensal_pct=pct,
        )
    finally:
        conn.close()


__all__ = [
    "HomeCockpitSnapshot",
    "HomeEvolucaoMetrics",
    "obter_home_cockpit_snapshot",
    "obter_home_evolucao_atendimentos",
    "_week_sunday_to_saturday",
]
