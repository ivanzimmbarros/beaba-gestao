"""Contrato UI — Governança prod Sereno (`page_governanca.py` + slot em `app.py`)."""

from __future__ import annotations

from pathlib import Path


def assert_gov_shell_slot_e_inject_na_app_constituicao() -> None:
    root = Path(__file__).resolve().parents[1]
    app_src = (root / "src" / "app.py").read_text(encoding="utf-8")
    assert 'class="bea-cv-gov-slot"' in app_src
    assert 'data-testid="bea-gov-slot"' in app_src
    assert "render_page_governanca" in app_src
    shell = (root / "src" / "ui" / "constituicao_visual_shell.py").read_text(encoding="utf-8")
    assert "def get_constituicao_gov_page_css" in shell
    assert "def inject_constituicao_gov_page" in shell
    assert ".bea-cv-gov-slot" in shell


def assert_governanca_sector_operacional_na_pagina() -> None:
    root = Path(__file__).resolve().parents[1]
    pg = (root / "src" / "ui" / "page_governanca.py").read_text(encoding="utf-8")
    assert "st.tabs" in pg
    assert "listar_auditoria" in pg
    assert "Filtrar registos por módulo" in pg
    assert "Auditoria de utilizadores e acessos" in pg
    assert "Log horário" in pg
    assert "Estados de recuperação" in pg
    assert "Painel executivo de resiliência" in pg
    assert "Status de Integridade dos Dados" in pg
    assert "Sincronia com o Sistema" in pg
    assert "⏱️ [TEMPO DE RECUPERAÇÃO]" in pg
    assert "Relatório de Auditoria de Dados (Drill)" in pg
    assert "Executar Backup Agora" in pg
    assert "restore_test_drill.py" in pg
    assert "backup_hourly" in pg
    assert "gha_restore_state.json" in pg
    assert "staging_restore_drill_state.json" in pg


def assert_sidebar_governanca_reservada_admin() -> None:
    root = Path(__file__).resolve().parents[1]
    sh = (root / "src" / "ui" / "shell_sidebar.py").read_text(encoding="utf-8")
    assert '("governanca", "Governança")' in sh
    assert 'if p == "admin"' in sh
    assert "_nav_items_para_perfil" in sh


def assert_constituicao_gov_css_horizonte_ilhas_master() -> None:
    """Paridade técnica com Catálogo: Horizonte 300px/150 mobile + Ilha #FFFFFF radius 20 + sombras."""
    from src.ui.constituicao_visual_shell import CV_CREME, get_constituicao_gov_page_css

    css = get_constituicao_gov_page_css()
    assert "bea-cv-gov-slot" in css
    assert "300px" in css
    assert "768px" in css
    assert "20px" in css and "border-radius" in css
    assert CV_CREME in css
    assert "118, 148, 125" in css and "0.12" in css


def test_gov_ui_contracts_consolidados() -> None:
    assert_gov_shell_slot_e_inject_na_app_constituicao()
    assert_governanca_sector_operacional_na_pagina()
    assert_sidebar_governanca_reservada_admin()


def test_governanca_visual_master_paridade_gov_vs_cat_ficheiro() -> None:
    assert_constituicao_gov_css_horizonte_ilhas_master()
