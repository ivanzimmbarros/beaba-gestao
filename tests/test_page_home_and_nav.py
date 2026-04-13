"""Fase 1 épico Home: `page_home` como módulo; «Início» na posição 0 da sidebar.

A entrada «Clientes e Agendamentos» aponta para a página consolidada; o Setor 4 dessa página
mantém a listagem dentro do expander «Agendamentos» (contrato em `cag_setor4_ui_contract`).
"""

from __future__ import annotations

from tests.cag_setor4_ui_contract import assert_cag_setor4_lista_dentro_expander_agendamentos


def test_page_home_expoe_render_page_home():
    from src.ui import page_home as mod

    assert hasattr(mod, "render_page_home")
    assert callable(mod.render_page_home)


def test_page_home_plotly_donut_smoke():
    from src.ui.page_home import _figure_donut_hoje_semana, _figure_donut_taxa_cancelamento

    assert _figure_donut_hoje_semana(1, 3).data
    assert _figure_donut_taxa_cancelamento(None).data


def test_shell_sidebar_nav_items_inicio_posicao_zero():
    from src.ui.shell_sidebar import NAV_ITEMS

    assert len(NAV_ITEMS) >= 1
    assert NAV_ITEMS[0] == ("home", "Início")
    assert NAV_ITEMS[1][0] == "clientes_agendamentos"
    assert ("financeiro", "Financeiro") in NAV_ITEMS


def test_nav_clientes_agendamentos_respeita_contrato_setor4_expander():
    assert_cag_setor4_lista_dentro_expander_agendamentos()
