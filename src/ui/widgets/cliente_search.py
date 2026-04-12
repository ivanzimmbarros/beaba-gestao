"""Área de busca de cliente alinhada (NIF / email / telefone em linha única)."""

from __future__ import annotations

from datetime import date

import streamlit as st

# Limite inferior padrão para `st.date_input` em formulários de cliente (alinhado a Clientes / Colaboradores).
CLIENTE_SEARCH_DATE_MIN = date(1900, 1, 1)

_BUSCA_LBL_HTML = (
    '<p style="margin:0 0 4px 0;font-size:0.8rem;color:#666;'
    'min-height:1.35rem;line-height:1.35rem;">{}</p>'
)


def render_cliente_search_widget(
    *,
    key_prefix: str,
    button_label: str = "Procurar",
    button_type: str = "primary",
    minimal: bool = False,
) -> bool:
    """
    Renderiza NIF/documento (com checkbox internacional), email e telefone numa única linha,
    com rótulos HTML, e o botão «Procurar».

    Com `minimal=True` (ex.: Painel de Vendas), omite rótulos HTML pesados e usa só placeholders.

    Chaves de sessão (todas com prefixo `key_prefix`):
    `{prefix}_docintl`, `{prefix}_nif`, `{prefix}_email`, `{prefix}_tel_txt`, `{prefix}_go`.

    Retorna True se o botão «Procurar» foi clicado neste rerun.

    Nota: calendários em formulários de ficha devem usar `CLIENTE_SEARCH_DATE_MIN` em `min_value`.
    """
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
        with st.container():
            clicked = st.button(
                button_label,
                type=button_type,
                key=go_key,
                width="stretch",
            )

    return bool(clicked)
