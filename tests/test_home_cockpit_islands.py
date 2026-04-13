"""Cockpit Home — ilhas sem border Streamlit, marcador e Panorama HTML (Template Master)."""

from __future__ import annotations

from pathlib import Path

from src.ui.home_cockpit_ui_helpers import (
    HOME_ISLAND_MARK_CLASS,
    home_island_mark_html,
    panorama_card_block_html,
)


def test_home_island_mark_class_present():
    h = home_island_mark_html()
    assert HOME_ISLAND_MARK_CLASS in h
    assert "bea-cv-home-island-mark" in h


def test_panorama_card_block_material_and_serif_title():
    h = panorama_card_block_html(
        material_icon="euro_symbol",
        title="Estimativa no mês",
        value_display="€ 10,00",
        testid="bea-home-card-estimativa",
    )
    assert "material-symbols-outlined" in h
    assert "euro_symbol" in h
    assert "bea-cv-pano-icon-wrap" in h
    assert "bea-cv-pano-card-h" in h
    assert "bea-cv-panorama-card-val" in h
    assert 'data-testid="bea-home-card-estimativa"' in h


def test_page_home_sem_st_container_border_true():
    root = Path(__file__).resolve().parents[1]
    src = (root / "src" / "ui" / "page_home.py").read_text(encoding="utf-8")
    assert "border=True" not in src


def test_constituicao_cockpit_css_ilha_selector():
    from src.ui.constituicao_visual_shell import (
        get_constituicao_home_cockpit_extra_css,
        get_constituicao_home_page_css,
    )

    css_c = get_constituicao_home_cockpit_extra_css()
    assert "bea-cv-home-island-mark" in css_c
    assert "Material+Symbols+Outlined" in css_c
    assert ":has(.bea-cv-home-slot)" in css_c
    assert "box-shadow: none !important" in css_c

    css_p = get_constituicao_home_page_css()
    assert "bea-cv-home-mother-island" in css_p
    assert "rgba(118, 148, 125, 0.12)" in css_p or "118, 148, 125, 0.12" in css_p


def test_constituicao_shell_sidebar_ativo_sem_borda_esquerda():
    from src.ui.constituicao_visual_shell import get_constituicao_shell_css

    css = get_constituicao_shell_css()
    assert "border-left: 4px solid" not in css
    assert "rgba(255, 255, 255, 0.15)" in css
