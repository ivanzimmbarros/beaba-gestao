"""Widgets Streamlit: telemóvel/fixos, país com pesquisa, número nacional → E.164."""

from __future__ import annotations

import phonenumbers
import streamlit as st
from phonenumbers import NumberParseException

from src.modules.country_dial_codes import (
    encontrar_por_texto_busca,
    listar_paises_indicativo,
    rotulo_pais_telefone,
)
from src.modules.telefone import normalizar_telefone_e164


def render_grupo_telefone(
    st_module,
    *,
    prefix: str,
    label: str = "Contacto telefónico",
    disabled: bool = False,
) -> None:
    st_module.markdown(f"**{label}**")
    st_module.radio(
        "Tipo de linha *",
        ["Telemóvel", "Fixo"],
        horizontal=True,
        key=f"{prefix}_tt",
        disabled=disabled,
    )
    st_module.caption("Indicativo do país e número nacional (validação por país).")
    busca = st_module.text_input(
        "Filtrar país (nome, ISO2 ou indicativo)",
        key=f"{prefix}_tp_filtro",
        placeholder="Ex.: Portugal, BR, 351…",
        disabled=disabled,
    )
    opts = encontrar_por_texto_busca(busca)
    labels = [rotulo_pais_telefone(iso, dial, nome) for iso, dial, nome in opts]
    st_module.selectbox(
        "País / indicativo *",
        list(range(len(opts))),
        format_func=lambda i: labels[i],
        key=f"{prefix}_tp_idx",
        disabled=disabled,
    )
    st_module.text_input(
        "Número nacional (sem +indicativo) *",
        key=f"{prefix}_tp_nac",
        placeholder="Apenas dígitos do número local",
        disabled=disabled,
    )


def preencher_session_telefone_de_e164(prefix: str, e164: str) -> None:
    """Inicializa chaves de `render_grupo_telefone` a partir de um número E.164 (edição de ficha)."""
    v = (e164 or "").strip()
    if not v:
        return
    try:
        parsed = phonenumbers.parse(v, None)
    except NumberParseException:
        return
    if not phonenumbers.is_valid_number(parsed):
        return
    iso = phonenumbers.region_code_for_number(parsed)
    if not iso:
        return
    national = str(parsed.national_number)
    opts = listar_paises_indicativo()
    idx = 0
    for i, (i_iso, _d, _n) in enumerate(opts):
        if i_iso == iso:
            idx = i
            break
    st.session_state[f"{prefix}_tp_idx"] = idx
    st.session_state[f"{prefix}_tp_nac"] = national
    t = phonenumbers.number_type(parsed)
    if t == phonenumbers.PhoneNumberType.FIXED_LINE:
        st.session_state[f"{prefix}_tt"] = "Fixo"
    else:
        st.session_state[f"{prefix}_tt"] = "Telemóvel"


def ler_e164_de_widgets(prefix: str) -> tuple[bool, str, str]:
    """Após `render_grupo_telefone`, devolve (ok, e164 ou \"\", mensagem_erro)."""
    tipo = str(st.session_state.get(f"{prefix}_tt", "Telemóvel"))
    tipo_linha = "movel" if tipo == "Telemóvel" else "fixo"
    busca = str(st.session_state.get(f"{prefix}_tp_filtro", ""))
    opts = encontrar_por_texto_busca(busca)
    ix = st.session_state.get(f"{prefix}_tp_idx", 0)
    try:
        ix = int(ix)
    except (TypeError, ValueError):
        ix = 0
    if ix < 0 or ix >= len(opts):
        opts = listar_paises_indicativo()
        ix = 0
    iso, _dial, _nome = opts[ix]
    nacional = str(st.session_state.get(f"{prefix}_tp_nac", "") or "")
    return normalizar_telefone_e164(nacional, iso, tipo_linha)
