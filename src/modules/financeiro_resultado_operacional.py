"""Financeiro — resultado operacional consolidado (agregação para o painel do sector 1)."""

from __future__ import annotations

import sqlite3

from src.modules.financeiro_entradas_convertidas import (
    listar_linhas_gestao_entradas_convertidas_vendas,
)
from src.modules.financeiro_lancamentos_gasto import listar_lancamentos_controle
from src.modules.financeiro_repasses_colaboradores import listar_linhas_gestao_repasses
from src.modules.financeiro_saldos_clientes import listar_linhas_gestao_saldos_clientes_ativos


def _norm_cenario(cenario_entradas: str) -> str:
    k = str(cenario_entradas or "").strip().lower()
    return "recebido" if k == "recebido" else "convertido"


def _gastos_real_centavos_periodo(
    conn: sqlite3.Connection,
    *,
    mes_referencia: int | None,
    ano_referencia: int | None,
    filtro_centro_ids: list[int] | None,
    filtro_natureza_ids: list[int] | None,
    filtro_tipo_ids: list[int] | None,
) -> int:
    rows = listar_lancamentos_controle(
        conn,
        filtro_centro_ids=filtro_centro_ids,
        filtro_natureza_ids=filtro_natureza_ids,
        filtro_tipo_ids=filtro_tipo_ids,
    )
    total = 0
    for r in rows:
        if str(r.get("tipo_registo") or "").strip() != "Real":
            continue
        dcomp = str(r.get("data_competencia_iso") or "").strip()[:10]
        if ano_referencia is not None:
            if len(dcomp) != 10 or dcomp[4] != "-" or dcomp[7] != "-":
                continue
            try:
                y = int(dcomp[0:4])
            except ValueError:
                continue
            if y != int(ano_referencia):
                continue
        if mes_referencia is not None and 1 <= int(mes_referencia) <= 12:
            if len(dcomp) != 10 or dcomp[4] != "-" or dcomp[7] != "-":
                continue
            try:
                m = int(dcomp[5:7])
            except ValueError:
                continue
            if m != int(mes_referencia):
                continue
        total += int(r.get("valor_centavos") or 0)
    return int(total)


def agregar_resultado_operacional_consolidado(
    conn: sqlite3.Connection,
    *,
    mes_referencia: int | None,
    ano_referencia: int | None,
    cenario_entradas: str,
    gasto_filtro_centro_ids: list[int] | None = None,
    gasto_filtro_natureza_ids: list[int] | None = None,
    gasto_filtro_tipo_ids: list[int] | None = None,
    repasse_colaborador_ids: list[int] | None = None,
    repasse_naturezas: list[str] | None = None,
    repasse_servico_ids: list[int] | None = None,
    saldo_cliente_ids: list[int] | None = None,
    saldo_naturezas: list[str] | None = None,
    saldo_servico_ids: list[int] | None = None,
    entrada_cliente_ids: list[int] | None = None,
    entrada_naturezas: list[str] | None = None,
    entrada_servico_ids: list[int] | None = None,
    entrada_estados_pagamento: list[str] | None = None,
) -> dict[str, int]:
    """
    Consolida métricas para o painel «1. Resultado Operacional Consolidado».

    **Fórmula principal (fluxo):** ``Entradas − Gastos (Real, competência) − Repasses``.

    **Saldos de clientes:** soma da exposição em crédito activo (cancelamentos) com os
    mesmos filtros de período / dimensão que a listagem de saldos; **não** entram na linha
    «resultado» acima — servem como métrica paralela de exposição (tesouraria vs crédito em carteira).
    """
    cen = _norm_cenario(cenario_entradas)
    ent_rows = listar_linhas_gestao_entradas_convertidas_vendas(
        conn,
        cliente_ids=entrada_cliente_ids,
        naturezas=entrada_naturezas,
        servico_ids=entrada_servico_ids,
        mes=mes_referencia,
        ano=ano_referencia,
        estados_pagamento=entrada_estados_pagamento,
    )
    if cen == "recebido":
        entradas = sum(int(r["total_valor_recebido_centavos"]) for r in ent_rows)
    else:
        entradas = sum(int(r["valor_final_venda_centavos"]) for r in ent_rows)

    gastos = _gastos_real_centavos_periodo(
        conn,
        mes_referencia=mes_referencia,
        ano_referencia=ano_referencia,
        filtro_centro_ids=gasto_filtro_centro_ids,
        filtro_natureza_ids=gasto_filtro_natureza_ids,
        filtro_tipo_ids=gasto_filtro_tipo_ids,
    )

    rep_rows = listar_linhas_gestao_repasses(
        conn,
        colaborador_ids=repasse_colaborador_ids,
        naturezas=repasse_naturezas,
        servico_ids=repasse_servico_ids,
        mes=mes_referencia,
        ano=ano_referencia,
    )
    repasses = sum(int(r["valor_repasse_centavos"]) for r in rep_rows)

    sal_rows = listar_linhas_gestao_saldos_clientes_ativos(
        conn,
        cliente_ids=saldo_cliente_ids,
        naturezas=saldo_naturezas,
        servico_ids=saldo_servico_ids,
        mes=mes_referencia,
        ano=ano_referencia,
    )
    saldos = sum(int(r["saldo_restante_centavos"]) for r in sal_rows)

    resultado_fluxo = int(entradas) - int(gastos) - int(repasses)
    return {
        "entradas_centavos": int(entradas),
        "gastos_real_centavos": int(gastos),
        "repasses_centavos": int(repasses),
        "saldos_exposicao_centavos": int(saldos),
        "resultado_fluxo_centavos": int(resultado_fluxo),
    }
