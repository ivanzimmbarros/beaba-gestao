"""
Aplicação Streamlit BeaBa Gestão — shell com Constituição Visual BeaBá Sereno (Horizonte + Ilhas).

Referência normativa: Template Master + `.cursorrules` (faixa 300px, creme #FAF8F5, ilhas 20px, sombras compostas).
"""

from __future__ import annotations

import streamlit as st

from src.database.connection import create_tables
from src.ui.constituicao_visual_shell import inject_cag_visual_mount, inject_constituicao_shell
from src.ui.page_catalogo import render_page_catalogo
from src.ui.page_clientes_agendamentos import render_page_clientes_agendamentos
from src.ui.page_colaboradores import render_page_colaboradores
from src.ui.page_dashboards import render_page_dashboards
from src.ui.page_home import render_page_home
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


def _shell_no_breadcrumb(*_a, **_k) -> None:
    """Menu lateral global: páginas internas sem trilho nem botão Voltar."""
    return


def main() -> None:
    page = st.session_state.page
    render_shell_sidebar(current_page=page)
    _, col_main, _ = st.columns([0.06, 0.88, 0.06])
    try:
        with col_main:
            if page == "home":
                render_page_home()
            elif page == "clientes_agendamentos":
                # Marcador DOM para CSS (Ilha Mãe + Horizonte): fica na coluna central, imune a sanitização do markdown interno.
                st.markdown(
                    '<div class="bea-cv-cag-slot" data-testid="bea-cag-slot" aria-hidden="true"></div>',
                    unsafe_allow_html=True,
                )
                render_page_clientes_agendamentos(
                    render_back_and_breadcrumb=_shell_no_breadcrumb,
                )
            elif page in ("colaboradores", "colaboradoras"):
                if page == "colaboradoras":
                    st.session_state.page = "colaboradores"
                st.markdown(
                    '<div class="bea-cv-col-slot" data-testid="bea-col-slot" aria-hidden="true"></div>',
                    unsafe_allow_html=True,
                )
                render_page_colaboradores(
                    render_back_and_breadcrumb=_shell_no_breadcrumb,
                )
            elif page == "catalogo":
                render_page_catalogo(render_back_and_breadcrumb=_shell_no_breadcrumb)
            elif page == "vendas":
                st.markdown(
                    '<div class="bea-cv-vnd-slot" data-testid="bea-vnd-slot" aria-hidden="true"></div>',
                    unsafe_allow_html=True,
                )
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
                st.markdown(
                    '<div class="bea-cv-cag-slot" data-testid="bea-cag-slot" aria-hidden="true"></div>',
                    unsafe_allow_html=True,
                )
                render_page_clientes_agendamentos(
                    render_back_and_breadcrumb=_shell_no_breadcrumb,
                )
            else:
                st.session_state.page = "home"
                render_page_home()
            inject_cag_visual_mount()
    except Exception as err:
        st.error("Ocorreu um erro ao renderizar esta página. Detalhes abaixo.")
        st.exception(err)


main()
