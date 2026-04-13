"""Contrato UI — Painel de Vendas (Ilha Mãe Sereno + slot em `app.py`)."""

from __future__ import annotations

from pathlib import Path


def assert_vnd_area_unica_shell() -> None:
    root = Path(__file__).resolve().parents[1]
    app_src = (root / "src" / "app.py").read_text(encoding="utf-8")
    assert 'class="bea-cv-vnd-slot"' in app_src
    assert 'data-testid="bea-vnd-slot"' in app_src
    assert 'elif page == "vendas"' in app_src
    shell = (root / "src" / "ui" / "constituicao_visual_shell.py").read_text(encoding="utf-8")
    assert "def get_constituicao_vnd_page_css" in shell
    assert "def inject_constituicao_vnd_page" in shell
    assert "bea-cv-vnd-mother-island" in shell
    assert "def inject_area_unica_visual_mount" in shell
