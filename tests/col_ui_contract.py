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


def assert_col_pesquisa_unificada_na_pagina() -> None:
    """Contrato: pesquisa unificada (Nome+NIF+Email+Tel), NIF só PT na busca, placeholder colaborador."""
    root = Path(__file__).resolve().parents[1]
    src = (root / "src" / "ui" / "page_colaboradores.py").read_text(encoding="utf-8")
    assert "pesquisa_unificada=True" in src
    assert "col_busca_nome" in src
    assert "buscar_colaboradores_por_prefixo_nome" in src
    assert "documento_internacional=False" in src
    assert "Nome do colaborador" in src
    assert 'entidade_nome="colaborador"' in src


def assert_col_dados_parceria_na_ficha() -> None:
    """Ficha: secção «Dados da Parceria», IBAN, actividade/contrato Sim/Não, documento complementar na linha do NIF."""
    root = Path(__file__).resolve().parents[1]
    src = (root / "src" / "ui" / "page_colaboradores.py").read_text(encoding="utf-8")
    assert "Dados da Parceria" in src
    assert "Passaporte, Título de Residência ou Cartão Cidadão" in src
    assert "Atividade Econômica Aberta?" in src
    assert "Contrato de Prestação de Serviço assinado?" in src
    assert "Dados Bancários — IBAN" in src
    assert "_doc_par" in src
    assert "iban_dados_bancarios" in src


def assert_col_ficha_contacto_grupo_telefone() -> None:
    """Ficha: mesmo bloco telefónico que Clientes e Agendamentos (`telefone_widgets`)."""
    root = Path(__file__).resolve().parents[1]
    src = (root / "src" / "ui" / "page_colaboradores.py").read_text(encoding="utf-8")
    assert "render_grupo_telefone" in src
    assert "ler_e164_de_widgets" in src
    assert "preencher_session_telefone_de_e164" in src
    assert "Contacto principal *" in src


def assert_col_mapa_equipa_na_pagina() -> None:
    """Contrato: vitrine 3×3 substituída por Mapa da Equipa (filtros + tabela + módulo)."""
    root = Path(__file__).resolve().parents[1]
    src = (root / "src" / "ui" / "page_colaboradores.py").read_text(encoding="utf-8")
    assert "Mapa da Equipa" in src
    assert "col_mapa_natureza" in src
    assert "col_mapa_especialidade" in src
    assert "col_mapa_svc" in src
    assert "col_mapa_pesquisar" in src
    assert "listar_colaboradores_mapa_equipa" in src
    assert "resolver_conjunto_servicos_mapa_equipa" in src
    assert "listar_colaboradores_vitrine" not in src
    assert "bea-col-mapa-wrap" in src
    assert "bea-col-mapa-th" in src
    assert "type=\"tertiary\"" in src or "type='tertiary'" in src


def assert_col_disponibilidade_setor_na_pagina() -> None:
    """Contrato: ilha «Disponibilidade e calendário operacional» fora da ficha + calendário em bea-proto-scope."""
    root = Path(__file__).resolve().parents[1]
    pg = (root / "src" / "ui" / "page_colaboradores.py").read_text(encoding="utf-8")
    ui = (root / "src" / "ui" / "colaboradores_disponibilidade_ui.py").read_text(encoding="utf-8")
    sh = (root / "src" / "ui" / "constituicao_visual_shell.py").read_text(encoding="utf-8")
    assert "render_colaboradores_disponibilidade_setor" in pg
    assert "3. Disponibilidade e calendário operacional" in ui
    assert "bea-col-disp-flag" in ui
    assert "bea-proto-scope" in ui
    assert "confirmar_plano_publicado" in ui
    assert "bea-col-disp-flag" in sh
    assert "filt_resumo" in ui
    assert "listar_colaboradores_mapa_equipa(ids_nat)" in ui
