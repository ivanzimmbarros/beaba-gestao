"""CAG — BeaBá Sereno: sem border Streamlit, ilhas no shell, cards métricas com ícones."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_page_cag_sem_border_true():
    root = Path(__file__).resolve().parents[1]
    src = (root / "src" / "ui" / "page_clientes_agendamentos.py").read_text(encoding="utf-8")
    assert "border=True" not in src


def test_cag_metric_card_html_material_e_serif():
    from src.ui import page_clientes_agendamentos as cag

    h = cag._cag_metric_card_html(
        material_icon="euro_symbol",
        title="Valor total",
        body_html="<p>x</p>",
    )
    assert "material-symbols-outlined" in h
    assert "euro_symbol" in h
    assert "bea-cv-cag-metric-icon" in h
    assert "bea-cv-cag-metric-title" in h


def test_cag_shell_css_ilha_mae_e_pagina_ativa():
    from src.ui.constituicao_visual_shell import (
        cag_mother_mark_html,
        get_constituicao_cag_page_css,
    )

    assert "bea-cv-cag-mother-mark" in cag_mother_mark_html()
    css = get_constituicao_cag_page_css()
    assert "bea-cv-cag-page-active" in css
    assert "bea-cv-cag-mother-mark" in css
    assert "0 12px 40px rgba(118, 148, 125, 0.12)" in css
    assert "bea-cv-cag-metric-card" in css
    assert "Material+Symbols+Outlined" in css


@pytest.mark.parametrize(
    "fn",
    (
        "cag_valores_setor2_identificacao_basica",
        "_html_linhas_natureza",
        "_cag_metric_card_html",
    ),
)
def test_cag_helpers_exportados_para_e2e(fn: str):
    from src.ui import page_clientes_agendamentos as cag

    assert hasattr(cag, fn)
    assert callable(getattr(cag, fn))
