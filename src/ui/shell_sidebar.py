"""
Menu lateral global — Constituição Visual BeaBá Sereno (Sálvia #76947D, tipografia sans).

Ícones «lineares» no Master referem-se ao tratamento gráfico; na shell Streamlit usamos
rótulos texto limpos (sem emoji) para alinhar ao contraste branco sobre sálvia.
"""

from __future__ import annotations

import streamlit as st

# Ordem e chaves alinhadas a `src.app.main`
NAV_ITEMS: list[tuple[str, str]] = [
    ("clientes_agendamentos", "Clientes e Agendamentos"),
    ("vendas", "Painel de Vendas"),
    ("colaboradores", "Colaboradores"),
    ("catalogo", "Catálogo"),
]


def render_shell_sidebar(*, current_page: str) -> None:
    """Renderiza `st.sidebar` com links de navegação (session_state.page)."""
    with st.sidebar:
        st.markdown(
            '<p class="bea-sidebar-app-title">Sistema de Gestão do BeaBa Materno</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p class="bea-sidebar-sector-title">Navegação</p>',
            unsafe_allow_html=True,
        )
        st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
        for page_key, label in NAV_ITEMS:
            is_active = current_page == page_key
            if st.button(
                label,
                key=f"bea_nav_{page_key}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.page = page_key
                st.rerun()

        st.divider()
        st.markdown(
            '<p class="bea-sidebar-sector-title">Outros</p>',
            unsafe_allow_html=True,
        )
        if st.button("Início / Hub", key="bea_nav_home", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()
        if st.button("Dashboards", key="bea_nav_dash", use_container_width=True):
            st.session_state.page = "dashboards"
            st.rerun()
        if st.button("Relatórios", key="bea_nav_rel", use_container_width=True):
            st.session_state.page = "relatorios"
            st.rerun()
