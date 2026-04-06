"""
Aplicação Streamlit BeaBa Gestão — shell V11.0 (tema + dashboard de 4 blocos).
Referência: docs/CADERNO_MESTRE.md
"""

from __future__ import annotations

import streamlit as st

from src.database.connection import create_tables
from src.modules.cliente import cadastrar_cliente
from src.ui.theme import inject_bea_theme

st.set_page_config(
    page_title="BeaBa Gestão",
    page_icon="⚜️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

create_tables()
inject_bea_theme()

if "page" not in st.session_state:
    st.session_state.page = "home"


def _nav_home() -> None:
    st.session_state.page = "home"


def _render_back_and_breadcrumb(trail: list[str], *, back_key: str) -> None:
    """100% das vistas internas: retorno + breadcrumbs (CADERNO V11.0)."""
    c_back, _ = st.columns([1, 4])
    with c_back:
        if st.button("← Voltar ao Início", key=back_key):
            _nav_home()
    st.markdown(
        '<p class="bea-breadcrumb">' + " › ".join(trail) + "</p>",
        unsafe_allow_html=True,
    )


def _page_home() -> None:
    st.markdown(
        '<h1 class="bea-title" style="text-align:center;margin-bottom:0.25rem;">BeaBa Gestão</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="text-align:center;font-family:Montserrat,sans-serif;color:#545454;opacity:0.85;">'
        "Centro terapêutico — painel operacional</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        """
        <style>
        .bea-dash-wrap { max-width: 920px; margin: 0 auto; }
        </style>
        <div class="bea-dash-wrap">
        """,
        unsafe_allow_html=True,
    )

    row1 = st.columns(2)
    with row1[0]:
        if st.button("Gestão de Clientes", use_container_width=True, type="primary"):
            st.session_state.page = "clientes"
    with row1[1]:
        if st.button("Gestão de Colaboradoras", use_container_width=True, type="secondary"):
            st.session_state.page = "colaboradoras"

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    row2 = st.columns(2)
    with row2[0]:
        if st.button("Catálogo de Serviços", use_container_width=True, type="primary"):
            st.session_state.page = "catalogo"
    with row2[1]:
        if st.button("Painel de Vendas", use_container_width=True, type="secondary"):
            st.session_state.page = "vendas"

    st.markdown("</div>", unsafe_allow_html=True)


def _page_clientes() -> None:
    _render_back_and_breadcrumb(["Home", "Clientes", "Cadastro"], back_key="bea_back_clientes")
    st.markdown("### Cadastro de clientes")
    st.caption("WhatsApp com 11 dígitos (DDD + número). Unicidade obrigatória.")

    nome = st.text_input("Nome completo")
    whatsapp = st.text_input("WhatsApp (DDD + número)")
    if st.button("Cadastrar cliente", type="primary"):
        if not nome or not whatsapp:
            st.warning("Preencha nome e WhatsApp.")
        else:
            ok, msg = cadastrar_cliente(nome, whatsapp)
            if ok:
                st.success(msg)
            else:
                st.error(msg)


def _page_placeholder(title: str, trail: list[str], blurb: str, *, back_key: str) -> None:
    _render_back_and_breadcrumb(trail, back_key=back_key)
    st.markdown(f"### {title}")
    st.info(blurb)


def main() -> None:
    page = st.session_state.page
    if page == "home":
        _page_home()
    elif page == "clientes":
        _page_clientes()
    elif page == "colaboradoras":
        _page_placeholder(
            "Colaboradoras",
            ["Home", "Colaboradoras"],
            "Módulo em construção: cadastro, percentual de repasse e vínculos.",
            back_key="bea_back_colaboradoras",
        )
    elif page == "catalogo":
        _page_placeholder(
            "Catálogo de serviços",
            ["Home", "Catálogo"],
            "Módulo em construção: Sessão, Tempo, Pacote e Produto (4 naturezas).",
            back_key="bea_back_catalogo",
        )
    elif page == "vendas":
        _page_placeholder(
            "Painel de vendas",
            ["Home", "Vendas"],
            "Módulo em construção: exceções financeiras e centavos.",
            back_key="bea_back_vendas",
        )
    else:
        st.session_state.page = "home"
        _page_home()


main()
