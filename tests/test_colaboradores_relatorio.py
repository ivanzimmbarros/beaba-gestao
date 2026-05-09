"""E24 Colaboradores — relatório consolidado realização/repasse (domínio puro)."""

from __future__ import annotations

from datetime import date

import pytest

from src.database.connection import create_tables, get_connection
from src.modules.colaborador import MAPA_EQUI_ESP_SEM_LABEL
from src.modules.colaboradores_relatorio import (
    LABEL_TECNICO_TZ_PT,
    agregar_metricas_repasse_linhas,
    formato_euro_centavos_pt,
    formato_percentual_bp,
    listar_linhas_relatorio_repasse_global,
    linhas_para_grid_pdf,
    quando_linha_civil_etiqueta_lisboa,
    validar_dimensao_e_seleccao_repasse_relatorio,
    validar_periodo_repasse_relatorio,
)
from src.modules.colaboradores_relatorio_pdf import montar_pdf_relatorio_repasse_landscape

from tests.test_financeiro_repasses_colaboradores import _seed_repasse_row


@pytest.fixture()
def rep_conn_cr(tmp_path, monkeypatch):
    db = tmp_path / "col_rel_repasse.db"
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(db))
    create_tables()
    c = get_connection()
    assert c is not None
    yield c
    c.close()


def test_validadores_periodo_e_multiselect() -> None:
    assert validar_periodo_repasse_relatorio(None, date(2026, 1, 10))[0] is False
    assert validar_periodo_repasse_relatorio(date(2026, 2, 1), date(2026, 1, 1))[0] is False
    assert validar_dimensao_e_seleccao_repasse_relatorio(
        "especialidade",
        especialidades=None,
        servico_ids=None,
        colaborador_ids=None,
    ) == (False, "Seleccione pelo menos uma especialidade (filtro obrigatório).")
    assert validar_dimensao_e_seleccao_repasse_relatorio(
        "servico",
        especialidades=None,
        servico_ids=[1],
        colaborador_ids=None,
    )[0]


def test_formato_pct_e_euro_repasse_repasse_bp() -> None:
    assert "5" in formato_percentual_bp(500)
    assert "€" in formato_euro_centavos_pt(199)


def test_quando_label_inclui_lisboa() -> None:
    s = quando_linha_civil_etiqueta_lisboa(data_ymd="2026-03-20", hora_inicio="09:00")
    assert LABEL_TECNICO_TZ_PT in s
    assert "20/03/2026" in s


def test_listar_linhas_modo_especialidade_nome_servico(rep_conn_cr) -> None:
    """Usa especialidade efectiva ligada ao `servico_id` criado pela seed Financeiro."""
    _, sid = _seed_repasse_row(rep_conn_cr)
    cur = rep_conn_cr.execute(
        """
        SELECT trim(IFNULL(e.nome, ''))
        FROM servicos s
        LEFT JOIN especialidades e ON e.id = s.especialidade_id
        WHERE s.id = ?
        """,
        (int(sid),),
    )
    raw = cur.fetchone()
    esp_txt = str(raw[0]).strip() if raw and raw[0] is not None else ""
    sel_list = [MAPA_EQUI_ESP_SEM_LABEL] if esp_txt == "" else [esp_txt]
    rows = listar_linhas_relatorio_repasse_global(
        rep_conn_cr,
        data_ini=date(2026, 1, 1),
        data_fim=date(2026, 12, 31),
        modo="especialidade",
        especialidades_escolhidas=sel_list,
        servico_ids=None,
        colaborador_ids=None,
    )
    assert len(rows) >= 1


def test_listar_linhas_modo_colaborador_vs_servico(rep_conn_cr) -> None:
    cid, sid = _seed_repasse_row(rep_conn_cr)
    rows_col = listar_linhas_relatorio_repasse_global(
        rep_conn_cr,
        data_ini=date(2026, 1, 1),
        data_fim=date(2026, 12, 31),
        modo="colaborador",
        especialidades_escolhidas=None,
        servico_ids=None,
        colaborador_ids=[cid],
    )
    rows_srv = listar_linhas_relatorio_repasse_global(
        rep_conn_cr,
        data_ini=date(2026, 1, 1),
        data_fim=date(2026, 12, 31),
        modo="servico",
        especialidades_escolhidas=None,
        servico_ids=[sid],
        colaborador_ids=None,
    )
    assert len(rows_col) >= 1
    assert rows_col == rows_srv
    met = agregar_metricas_repasse_linhas(rows_col)
    assert met["global"]["n_linhas"] == len(rows_col)
    assert met["global"]["repasse_cent"] == sum(r["valor_repasse_centavos"] for r in rows_col)


def test_linhas_para_grid_pdf_ultima_coluna_estado_repasse(rep_conn_cr) -> None:
    """Contrato PDF E24: cabeçalho da última coluna alinhado ao documento institucional."""
    _cid, sid = _seed_repasse_row(rep_conn_cr)
    rows = listar_linhas_relatorio_repasse_global(
        rep_conn_cr,
        data_ini=date(2026, 1, 1),
        data_fim=date(2026, 12, 31),
        modo="servico",
        especialidades_escolhidas=None,
        servico_ids=[sid],
        colaborador_ids=None,
    )
    grid = linhas_para_grid_pdf(rows)
    assert grid and grid[0][-1] == "Estado Pgto. Repasse"


def test_pdf_landscape_pdf_magic_bytes(rep_conn_cr) -> None:
    """Requer Arial/DejaVu no hospedeiro; caso contrário é skip declarado."""
    _cid, sid = _seed_repasse_row(rep_conn_cr)
    rows = listar_linhas_relatorio_repasse_global(
        rep_conn_cr,
        data_ini=date(2026, 1, 1),
        data_fim=date(2026, 12, 31),
        modo="servico",
        especialidades_escolhidas=None,
        servico_ids=[sid],
        colaborador_ids=None,
    )
    grid = linhas_para_grid_pdf(rows)
    try:
        pdf_b = montar_pdf_relatorio_repasse_landscape(
            titulo="Teste relatório QA",
            meta_filtros_texto=["Filtros smoke"],
            resumo_texto=["Resumo smoke"],
            linhas_tabela=grid,
        )
    except RuntimeError:
        pytest.skip("Fontes PDF Unicode indisponíveis neste agente/OS")
    assert pdf_b.startswith(b"%PDF")
