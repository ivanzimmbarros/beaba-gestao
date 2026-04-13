"""Financeiro — BeaBá Sereno (Ilha Mãe, slot + CSS)."""

from __future__ import annotations

from pathlib import Path

from tests.fin_ui_contract import assert_fin_area_unica_shell


def test_fin_contract_alinhado_com_app_e_shell():
    assert_fin_area_unica_shell()


def test_fin_shell_css_ilha_mae_e_slot():
    from src.ui.constituicao_visual_shell import (
        get_constituicao_fin_page_css,
        inject_constituicao_fin_page,
    )

    assert callable(inject_constituicao_fin_page)
    css = get_constituicao_fin_page_css()
    assert "bea-cv-fin-slot" in css
    assert ':has(.bea-cv-fin-slot)' in css
    assert '[data-testid="column"]:has(.bea-cv-fin-slot)' in css
    assert '[data-testid="bea-fin-slot"]' in css
    assert "body.bea-cv-fin-page" in css
    assert "bea-cv-fin-mother-island" in css
    assert "0 12px 40px rgba(118, 148, 125, 0.12)" in css
    assert "0 2px 10px rgba(0, 0, 0, 0.05)" in css


def test_render_page_financeiro_importa_inject_constituicao_fin():
    src = Path(__file__).resolve().parents[1] / "src" / "ui" / "page_financeiro.py"
    t = src.read_text(encoding="utf-8")
    assert "inject_constituicao_fin_page" in t
    assert "border=True" not in t
    assert "fin_gxc_btn_salvar_linha1" in t
    assert "Cadastramento de Novas Categorias" in t
    assert "alinhadas à esquerda do formulário" in t
