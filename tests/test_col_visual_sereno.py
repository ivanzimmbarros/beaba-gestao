"""Colaboradores — BeaBá Sereno (Ilha Mãe, sem `border=True`, slot + CSS)."""

from __future__ import annotations

from pathlib import Path

from tests.col_ui_contract import assert_col_area_unica_shell


def test_col_contract_alinhado_com_app_e_shell():
    assert_col_area_unica_shell()


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
    assert "0 12px 40px rgba(118, 148, 125, 0.12)" in css
    assert "0 2px 10px rgba(0, 0, 0, 0.05)" in css


def test_render_page_colaboradores_importa_inject_constituicao_col():
    from src.ui import page_colaboradores as mod

    assert hasattr(mod, "render_page_colaboradores")
    assert callable(mod.render_page_colaboradores)
    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert "inject_constituicao_col_page()" in src
