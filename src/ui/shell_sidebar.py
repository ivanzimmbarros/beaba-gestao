"""
Menu lateral global — Constituição Visual BeaBá Sereno (Sálvia #76947D, tipografia sans).

Ícones «lineares» no Master referem-se ao tratamento gráfico; na shell Streamlit usamos
rótulos texto limpos (sem emoji) para alinhar ao contraste branco sobre sálvia.
"""

from __future__ import annotations

import streamlit as st

from src.ui.page_auth import clear_session_full

# Ordem e chaves alinhadas a `src.app` (Streamlit). Posição 0 = Início (home).
NAV_ITEMS: list[tuple[str, str]] = [
    ("home", "Início"),
    ("vendas", "Painel de Vendas"),
    ("clientes_agendamentos", "Clientes e Agendamentos"),
    ("catalogo", "Catálogo"),
    ("colaboradores", "Colaboradores"),
    ("financeiro", "Financeiro"),
]


def _nav_items_para_perfil(user_perfil: str | None) -> list[tuple[str, str]]:
    p = (user_perfil or "admin").strip().lower()
    nav: list[tuple[str, str]]
    if p == "colaborador":
        nav = [(k, v) for k, v in NAV_ITEMS if k != "financeiro"]
    else:
        nav = list(NAV_ITEMS)
    if p == "admin":
        nav = nav + [("governanca", "Governança")]
    return nav


def render_shell_sidebar(*, current_page: str, user_perfil: str | None = None) -> None:
    """Renderiza `st.sidebar` com links de navegação (session_state.page)."""
    nav = _nav_items_para_perfil(user_perfil)
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
        for page_key, label in nav:
            is_active = current_page == page_key
            if st.button(
                label,
                key=f"bea_nav_{page_key}",
                width="stretch",
                type="primary" if is_active else "secondary",
            ):
                st.session_state.page = page_key
                st.rerun()

        st.divider()
        st.markdown(
            '<p class="bea-sidebar-sector-title">Outros</p>',
            unsafe_allow_html=True,
        )
        if st.button("Dashboards", key="bea_nav_dash", width="stretch"):
            st.session_state.page = "dashboards"
            st.rerun()
        if st.button("Relatórios", key="bea_nav_rel", width="stretch"):
            st.session_state.page = "relatorios"
            st.rerun()

        st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
        if st.button("Sair", key="bea_nav_logout", width="stretch", type="secondary"):
            clear_session_full()
