"""Contrato UI — Financeiro (Ilha Mãe Sereno + slot em `app.py`)."""

from __future__ import annotations

from pathlib import Path


def assert_fin_area_unica_shell() -> None:
    root = Path(__file__).resolve().parents[1]
    app_src = (root / "src" / "app.py").read_text(encoding="utf-8")
    assert 'class="bea-cv-fin-slot"' in app_src
    assert 'data-testid="bea-fin-slot"' in app_src
    assert "render_page_financeiro" in app_src
    shell = (root / "src" / "ui" / "constituicao_visual_shell.py").read_text(encoding="utf-8")
    assert "def get_constituicao_fin_page_css" in shell
    assert "def inject_constituicao_fin_page" in shell
    assert "bea-cv-fin-mother-island" in shell
    assert "bea-cv-fin-slot" in shell
    assert "bea-cv-fin-page" in shell
    assert 'querySelector(".bea-cv-fin-slot")' in shell
