"""Contrato UI — Catálogo de serviços (Ilha Mãe Sereno + slot em `app.py`)."""

from __future__ import annotations

from pathlib import Path


def assert_cat_especialidade_form_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    page = (root / "src" / "ui" / "page_catalogo.py").read_text(encoding="utf-8")
    assert "2. Especialidade *" in page
    assert "1. Natureza *" in page
    assert "3. Nome do Serviço ou Produto *" in page
    assert "listar_especialidades_por_natureza" in page
    assert "cadastrar_especialidade" in page
    assert "Confirmar tipo de registo" in page
    assert "Registar no catálogo" in page
    assert "Nova especialidade" in page and "Novo serviço" in page
    assert "_render_cat_expander_cadastro" in page
    assert "col_nat, col_esp = st.columns(2)" in page
    assert "Nova especialidade (nesta natureza)" not in page


def assert_cat_area_unica_shell() -> None:
    root = Path(__file__).resolve().parents[1]
    app_src = (root / "src" / "app.py").read_text(encoding="utf-8")
    assert 'class="bea-cv-cat-slot"' in app_src
    assert 'data-testid="bea-cat-slot"' in app_src
    assert "render_page_catalogo" in app_src
    shell = (root / "src" / "ui" / "constituicao_visual_shell.py").read_text(encoding="utf-8")
    assert "def get_constituicao_cat_page_css" in shell
    assert "def inject_constituicao_cat_page" in shell
    assert "bea-cv-cat-mother-island" in shell
    assert "bea-cv-cat-slot" in shell
    assert "bea-cv-cat-page" in shell
    assert 'querySelector(".bea-cv-cat-slot")' in shell
