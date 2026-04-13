"""Contrato UI — Painel de Vendas (Ilha Mãe Sereno + slot em `app.py`)."""

from __future__ import annotations

from pathlib import Path


def assert_vnd_pesquisa_unificada_cliente_na_pagina() -> None:
    """Contrato: área «1. Pesquisa de clientes» com modo unificado (Nome+NIF+Email+Tel), sem doc na busca."""
    root = Path(__file__).resolve().parents[1]
    src = (root / "src" / "ui" / "page_vendas.py").read_text(encoding="utf-8")
    assert "pesquisa_unificada=True" in src
    assert "vnd_busca_nome" in src
    assert "buscar_clientes_por_prefixo_nome" in src
    assert "documento_internacional=False" in src


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
    assert "bea-busca-nome-sug-panel" in shell


def assert_vnd_editar_cliente_number_input_sem_value_duplicado_session() -> None:
    """Contrato Streamlit: form editar ficha (prefixo *_vc_) — sem value= em number_input com key já primada."""
    root = Path(__file__).resolve().parents[1]
    src = (root / "src" / "ui" / "page_vendas.py").read_text(encoding="utf-8")
    assert 'value=int(st.session_state.get(f"{p}_qfil"' not in src
    assert 'value=min(10, int(st.session_state.get(f"{p}_nem"' not in src
