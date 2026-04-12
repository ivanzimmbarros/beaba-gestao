"""Página inicial — Cockpit (Fase 3): dados reais, ilhas sobre o horizonte 300px, drill-down para CAG."""

from __future__ import annotations

import html
import os
from datetime import date, datetime

import plotly.graph_objects as go
import streamlit as st

from src.modules.agendamento import listar_agendamentos
from src.modules.home_cockpit_metrics import (
    HomeCockpitSnapshot,
    obter_home_cockpit_snapshot,
    obter_home_evolucao_atendimentos,
)
from src.ui.constituicao_visual_shell import (
    inject_constituicao_home_cockpit_extra,
    inject_constituicao_home_hub,
)
from src.ui.home_cockpit_ui_helpers import (
    agenda_day_table_html,
    evolucao_atendimentos_html,
)

CV_SALVIA = "rgba(118, 148, 125, 0.88)"
CV_SALVIA_TRACK = "rgba(118, 148, 125, 0.14)"
CV_TERRA = "rgba(212, 163, 115, 0.92)"
CV_TERRA_TRACK = "rgba(212, 163, 115, 0.18)"
CV_TITLE = "#2D332F"


def _plotly_empty_donut(center: str) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Pie(
                values=[1],
                hole=0.72,
                marker_colors=["rgba(200, 200, 200, 0.35)"],
                textinfo="none",
                showlegend=False,
                hoverinfo="skip",
            )
        ]
    )
    fig.update_layout(
        margin=dict(t=8, b=8, l=8, r=8),
        height=220,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    fig.add_annotation(
        text=center,
        x=0.5,
        y=0.45,
        showarrow=False,
        font=dict(size=22, color=CV_TITLE),
    )
    return fig


def _figure_donut_hoje_semana(hoje: int, semana: int) -> go.Figure:
    if semana <= 0:
        return _plotly_empty_donut("—")
    resto = max(0, semana - hoje)
    fig = go.Figure(
        data=[
            go.Pie(
                values=[hoje, resto],
                hole=0.72,
                marker_colors=[CV_SALVIA, CV_SALVIA_TRACK],
                textinfo="none",
                showlegend=False,
                hovertemplate="%{label}: %{value}<extra></extra>",
                labels=["Confirmados hoje", "Outros na semana"],
            )
        ]
    )
    pct = int(round(100 * hoje / semana)) if semana else 0
    fig.update_layout(
        margin=dict(t=8, b=8, l=8, r=8),
        height=220,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    fig.add_annotation(
        text=f"{pct}%",
        x=0.5,
        y=0.45,
        showarrow=False,
        font=dict(size=20, color=CV_TITLE),
    )
    return fig


def _figure_donut_contagem_unica(n: int) -> go.Figure:
    if n <= 0:
        return _plotly_empty_donut("—")
    fig = go.Figure(
        data=[
            go.Pie(
                values=[1],
                hole=0.72,
                marker_colors=[CV_SALVIA],
                textinfo="none",
                showlegend=False,
                hoverinfo="skip",
            )
        ]
    )
    fig.update_layout(
        margin=dict(t=8, b=8, l=8, r=8),
        height=220,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    fig.add_annotation(
        text=str(int(n)),
        x=0.5,
        y=0.45,
        showarrow=False,
        font=dict(size=22, color=CV_TITLE),
    )
    return fig


def _figure_donut_taxa_cancelamento(pct: float | None) -> go.Figure:
    if pct is None:
        return _plotly_empty_donut("—")
    p = max(0.0, min(100.0, float(pct)))
    rest = max(0.001, 100.0 - p)
    fig = go.Figure(
        data=[
            go.Pie(
                values=[p, rest],
                hole=0.72,
                marker_colors=[CV_TERRA, CV_TERRA_TRACK],
                textinfo="none",
                showlegend=False,
                hovertemplate="%{label}<extra></extra>",
                labels=["Taxa cancel.", "Base"],
            )
        ]
    )
    fig.update_layout(
        margin=dict(t=8, b=8, l=8, r=8),
        height=220,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    fig.add_annotation(
        text=f"{p:.1f}%",
        x=0.5,
        y=0.45,
        showarrow=False,
        font=dict(size=18, color=CV_TITLE),
    )
    return fig


def _ref_ym(snap: HomeCockpitSnapshot) -> tuple[int, int]:
    d = date.fromisoformat(str(snap.referencia_data_iso)[:10])
    return d.year, d.month


def _navigate_cag_drill(*, banner: str, seed_month: tuple[int, int] | None) -> None:
    st.session_state.cag_home_drill_banner = banner
    if seed_month:
        st.session_state.cag_home_calendar_seed_month = {
            "y": int(seed_month[0]),
            "m": int(seed_month[1]),
        }
    st.session_state.page = "clientes_agendamentos"
    st.rerun()


def render_page_home() -> None:
    inject_constituicao_home_hub()
    inject_constituicao_home_cockpit_extra()

    st.markdown(
        '<div class="bea-cv-cockpit-active" data-testid="bea-home-cockpit-root"></div>',
        unsafe_allow_html=True,
    )

    nome = html.escape(str(os.environ.get("BEABA_HOME_DISPLAY_NAME", "Lara")).strip() or "Lara")
    agora = datetime.now()
    relogio = agora.strftime("%H:%M")

    with st.spinner("A carregar cockpit…"):
        snap = obter_home_cockpit_snapshot()
        evo = obter_home_evolucao_atendimentos()
        ref_iso = (snap.referencia_data_iso if snap else date.today().isoformat())[:10]
        raw_agenda = listar_agendamentos(data_de=ref_iso, data_ate=ref_iso)
        agenda_rows = [r for r in raw_agenda if str(r.get("status") or "") != "CANCELADO"]
        agenda_rows.sort(
            key=lambda r: (
                str(r.get("hora_inicio") or ""),
                int(r.get("id") or 0),
            )
        )

    st.markdown(
        f"""
        <div class="bea-cv-cockpit-hero">
          <h1>Olá, {nome}</h1>
          <p class="bea-cv-cockpit-greet-sub">Bem-vindo ao cockpit operacional BeaBa Gestão.</p>
          <span class="bea-cv-cockpit-hero-ts" data-testid="bea-home-hero-clock">{relogio}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if snap is None:
        st.warning("Não foi possível carregar métricas (base indisponível).")
    else:
        ym = _ref_ym(snap)
        m_lbl = f"{ym[1]:02d}/{ym[0]}"

        with st.container(border=True):
            st.markdown(
                '<p class="bea-cv-cockpit-tier-title">Nível 1 — Fluxo operacional (donuts)</p>',
                unsafe_allow_html=True,
            )
            d1, d2, d3 = st.columns(3)
            cfg = dict(displayModeBar=False, staticPlot=False)
            with d1:
                st.plotly_chart(
                    _figure_donut_hoje_semana(
                        snap.donut1_confirmados_hoje,
                        snap.donut1_previstos_semana,
                    ),
                    use_container_width=True,
                    config=cfg,
                    key="home_donut_hoje",
                )
                st.markdown(
                    '<p class="bea-cv-donut-caption">Confirmados hoje vs total previsto na semana</p>',
                    unsafe_allow_html=True,
                )
            with d2:
                st.plotly_chart(
                    _figure_donut_contagem_unica(snap.donut2_agendados_e_confirmados_semana),
                    use_container_width=True,
                    config=cfg,
                    key="home_donut_semana",
                )
                st.markdown(
                    '<p class="bea-cv-donut-caption">Agendados + confirmados (semana)</p>',
                    unsafe_allow_html=True,
                )
            with d3:
                st.plotly_chart(
                    _figure_donut_taxa_cancelamento(snap.donut3_taxa_cancelamento_pct),
                    use_container_width=True,
                    config=cfg,
                    key="home_donut_retencao",
                )
                st.markdown(
                    '<p class="bea-cv-donut-caption">Taxa de cancelamento no mês</p>',
                    unsafe_allow_html=True,
                )

        with st.container(border=True):
            st.markdown(
                '<p class="bea-cv-cockpit-tier-title">Nível 2 — Panorama global</p>',
                unsafe_allow_html=True,
            )
            p1, p2 = st.columns(2)
            with p1:
                st.markdown(
                    f'<div class="bea-cv-panorama-card-title">Estimativa não confirmados</div>'
                    f'<div class="bea-cv-panorama-card-val" data-testid="bea-home-card-estimativa">'
                    f"{snap.card1_valor_fmt()}</div>",
                    unsafe_allow_html=True,
                )
                if st.button(
                    f"Explorar — estimativa ({m_lbl})",
                    key="home_drill_estimativa",
                    use_container_width=True,
                ):
                    _navigate_cag_drill(
                        banner=(
                            "**Panorama (cockpit):** estimativa de faturação em compromissos ainda **não confirmados** "
                            f"no mês **{m_lbl}**. Pesquise um cliente e reveja a lista de agendamentos desse mês "
                            "(estados ≠ Confirmado, excluindo cancelados)."
                        ),
                        seed_month=ym,
                    )
            with p2:
                st.markdown(
                    f'<div class="bea-cv-panorama-card-title">Total não confirmados</div>'
                    f'<div class="bea-cv-panorama-card-val" data-testid="bea-home-card-nao-conf">'
                    f"{int(snap.card2_total_nao_confirmados_mes)}</div>",
                    unsafe_allow_html=True,
                )
                if st.button(
                    f"Explorar — não confirmados ({m_lbl})",
                    key="home_drill_nao_conf",
                    use_container_width=True,
                ):
                    _navigate_cag_drill(
                        banner=(
                            "**Panorama (cockpit):** existem **"
                            f"{int(snap.card2_total_nao_confirmados_mes)}** agendamentos no mês **{m_lbl}** "
                            "fora do estado Confirmado (cancelados excluídos do indicador). "
                            "Na Área Única, carregue um cliente e ordene a lista por **Estado**."
                        ),
                        seed_month=ym,
                    )
            p3, p4 = st.columns(2)
            with p3:
                st.markdown(
                    f'<div class="bea-cv-panorama-card-title">Pré-agendados</div>'
                    f'<div class="bea-cv-panorama-card-val" data-testid="bea-home-card-pre-ag">'
                    f"{int(snap.card3_pre_agendados_mes)}</div>",
                    unsafe_allow_html=True,
                )
                if st.button(
                    f"Explorar — pré-agendados ({m_lbl})",
                    key="home_drill_pre_ag",
                    use_container_width=True,
                ):
                    _navigate_cag_drill(
                        banner=(
                            "**Panorama (cockpit):** **"
                            f"{int(snap.card3_pre_agendados_mes)}** marcações em **Pré-agendado** no mês **{m_lbl}**. "
                            "Na Área Única, confirme ou ajuste após carregar o cliente."
                        ),
                        seed_month=ym,
                    )
            with p4:
                st.markdown(
                    f'<div class="bea-cv-panorama-card-title">Saldo crédito (pós-cancel. SIM)</div>'
                    f'<div class="bea-cv-panorama-card-val" data-testid="bea-home-card-credito">'
                    f"{snap.card4_valor_fmt()}</div>",
                    unsafe_allow_html=True,
                )
                if st.button(
                    "Explorar — créditos em carteira",
                    key="home_drill_credito",
                    use_container_width=True,
                ):
                    _navigate_cag_drill(
                        banner=(
                            "**Panorama (cockpit):** saldo agregado de **crédito** em clientes com histórico de "
                            "**crédito por cancelamento (fluxo SIM)**. Pesquise o cliente e consulte o saldo na ficha."
                        ),
                        seed_month=ym,
                    )

        evo_html = ""
        if evo is not None:
            evo_html = evolucao_atendimentos_html(
                variacao_delta=int(evo.variacao_semanal_delta),
                desempenho_pct_label=evo.desempenho_pct_label(),
                mes_atual=int(evo.mes_concluidos_atual),
                mes_ant=int(evo.mes_concluidos_anterior),
            )
        else:
            evo_html = (
                '<div class="bea-cv-agenda-empty" data-testid="bea-home-evolucao-fallback">'
                "Métricas de evolução indisponíveis."
                "</div>"
            )

        ref_d = date.fromisoformat(ref_iso)
        agenda_html = agenda_day_table_html(
            agenda_rows,
            ref_date=ref_d,
            now=agora,
            prox_minutos=15,
        )

        with st.container(border=True):
            st.markdown(
                '<p class="bea-cv-cockpit-tier-title">Nível 3 — Agenda do dia e evolução</p>',
                unsafe_allow_html=True,
            )
            c_ag, c_ev = st.columns([0.68, 0.32])
            with c_ag:
                st.markdown("##### Agenda do dia")
                st.markdown(agenda_html, unsafe_allow_html=True)
            with c_ev:
                st.markdown("##### Evolução de atendimentos")
                st.markdown(evo_html, unsafe_allow_html=True)
