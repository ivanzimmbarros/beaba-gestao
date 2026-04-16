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


def assert_fin_repasses_sector_na_pagina() -> None:
    """Contrato: sector «2. Repasses», expander, módulo e botões de pesquisa (paridade com outros setores)."""
    root = Path(__file__).resolve().parents[1]
    src = (root / "src" / "ui" / "page_financeiro.py").read_text(encoding="utf-8")
    assert '2. Repasses' in src
    assert "Gestão de Repasses para os Colaboradores" in src
    assert "listar_linhas_gestao_repasses" in src
    assert "financeiro_repasses_colaboradores" in src
    assert "fin_rep_filt_v" in src
    assert "fin_rep_btn_pesquisar" in src
    assert "fin_rep_btn_limpar" in src
    assert "_fin_rep_limpar_pending" in src
    assert "Especialidades" in src
    assert "filtra_metadados_servicos_por_naturezas" in src
    assert "filtra_metadados_servicos_por_especialidades" in src
    assert "listar_servicos_metadados_para_filtro_repasse" in src


def assert_fin_repasses_filtros_cadeia_e_layout_na_pagina() -> None:
    """Contrato: filtro em cadeia Natureza → Especialidades → Serviço, 6 colunas + estado aplicado."""
    root = Path(__file__).resolve().parents[1]
    src = (root / "src" / "ui" / "page_financeiro.py").read_text(encoding="utf-8")
    assert "rp1, rp2, rp3, rp4, rp5, rp6 = st.columns(6" in src
    assert "REPASSE_ESP_SEM_LABEL" in src
    assert "fin_rep_apl_esp" in src
    assert "fin_rep_f" in src and "_ms_esp" in src
    assert "Natureza do Serviço" in src
    assert "Nome do Serviço" in src
