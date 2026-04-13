"""Área de busca de cliente — layout legado ou pesquisa unificada (Nome | NIF | Email | Telefone + Procurar)."""

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


def _render_nome_facilitador(*, key_prefix: str) -> None:
    """Lista clicável (não é selectbox); texto livre mantido no `text_input`."""
    sugs: list[tuple[int, str]] = list(st.session_state.get(f"{key_prefix}_nome_sug_list") or [])
    if not sugs:
        return
    st.markdown(
        f'<p data-testid="bea-busca-nome-sug-panel" style="margin:6px 0 4px 0;font-size:0.72rem;'
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
    pesquisa_unificada: bool = False,
    pesquisa_unificada_cag: bool = False,
) -> bool:
    """
    Com `pesquisa_unificada=True` (ou legado `pesquisa_unificada_cag=True`): rótulos numa linha; inputs +
    «Procurar» noutra (`vertical_alignment="center"`). Linha seguinte: sugestões de nome (col. Nome).

    Usado em Clientes e Agendamentos, Painel de Vendas, e extensível a Colaboradores / Catálogo.

    Caso contrário: layout legado (NIF+doc | email | telefone | botão), com `{prefix}_docintl`.

    Chaves de sessão (modo unificado): `{prefix}_nome`, `{prefix}_nome_sug_list`, `{prefix}_nif`,
    `{prefix}_email`, `{prefix}_tel_txt`, `{prefix}_go`.

    Retorna True se «Procurar» foi clicado neste rerun.
    """
    st.session_state.setdefault(f"{key_prefix}_nome_sug_list", [])

    unified = bool(pesquisa_unificada or pesquisa_unificada_cag)
    if unified:
        return _render_widget_pesquisa_unificada(
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


def _render_widget_pesquisa_unificada(
    *,
    key_prefix: str,
    button_label: str,
    button_type: str,
    minimal: bool,
) -> bool:
    clicked = False
    go_key = f"{key_prefix}_go"
    gap = "small"
    col_weights = [1.08, 1.08, 1.02, 1.02, 0.36]
    lbl = _BUSCA_LBL_CAG if minimal else _BUSCA_LBL_HTML

    # Linha 1 — só rótulos (col. do botão: vão com a mesma altura visual da faixa de rótulo).
    ln, lf, le, lt, lb = st.columns(col_weights, gap=gap, vertical_alignment="top")
    with ln:
        st.markdown(lbl.format("Nome"), unsafe_allow_html=True)
    with lf:
        st.markdown(lbl.format("NIF"), unsafe_allow_html=True)
    with le:
        st.markdown(lbl.format("Email"), unsafe_allow_html=True)
    with lt:
        st.markdown(lbl.format("Telefone"), unsafe_allow_html=True)
    with lb:
        st.markdown(
            '<div style="height:calc(1.35rem + 4px);margin:0;padding:0;" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )

    # Linha 2 — só inputs + botão; «center» alinha verticalmente o botão mais baixo ao meio dos text_input.
    cn, cf, ce, ct, cb = st.columns(col_weights, gap=gap, vertical_alignment="center")
    with cn:
        st.text_input(
            "Nome do cliente",
            key=f"{key_prefix}_nome",
            label_visibility="collapsed",
            placeholder="Nome do cliente",
            on_change=_refresh_nome_suggestions,
            args=(key_prefix,),
        )
        _refresh_nome_suggestions(key_prefix)

    with cf:
        st.text_input(
            "NIF",
            key=f"{key_prefix}_nif",
            label_visibility="collapsed",
            placeholder="NIF",
        )

    with ce:
        st.text_input(
            "Email",
            key=f"{key_prefix}_email",
            label_visibility="collapsed",
            placeholder="email@exemplo.com",
        )

    with ct:
        st.text_input(
            "Telefone",
            key=f"{key_prefix}_tel_txt",
            label_visibility="collapsed",
            placeholder="+351 912 345 678",
        )

    with cb:
        clicked = st.button(
            button_label,
            type=button_type,
            key=go_key,
            width="stretch",
        )

    r2n, _, _, _, _ = st.columns(col_weights, gap=gap, vertical_alignment="top")
    with r2n:
        _render_nome_facilitador(key_prefix=key_prefix)

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
