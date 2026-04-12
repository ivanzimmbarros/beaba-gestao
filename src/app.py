"""
Aplicação Streamlit BeaBa Gestão — shell com Constituição Visual BeaBá Sereno (Horizonte + Ilhas).

Referência normativa: Template Master + `.cursorrules` (faixa 300px, creme #FAF8F5, ilhas 20px, sombras compostas).
"""

from __future__ import annotations

import streamlit as st

from src.database.connection import create_tables
from src.ui.constituicao_visual_shell import inject_constituicao_home_hub, inject_constituicao_shell
from src.ui.page_catalogo import render_page_catalogo
from src.ui.page_clientes_agendamentos import render_page_clientes_agendamentos
from src.ui.page_colaboradores import render_page_colaboradores
from src.ui.page_dashboards import render_page_dashboards
from src.ui.page_vendas import render_page_vendas
from src.ui.shell_sidebar import render_shell_sidebar
from src.pages.theme import inject_beaba_verde_sereno
from src.ui.theme import inject_bea_theme

st.set_page_config(
    page_title="BeaBa Gestão",
    page_icon="⚜️",
    layout="wide",
    initial_sidebar_state="expanded",
)

create_tables()
inject_bea_theme()
inject_beaba_verde_sereno()
inject_constituicao_shell()

if "page" not in st.session_state:
    st.session_state.page = "home"


def _fmt_euro_centavos(centavos: int) -> str:
    """Formato canónico Master: € 1.250,00 (milhar por ponto, decimal vírgula)."""
    neg = "−" if centavos < 0 else ""
    x = abs(int(centavos))
    euros, cent = divmod(x, 100)
    s = str(euros)
    parts: list[str] = []
    while s:
        parts.append(s[-3:])
        s = s[:-3]
    body = ".".join(reversed(parts))
    return f"{neg}€ {body},{cent:02d}"


def _shell_no_breadcrumb(*_a, **_k) -> None:
    """Menu lateral global: páginas internas sem trilho nem botão Voltar."""
    return


def _page_home() -> None:
    """Hub — prova de conceito Constituição: Horizonte (via shell), hero, ilha métricas, ilhas de acção."""
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

    # Ilha: indicadores financeiros (valores ilustrativos; padrão € obrigatório)
    st.markdown(
        f"""
        <div class="bea-cv-island-metricas">
          <p class="bea-cv-island-titulo">Indicadores do dia (exemplo)</p>
          <div class="bea-cv-metric-grid">
            <div class="bea-cv-metric">
              <span class="lbl">Vendas registadas</span>
              <span class="eur">{_fmt_euro_centavos(0)}</span>
            </div>
            <div class="bea-cv-metric">
              <span class="lbl">Pendente de liquidação</span>
              <span class="eur">{_fmt_euro_centavos(0)}</span>
            </div>
            <div class="bea-cv-metric">
              <span class="lbl">Crédito em carteira</span>
              <span class="eur">{_fmt_euro_centavos(125000)}</span>
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


def main() -> None:
    page = st.session_state.page
    render_shell_sidebar(current_page=page)
    _, col_main, _ = st.columns([0.06, 0.88, 0.06])
    try:
        with col_main:
            if page == "home":
                _page_home()
            elif page == "clientes_agendamentos":
                render_page_clientes_agendamentos(
                    render_back_and_breadcrumb=_shell_no_breadcrumb,
                )
            elif page in ("colaboradores", "colaboradoras"):
                if page == "colaboradoras":
                    st.session_state.page = "colaboradores"
                render_page_colaboradores(
                    render_back_and_breadcrumb=_shell_no_breadcrumb,
                )
            elif page == "catalogo":
                render_page_catalogo(render_back_and_breadcrumb=_shell_no_breadcrumb)
            elif page == "vendas":
                render_page_vendas(render_back_and_breadcrumb=_shell_no_breadcrumb)
            elif page == "dashboards":
                render_page_dashboards(
                    render_back_and_breadcrumb=_shell_no_breadcrumb,
                    modo="dashboards",
                )
            elif page == "relatorios":
                render_page_dashboards(
                    render_back_and_breadcrumb=_shell_no_breadcrumb,
                    modo="relatorios",
                )
            elif page in ("clientes", "agendamentos"):
                st.session_state.page = "clientes_agendamentos"
                render_page_clientes_agendamentos(
                    render_back_and_breadcrumb=_shell_no_breadcrumb,
                )
            else:
                st.session_state.page = "home"
                _page_home()
    except Exception as err:
        st.error("Ocorreu um erro ao renderizar esta página. Detalhes abaixo.")
        st.exception(err)


main()
