"""Área de busca de cliente — layout compacto (3 campos) ou pesquisa unificada CAG (Nome | NIF | Email | Telefone)."""

from __future__ import annotations

from datetime import date

import streamlit as st

from src.modules.cliente import buscar_clientes_por_prefixo_nome

# Limite inferior padrão para `st.date_input` em formulários de cliente (alinhado a Clientes / Colaboradores).
CLIENTE_SEARCH_DATE_MIN = date(1900, 1, 1)

# Rótulos legados (páginas sem pesquisa unificada CAG)
_BUSCA_LBL_HTML = (
    '<p style="margin:0 0 4px 0;font-size:0.8rem;color:#666;'
    'min-height:1.35rem;line-height:1.35rem;">{}</p>'
)

# Token solicitado para CAG (#718355) + hierarquia sans; sombras Master nos painéis de sugestão
_BUSCA_LBL_CAG = (
    '<p style="margin:0 0 4px 0;font-size:0.8rem;color:#718355;font-weight:600;'
    'min-height:1.35rem;line-height:1.35rem;">{}</p>'
)

def _refresh_nome_suggestions(prefix: str, min_chars: int = 1) -> None:
    t = str(st.session_state.get(f"{prefix}_nome", "") or "").strip()
    if len(t) < min_chars:
        st.session_state[f"{prefix}_nome_sug_list"] = []
        return
    st.session_state[f"{prefix}_nome_sug_list"] = buscar_clientes_por_prefixo_nome(t, limit=12)


def _render_cag_nome_facilitador(*, key_prefix: str) -> None:
    """Lista clicável (não é selectbox); texto livre mantido no `text_input`."""
    sugs: list[tuple[int, str]] = list(st.session_state.get(f"{key_prefix}_nome_sug_list") or [])
    if not sugs:
        return
    st.markdown(
        f'<p data-testid="bea-cag-nome-sug-panel" style="margin:6px 0 4px 0;font-size:0.72rem;'
        f"color:#718355;font-weight:600;\">Sugestões</p>",
        unsafe_allow_html=True,
    )
    for cid, nome in sugs[:10]:
        label = nome if len(nome) <= 48 else nome[:45] + "…"
        if st.button(
            label,
            key=f"{key_prefix}_npick_{cid}",
            type="secondary",
            width="stretch",
        ):
            st.session_state[f"{key_prefix}_nome"] = nome
            st.session_state[f"{key_prefix}_nome_sug_list"] = []
            st.rerun()


def render_cliente_search_widget(
    *,
    key_prefix: str,
    button_label: str = "Procurar",
    button_type: str = "primary",
    minimal: bool = False,
    pesquisa_unificada_cag: bool = False,
) -> bool:
    """
    Com `pesquisa_unificada_cag=True` (Clientes e Agendamentos): linha Nome | NIF | Email | Telefone,
    checkbox «Doc. internacional» abaixo do NIF, facilitador de nome (lista clicável, sem selectbox),
    botão «Procurar» alinhado ao eixo médio da linha de inputs.

    Caso contrário: layout compacto legado (NIF+doc | email | telefone | botão).

    Chaves de sessão (prefixo `key_prefix`):
    `{prefix}_nome`, `{prefix}_nome_sug_list` (só CAG), `{prefix}_docintl`, `{prefix}_nif`,
    `{prefix}_email`, `{prefix}_tel_txt`, `{prefix}_go`.

    Retorna True se «Procurar» foi clicado neste rerun.
    """
    st.session_state.setdefault(f"{key_prefix}_nome_sug_list", [])

    if pesquisa_unificada_cag:
        return _render_widget_pesquisa_unificada_cag(
            key_prefix=key_prefix,
            button_label=button_label,
            button_type=button_type,
            minimal=minimal,
        )

    return _render_widget_legacy(
        key_prefix=key_prefix,
        button_label=button_label,
        button_type=button_type,
        minimal=minimal,
    )


