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


def assert_cag_dados_agendamento_tipo_virtual_widgets() -> None:
    """Contrato: Dados do Agendamento — tipo presencial/virtual e sala virtual (CAG)."""
    src = _CAG_PAGE.read_text(encoding="utf-8")
    assert "##### Dados do Agendamento" in src
    assert "Tipo de Atendimento *" in src
    assert "cag_ag_tipo_atendimento" in src
    assert "Sala virtual disponibilizada?" in src
    assert "cag_ag_sala_virtual" in src
