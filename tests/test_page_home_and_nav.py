"""Fase 1 épico Home: `page_home` como módulo; «Início» na posição 0 da sidebar.

«Painel de Vendas» segue «Início»; «Catálogo» fica acima de «Colaboradores».
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
    assert NAV_ITEMS[1] == ("vendas", "Painel de Vendas")
    keys = [k for k, _ in NAV_ITEMS]
    assert keys.index("catalogo") < keys.index("colaboradores")
    assert ("financeiro", "Financeiro") in NAV_ITEMS


def test_sidebar_env_badge_spec_por_ambiente():
    from src.ui.shell_sidebar import _sidebar_env_badge_spec

    assert _sidebar_env_badge_spec("production") is None
    assert _sidebar_env_badge_spec("main") is None
    assert _sidebar_env_badge_spec("prod") is None

    stg = _sidebar_env_badge_spec("staging")
    assert stg is not None
    assert stg[2] == "AMBIENTE DE TESTE"
    assert stg == _sidebar_env_badge_spec("stg")

    dev = _sidebar_env_badge_spec("dev")
    assert dev is not None
    assert dev[2] == "DESENVOLVIMENTO"
    assert dev[0] == "#FEF3C7" and dev[1] == "#B45309"
    assert dev == _sidebar_env_badge_spec("develop")
    assert dev == _sidebar_env_badge_spec("local")
    assert stg[0] == dev[0] and stg[1] == dev[1] and stg[2] != dev[2]


def test_nav_clientes_agendamentos_respeita_contrato_setor4_expander():
    assert_cag_setor4_lista_dentro_expander_agendamentos()