def _render_widget_pesquisa_unificada_cag(
    *,
    key_prefix: str,
    button_label: str,
    button_type: str,
    minimal: bool,
) -> bool:
    clicked = False
    go_key = f"{key_prefix}_go"
    gap = "small"
    cn, cf, ce, ct, cb = st.columns([1.08, 1.08, 1.02, 1.02, 0.36], gap=gap)

    lbl = _BUSCA_LBL_CAG if minimal else _BUSCA_LBL_HTML

    with cn:
        st.markdown(lbl.format("Nome"), unsafe_allow_html=True)
        st.text_input(
            "Nome do cliente",
            key=f"{key_prefix}_nome",
            label_visibility="collapsed",
            placeholder="Nome do cliente",
            on_change=_refresh_nome_suggestions,
            args=(key_prefix,),
        )
        _refresh_nome_suggestions(key_prefix)
        _render_cag_nome_facilitador(key_prefix=key_prefix)

    with cf:
        st.markdown(lbl.format("NIF"), unsafe_allow_html=True)
        ph_nif = (
            "Documento internacional"
            if st.session_state.get(f"{key_prefix}_docintl")
            else "NIF ou documento"
        )
        st.text_input(
            "NIF",
            key=f"{key_prefix}_nif",
            label_visibility="collapsed",
            placeholder=ph_nif,
        )
        st.checkbox(
            "Doc. internacional",
            key=f"{key_prefix}_docintl",
            label_visibility="visible",
        )

    with ce:
        st.markdown(lbl.format("Email"), unsafe_allow_html=True)
        st.text_input(
            "Email",
            key=f"{key_prefix}_email",
            label_visibility="collapsed",
            placeholder="email@exemplo.com",
        )

    with ct:
        st.markdown(lbl.format("Telefone"), unsafe_allow_html=True)
        st.text_input(
            "Telefone",
            key=f"{key_prefix}_tel_txt",
            label_visibility="collapsed",
            placeholder="+351 912 345 678",
        )

    with cb:
        # Centra verticalmente o botão relativamente à linha de inputs (~label + campo)
        st.markdown(
            '<div style="height:calc(1.35rem + 4px + 22px);" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )
        clicked = st.button(
            button_label,
            type=button_type,
            key=go_key,
            width="stretch",
        )

    return bool(clicked)


def _render_widget_legacy(
    *,
    key_prefix: str,
    button_label: str,
    button_type: str,
    minimal: bool,
) -> bool:
    c_b1, c_b2, c_b3, c_b4 = st.columns([1.45, 1.15, 1.2, 0.5], gap="small")
    clicked = False
    go_key = f"{key_prefix}_go"
    spacer = (
        '<div style="height: calc(1.35rem + 4px); margin: 0; padding: 0;" '
        'aria-hidden="true"></div>'
    )
    if minimal:
        spacer = '<div style="height: 0.35rem; margin: 0; padding: 0;" aria-hidden="true"></div>'

    with c_b1:
        if not minimal:
            st.markdown(_BUSCA_LBL_HTML.format("NIF / documento"), unsafe_allow_html=True)
        else:
            st.markdown(spacer, unsafe_allow_html=True)
        i_nif_l, i_nif_r = st.columns([0.44, 0.56], gap="small")
        with i_nif_l:
            st.checkbox(
                "Doc. internacional" if minimal else "Internacional",
                key=f"{key_prefix}_docintl",
                label_visibility="visible",
            )
        ph_nif = (
            "Documento internacional"
            if st.session_state.get(f"{key_prefix}_docintl")
            else "NIF ou documento"
        )
        with i_nif_r:
            st.text_input(
                "NIF",
                key=f"{key_prefix}_nif",
                label_visibility="collapsed",
                placeholder=ph_nif,
            )
    with c_b2:
        if not minimal:
            st.markdown(_BUSCA_LBL_HTML.format("Email"), unsafe_allow_html=True)
        else:
            st.markdown(spacer, unsafe_allow_html=True)
        st.text_input(
            "Email",
            key=f"{key_prefix}_email",
            label_visibility="collapsed",
            placeholder="email@exemplo.com",
        )
    with c_b3:
        if not minimal:
            st.markdown(_BUSCA_LBL_HTML.format("Telefone"), unsafe_allow_html=True)
        else:
            st.markdown(spacer, unsafe_allow_html=True)
        st.text_input(
            "Telefone",
            key=f"{key_prefix}_tel_txt",
            label_visibility="collapsed",
            placeholder="+351 912 345 678",
        )
    with c_b4:
        st.markdown(
            '<div style="height: calc(1.35rem + 4px); margin: 0; padding: 0;" '
            'aria-hidden="true"></div>'
            if not minimal
            else '<div style="height: 0.35rem; margin: 0; padding: 0;" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )
        clicked = st.button(
            button_label,
            type=button_type,
            key=go_key,
            width="stretch",
        )

    return bool(clicked)
