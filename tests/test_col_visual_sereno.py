"""Colaboradores — BeaBá Sereno (Ilha Mãe, sem `border=True`, slot + CSS)."""

from __future__ import annotations

from pathlib import Path

from tests.col_ui_contract import (
    assert_col_area_unica_shell,
    assert_col_disponibilidade_setor_na_pagina,
    assert_col_dados_parceria_na_ficha,
    assert_col_ficha_contacto_grupo_telefone,
    assert_col_mapa_equipa_na_pagina,
    assert_col_pesquisa_unificada_na_pagina,
    assert_col_relatorio_global_repasse_e24_contract,
)


def test_col_contract_alinhado_com_app_e_shell():
    assert_col_area_unica_shell()


def test_col_pesquisa_unificada_contrato():
    assert_col_pesquisa_unificada_na_pagina()


def test_col_ficha_grupo_telefone_contrato():
    assert_col_ficha_contacto_grupo_telefone()


def test_col_mapa_equipa_contrato():
    assert_col_mapa_equipa_na_pagina()


def test_col_disponibilidade_setor_contrato():
    assert_col_disponibilidade_setor_na_pagina()


def test_col_relatorio_global_repasse_e24_contrato():
    assert_col_relatorio_global_repasse_e24_contract()


def test_col_dados_parceria_contrato():
    assert_col_dados_parceria_na_ficha()


def test_page_colaboradores_sem_border_true():
    root = Path(__file__).resolve().parents[1]
    src = (root / "src" / "ui" / "page_colaboradores.py").read_text(encoding="utf-8")
    assert "border=True" not in src


def test_col_shell_css_ilha_mae_e_slot():
    from src.ui.constituicao_visual_shell import (
        get_constituicao_col_page_css,
        inject_area_unica_visual_mount,
        inject_constituicao_col_page,
    )

    assert callable(inject_area_unica_visual_mount)
    assert callable(inject_constituicao_col_page)
    css = get_constituicao_col_page_css()
    assert "bea-cv-col-slot" in css
    assert ':has(.bea-cv-col-slot)' in css
    assert '[data-testid="column"]:has(.bea-cv-col-slot)' in css
    assert '[data-testid="bea-col-slot"]' in css
    assert "body.bea-cv-col-page" in css
    assert "bea-cv-col-mother-island" in css
    assert "bea-busca-nome-sug-panel" in css
    assert "bea-col-mapa-wrap" in css
    assert "bea-col-mapa-th" in css
    assert "bea-col-disp-flag" in css
    assert "0 12px 40px rgba(118, 148, 125, 0.12)" in css
    assert "0 2px 10px rgba(0, 0, 0, 0.05)" in css


def test_render_page_colaboradores_importa_inject_constituicao_col():
    from src.ui import page_colaboradores as mod

    assert hasattr(mod, "render_page_colaboradores")
    assert callable(mod.render_page_colaboradores)
    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert "inject_constituicao_col_page()" in src
