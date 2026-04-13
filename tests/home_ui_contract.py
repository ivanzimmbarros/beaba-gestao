"""Contrato UI — Início / Cockpit (Ilha Mãe Sereno + slot em `app.py`)."""

from __future__ import annotations

from pathlib import Path


def assert_home_area_unica_shell() -> None:
    root = Path(__file__).resolve().parents[1]
    app_src = (root / "src" / "app.py").read_text(encoding="utf-8")
    assert 'class="bea-cv-home-slot"' in app_src
    assert 'data-testid="bea-home-slot"' in app_src
    assert "render_page_home" in app_src
    shell = (root / "src" / "ui" / "constituicao_visual_shell.py").read_text(encoding="utf-8")
    assert "def get_constituicao_home_page_css" in shell
    assert "def inject_constituicao_home_page" in shell
    assert "bea-cv-home-mother-island" in shell
    assert "bea-cv-home-slot" in shell
    assert "bea-cv-home-page" in shell
    assert 'querySelector(".bea-cv-home-slot")' in shell
