"""Catálogo de serviços — BeaBá Sereno (Ilha Mãe, slot + CSS)."""

from __future__ import annotations

from pathlib import Path

from tests.cat_ui_contract import assert_cat_area_unica_shell, assert_cat_especialidade_form_contract


def test_cat_contract_alinhado_com_app_e_shell():
    assert_cat_area_unica_shell()


def test_cat_especialidade_ui_contract():
    assert_cat_especialidade_form_contract()


def test_page_catalogo_sem_border_true():
    root = Path(__file__).resolve().parents[1]
    src = (root / "src" / "ui" / "page_catalogo.py").read_text(encoding="utf-8")
    assert "border=True" not in src


def test_cat_shell_css_ilha_mae_e_slot():
    from src.ui.constituicao_visual_shell import (
        get_constituicao_cat_page_css,
        inject_area_unica_visual_mount,
        inject_constituicao_cat_page,
    )

    assert callable(inject_area_unica_visual_mount)
    assert callable(inject_constituicao_cat_page)
    css = get_constituicao_cat_page_css()
    assert "bea-cv-cat-slot" in css
    assert ':has(.bea-cv-cat-slot)' in css
    assert '[data-testid="column"]:has(.bea-cv-cat-slot)' in css
    assert '[data-testid="bea-cat-slot"]' in css
    assert "body.bea-cv-cat-page" in css
    assert "bea-cv-cat-mother-island" in css
    assert "0 12px 40px rgba(118, 148, 125, 0.12)" in css
    assert "0 2px 10px rgba(0, 0, 0, 0.05)" in css


def test_render_page_catalogo_importa_inject_constituicao_cat():
    from src.ui import page_catalogo as mod

    assert hasattr(mod, "render_page_catalogo")
    assert callable(mod.render_page_catalogo)
    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert "inject_constituicao_cat_page()" in src
