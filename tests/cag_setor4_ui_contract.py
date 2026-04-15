"""
Contrato UI CAG — Setor 4 (2026-04): «Lista de agendamentos» e `_cag_setor4_render_list_island`
obrigatoriamente dentro do `st.expander("Agendamentos", ...)`.

Usado por testes unitários e pela fatia E20 em `e2e_stress_test.py`.
"""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_CAG_PAGE = _REPO / "src" / "ui" / "page_clientes_agendamentos.py"
_SETOR4_START = "def _render_cag_setor4_gestao_agendamentos"
_NEXT_FN = "\ndef render_page_clientes_agendamentos"
_LIST_ISLAND_START = "def _cag_setor4_render_list_island"
_LIST_ISLAND_NEXT = "\ndef _render_cag_setor4_gestao_agendamentos"
_DATOS_AG_FORM_START = "def _cag_setor4_render_dados_ag_form_e_wizards"
_DATOS_AG_FORM_NEXT = "\ndef _cag_setor4_render_list_island"
_CONV_PAC_START = "def _cag_render_conversao_pacote_hoje_block"
_CONV_PAC_NEXT = "\ndef _cag_setor4_render_dados_ag_form_e_wizards"


def _render_setor4_source_block(src: str) -> str:
    start = src.find(_SETOR4_START)
    if start == -1:
        raise AssertionError(
            f"{_SETOR4_START!r} não encontrado em page_clientes_agendamentos.py"
        )
    rel = src[start:]
    end_off = rel.find(_NEXT_FN)
    if end_off == -1:
        raise AssertionError(
            "Não foi possível delimitar _render_cag_setor4_gestao_agendamentos "
            "(próxima função render_page_clientes_agendamentos ausente)."
        )
    return rel[:end_off]


def _list_island_source_block(src: str) -> str:
    start = src.find(_LIST_ISLAND_START)
    if start == -1:
        raise AssertionError(f"{_LIST_ISLAND_START!r} não encontrado em page_clientes_agendamentos.py")
    rel = src[start:]
    end_off = rel.find(_LIST_ISLAND_NEXT)
    if end_off == -1:
        raise AssertionError(
            "Não foi possível delimitar _cag_setor4_render_list_island "
            "(próxima função _render_cag_setor4_gestao_agendamentos ausente)."
        )
    return rel[:end_off]


def assert_cag_setor4_lista_dentro_expander_agendamentos() -> None:
    """Falha com AssertionError se o contrato Setor 4 for violado."""
    src = _CAG_PAGE.read_text(encoding="utf-8")
    fn = _render_setor4_source_block(src)
    if 'with st.expander("Agendamentos"' not in fn:
        raise AssertionError('Setor 4: obrigatório `with st.expander("Agendamentos"`')
    if "calendário e formulário" in fn:
        raise AssertionError(
            "Setor 4: rótulo legado «Agendamentos — calendário e formulário» não deve existir"
        )
    i_exp = fn.find('with st.expander("Agendamentos"')
    i_title = fn.find('"Lista de agendamentos"')
    i_list = fn.find("_cag_setor4_render_list_island")
    if i_list == -1:
        raise AssertionError("Setor 4: _cag_setor4_render_list_island ausente")
    if i_title == -1:
        raise AssertionError('Setor 4: título "Lista de agendamentos" ausente')
    if not (0 <= i_exp < i_title < i_list):
        raise AssertionError(
            "Setor 4: ordem obrigatória expander Agendamentos → título Lista → "
            f"_cag_setor4_render_list_island (índices {i_exp}, {i_title}, {i_list})"
        )
    if fn.find("_cag_setor4_render_list_island", 0, i_exp) != -1:
        raise AssertionError("Setor 4: listagem não pode ser chamada antes do expander")
    isl = _list_island_source_block(src)
    if "Seleccionar agendamento (página actual)" in isl:
        raise AssertionError(
            "Setor 4: o selector legado «Seleccionar agendamento (página actual)» foi removido — "
            "usar tabela com selecção de linha."
        )
    if "st.dataframe" not in isl:
        raise AssertionError("Setor 4: listagem deve usar `st.dataframe` com selecção de linha.")
    if "_cag_df_selected_rows" not in src:
        raise AssertionError("Setor 4: helper `_cag_df_selected_rows` ausente em page_clientes_agendamentos.py")


def _conversao_pacote_hoje_source_block(src: str) -> str:
    start = src.find(_CONV_PAC_START)
    if start == -1:
        raise AssertionError(
            f"{_CONV_PAC_START!r} não encontrado em page_clientes_agendamentos.py"
        )
    end = src.find(_CONV_PAC_NEXT, start)
    if end == -1:
        raise AssertionError(
            "Não foi possível delimitar _cag_render_conversao_pacote_hoje_block "
            "(próxima função _cag_setor4_render_dados_ag_form_e_wizards ausente)."
        )
    return src[start:end]


def _dados_ag_form_source_block(src: str) -> str:
    start = src.find(_DATOS_AG_FORM_START)
    if start == -1:
        raise AssertionError(
            f"{_DATOS_AG_FORM_START!r} não encontrado em page_clientes_agendamentos.py"
        )
    end = src.find(_DATOS_AG_FORM_NEXT, start)
    if end == -1:
        raise AssertionError(
            "Não foi possível delimitar _cag_setor4_render_dados_ag_form_e_wizards "
            "(próxima função _cag_setor4_render_list_island ausente)."
        )
    return src[start:end]


def assert_cag_conversao_pacote_hoje_no_form_dados_agendamento() -> None:
    """Contrato: helper de conversão + invocação após o form, antes de `if submitted:`."""
    src = _CAG_PAGE.read_text(encoding="utf-8")
    conv = _conversao_pacote_hoje_source_block(src)
    if "Converter para consumo de pacote (hoje)" not in conv:
        raise AssertionError("CAG: expander «Converter para consumo de pacote (hoje)» ausente")
    if "converter_agendamento_avulso_para_consumo_pacote(" not in conv:
        raise AssertionError("CAG: chamada a converter_agendamento_avulso_para_consumo_pacote ausente")
    blk = _dados_ag_form_source_block(src)
    if "_cag_render_conversao_pacote_hoje_block(" not in blk:
        raise AssertionError("CAG: _cag_render_conversao_pacote_hoje_block ausente no form dados ag.")
    i_btn = blk.find('st.form_submit_button("Salvar Agendamento"')
    i_conv = blk.find("_cag_render_conversao_pacote_hoje_block")
    i_sub = blk.find("if submitted:")
    if i_btn == -1 or i_conv == -1 or i_sub == -1:
        raise AssertionError(
            f"CAG: ordem Salvar → conversão pacote → submitted incompleta ({i_btn}, {i_conv}, {i_sub})"
        )
    if not (i_btn < i_conv < i_sub):
        raise AssertionError(
            "CAG: obrigatório `form_submit_button` Salvar Agendamento → "
            "_cag_render_conversao_pacote_hoje_block → `if submitted:`"
        )


def assert_cag_dados_agendamento_tipo_virtual_widgets() -> None:
    """Contrato: Dados do Agendamento — tipo presencial/virtual e sala virtual (CAG)."""
    src = _CAG_PAGE.read_text(encoding="utf-8")
    assert "##### Dados do Agendamento" in src
    assert "Tipo de Atendimento *" in src
    assert "cag_ag_tipo_atendimento" in src
    assert "Sala virtual disponibilizada?" in src
    assert "cag_ag_sala_virtual" in src
    assert "CAG_AG_STATUS_UI_KEY" in src
