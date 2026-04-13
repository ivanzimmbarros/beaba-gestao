"""CAG — BeaBá Sereno: sem border Streamlit, ilhas no shell, cards métricas com ícones."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cag_setor4_ui_contract import assert_cag_setor4_lista_dentro_expander_agendamentos


def test_cag_setor4_contract_alinhado_com_shell_sereno():
    """Setor 4: lista no expander Agendamentos (contrato partilhado com E20)."""
    assert_cag_setor4_lista_dentro_expander_agendamentos()


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


def test_cag_shell_css_ilha_mae_e_slot():
    from src.ui.constituicao_visual_shell import (
        get_constituicao_cag_page_css,
        inject_cag_visual_mount,
    )

    assert callable(inject_cag_visual_mount)
    css = get_constituicao_cag_page_css()
    assert "bea-cv-cag-slot" in css
    assert ':has(.bea-cv-cag-slot)' in css
    assert '[data-testid="column"]:has(.bea-cv-cag-slot)' in css
    assert '[data-testid="bea-cag-slot"]' in css
    assert "body.bea-cv-cag-page" in css
    assert "bea-cv-cag-mother-island" in css
    assert "0 12px 40px rgba(118, 148, 125, 0.12)" in css
    assert "0 2px 10px rgba(0, 0, 0, 0.05)" in css
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
