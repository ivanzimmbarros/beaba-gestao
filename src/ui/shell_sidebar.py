"""
Menu lateral global — Constituição Visual BeaBá Sereno (Sálvia #76947D, tipografia sans).

Ícones «lineares» no Master referem-se ao tratamento gráfico; na shell Streamlit usamos
rótulos texto limpos (sem emoji) para alinhar ao contraste branco sobre sálvia.
"""

from __future__ import annotations

import streamlit as st

from src.ui.page_auth import clear_session_full
from src.database.connection import get_beaba_env_type_raw

# Ordem e chaves alinhadas a `src.app` (Streamlit). Posição 0 = Início (home).
NAV_ITEMS: list[tuple[str, str]] = [
    ("home", "Início"),
    ("vendas", "Painel de Vendas"),
    ("clientes_agendamentos", "Clientes e Agendamentos"),
    ("catalogo", "Catálogo"),
    ("colaboradores", "Colaboradores"),
    ("financeiro", "Financeiro"),
]

_NAV_USUARIOS_ADMIN: tuple[str, str] = ("usuarios", "Gestão de utilizadores")


_PAGES_PERFIL_USUARIO: tuple[str, ...] = ("home", "vendas", "clientes_agendamentos")

_PRODUCTION_ENVS = frozenset({"production", "prod", "main"})
_STAGING_ENVS = frozenset({"staging", "stg"})
_DEV_ENVS = frozenset({"dev", "develop", "development", "local"})


def _sidebar_env_badge_spec(env_raw: str) -> tuple[str, str, str] | None:
    """Selo de ambiente (bg, fg, texto) ou ``None`` quando produção/main (sidebar limpa)."""
    key = (env_raw or "local").strip().lower()
    if key in _PRODUCTION_ENVS:
        return None
    if key in _STAGING_ENVS:
        # Alerta âmbar — contraste legível sobre a faixa sálvia da sidebar (Sereno).
        return ("#FEF3C7", "#B45309", "AMBIENTE DE TESTE")
    if key in _DEV_ENVS:
        return ("#2563EB", "#FFFFFF", "DESENVOLVIMENTO")
    # Ambiente desconhecido: selo de desenvolvimento (nunca silenciar como produção).
    return ("#2563EB", "#FFFFFF", "DESENVOLVIMENTO")


def _render_sidebar_env_badge(badge_bg: str, badge_fg: str, badge_txt: str) -> None:
    st.markdown(
        f"""
        <div style="
          display:flex;
          justify-content:center;
          align-items:center;
          padding:10px 10px 6px 10px;">
          <div style="
            background:{badge_bg};
            color:{badge_fg};
            font-weight:800;
            letter-spacing:0.6px;
            border-radius:999px;
            padding:6px 12px;
            font-size:12px;
            text-transform:uppercase;
            width:100%;
            text-align:center;
            font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
            box-shadow: 0 1px 2px rgba(45, 51, 47, 0.12);">
            {badge_txt}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _perfil_sidebar_normalizado(user_perfil: str | None) -> str:
    raw = (user_perfil or "admin").strip().lower()
    if raw == "colaborador":
        return "usuario"
    return raw


def _nav_items_para_perfil(user_perfil: str | None) -> list[tuple[str, str]]:
    p = _perfil_sidebar_normalizado(user_perfil)
    if p == "usuario":
        return [(k, v) for k, v in NAV_ITEMS if k in _PAGES_PERFIL_USUARIO]
    if p == "admin":
        return list(NAV_ITEMS) + [_NAV_USUARIOS_ADMIN, ("governanca", "Governança")]
    return list(NAV_ITEMS)


def render_shell_sidebar(*, current_page: str, user_perfil: str | None = None) -> None:
    """Renderiza `st.sidebar` com links de navegação (session_state.page)."""
    nav = _nav_items_para_perfil(user_perfil)
    ep = _perfil_sidebar_normalizado(user_perfil)
    with st.sidebar:
        badge = _sidebar_env_badge_spec(get_beaba_env_type_raw())
        if badge is not None:
            badge_bg, badge_fg, badge_txt = badge
            _render_sidebar_env_badge(badge_bg, badge_fg, badge_txt)
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
        if ep != "usuario":
            if st.button("Dashboards", key="bea_nav_dash", width="stretch"):
                st.session_state.page = "dashboards"
                st.rerun()
            if st.button("Relatórios", key="bea_nav_rel", width="stretch"):
                st.session_state.page = "relatorios"
                st.rerun()

        st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
        if st.button("Sair", key="bea_nav_logout", width="stretch", type="secondary"):
            clear_session_full()
