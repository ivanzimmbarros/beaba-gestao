"""Painel de Vendas — BeaBá Sereno (Ilha Mãe, sem `border=True`, slot + CSS)."""

from __future__ import annotations

from pathlib import Path

from tests.vnd_ui_contract import (
    assert_vnd_area_unica_shell,
    assert_vnd_pesquisa_unificada_cliente_na_pagina,
)


def test_vnd_contract_alinhado_com_app_e_shell():
    assert_vnd_area_unica_shell()


def test_vnd_pesquisa_unificada_contrato():
    assert_vnd_pesquisa_unificada_cliente_na_pagina()


def test_page_vendas_sem_border_true():
    root = Path(__file__).resolve().parents[1]
    src = (root / "src" / "ui" / "page_vendas.py").read_text(encoding="utf-8")
    assert "border=True" not in src


def test_vnd_shell_css_ilha_mae_e_slot():
    from src.ui.constituicao_visual_shell import (
        get_constituicao_vnd_page_css,
        inject_area_unica_visual_mount,
        inject_cag_visual_mount,
        inject_constituicao_vnd_page,
    )

    assert callable(inject_area_unica_visual_mount)
    assert callable(inject_cag_visual_mount)
    assert callable(inject_constituicao_vnd_page)
    css = get_constituicao_vnd_page_css()
    assert "bea-cv-vnd-slot" in css
    assert ':has(.bea-cv-vnd-slot)' in css
    assert '[data-testid="column"]:has(.bea-cv-vnd-slot)' in css
    assert '[data-testid="bea-vnd-slot"]' in css
    assert "body.bea-cv-vnd-page" in css
    assert "bea-cv-vnd-mother-island" in css
    assert "0 12px 40px rgba(118, 148, 125, 0.12)" in css
    assert "0 2px 10px rgba(0, 0, 0, 0.05)" in css
    assert "bea-busca-nome-sug-panel" in css


def test_render_page_vendas_importa_inject_constituicao_vnd():
    from src.ui import page_vendas as mod

    assert hasattr(mod, "render_page_vendas")
    assert callable(mod.render_page_vendas)
    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert "inject_constituicao_vnd_page()" in src
