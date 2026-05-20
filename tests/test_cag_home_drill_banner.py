"""Faixa drill-down Início → CAG (Panorama Global)."""

from __future__ import annotations

from src.ui.home_cockpit_ui_helpers import cag_home_drill_banner_html


def test_cag_home_drill_banner_centered_markup():
    h = cag_home_drill_banner_html(
        "Pesquise um cliente e reveja a lista de agendamentos pendentes confirmação desse mês."
    )
    assert "bea-cv-cag-home-drill-banner" in h
    assert "bea-cv-cag-home-drill-banner-t" in h
    assert "pendentes confirmação" in h


def test_cag_home_drill_banner_allows_strong():
    h = cag_home_drill_banner_html("Existem <strong>3</strong> agendamentos.")
    assert "<strong>3</strong>" in h
