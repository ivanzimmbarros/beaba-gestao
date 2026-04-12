"""Página inicial (Hub) — Constituição Visual BeaBá Sereno; rota padrão em `st.session_state.page` = ``home``."""

from __future__ import annotations

import streamlit as st

from src.ui.constituicao_visual_shell import inject_constituicao_home_hub
from src.ui.fmt_euro_constituicao import fmt_euro_centavos


def render_page_home() -> None:
    """Hub — Horizonte (via shell global), hero, ilha métricas, ilhas de acção."""
    inject_constituicao_home_hub()

    st.markdown(
        """
        <div class="bea-cv-hero">
          <h1>BeaBa Gestão</h1>
          <p class="bea-cv-sub">Centro terapêutico — painel operacional</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="bea-cv-island-metricas">
          <p class="bea-cv-island-titulo">Indicadores do dia (exemplo)</p>
          <div class="bea-cv-metric-grid">
            <div class="bea-cv-metric">
              <span class="lbl">Vendas registadas</span>
              <span class="eur">{fmt_euro_centavos(0)}</span>
            </div>
            <div class="bea-cv-metric">
              <span class="lbl">Pendente de liquidação</span>
              <span class="eur">{fmt_euro_centavos(0)}</span>
            </div>
            <div class="bea-cv-metric">
              <span class="lbl">Crédito em carteira</span>
              <span class="eur">{fmt_euro_centavos(125000)}</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    row1 = st.columns(2)
    with row1[0]:
        if st.button("Painel de Vendas", width="stretch", type="primary"):
            st.session_state.page = "vendas"
    with row1[1]:
        if st.button("Clientes e Agendamentos", width="stretch", type="secondary"):
            st.session_state.page = "clientes_agendamentos"

    row2 = st.columns(2)
    with row2[0]:
        if st.button("Gestão de Colaboradores", width="stretch", type="primary"):
            st.session_state.page = "colaboradores"
    with row2[1]:
        if st.button("Catálogo de Serviços", width="stretch", type="secondary"):
            st.session_state.page = "catalogo"

    row3 = st.columns(2)
    with row3[0]:
        if st.button("Dashboards", width="stretch", type="primary"):
            st.session_state.page = "dashboards"
    with row3[1]:
        if st.button("Relatórios", width="stretch", type="secondary"):
            st.session_state.page = "relatorios"
