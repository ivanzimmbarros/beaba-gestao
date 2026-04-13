"""Contrato UI — Colaboradores (Ilha Mãe Sereno + slot em `app.py`)."""

from __future__ import annotations

from pathlib import Path


def assert_col_area_unica_shell() -> None:
    root = Path(__file__).resolve().parents[1]
    app_src = (root / "src" / "app.py").read_text(encoding="utf-8")
    assert 'class="bea-cv-col-slot"' in app_src
    assert 'data-testid="bea-col-slot"' in app_src
    assert "render_page_colaboradores" in app_src
    shell = (root / "src" / "ui" / "constituicao_visual_shell.py").read_text(encoding="utf-8")
    assert "def get_constituicao_col_page_css" in shell
    assert "def inject_constituicao_col_page" in shell
    assert "bea-cv-col-mother-island" in shell
    assert "bea-cv-col-slot" in shell
    assert "bea-cv-col-page" in shell
    assert 'querySelector(".bea-cv-col-slot")' in shell
