"""Dashboards e relatórios — agregações sobre vendas (E08, Fase A: receita sem custo)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from src.database.connection import get_connection

GranularidadeTemporal = Literal["dia", "mes"]
DimensaoGroupBy = Literal["servico", "cliente", "colaborador", "natureza", "dia", "mes"]


@dataclass
class FiltrosDashboard:
    """Filtros aplicados às linhas `venda_itens` + cabeçalho `vendas`."""

    data_inicio: str
    data_fim: str
    cliente_ids: list[int] = field(default_factory=list)
    servico_ids: list[int] = field(default_factory=list)
    colaborador_ids: list[int] = field(default_factory=list)
    apenas_natureza_produto: bool = False


def _where(f: FiltrosDashboard) -> tuple[str, list[Any]]:
    parts = ["date(v.data_registo) >= date(?)", "date(v.data_registo) <= date(?)"]
    params: list[Any] = [f.data_inicio[:10], f.data_fim[:10]]
    if f.cliente_ids:
        ph = ",".join("?" * len(f.cliente_ids))
        parts.append(f"v.cliente_id IN ({ph})")
        params.extend(int(x) for x in f.cliente_ids)
    if f.servico_ids:
        ph = ",".join("?" * len(f.servico_ids))
        parts.append(f"vi.servico_id IN ({ph})")
        params.extend(int(x) for x in f.servico_ids)
    if f.colaborador_ids:
        ph = ",".join("?" * len(f.colaborador_ids))
        parts.append(f"vi.colaborador_id IN ({ph})")
        params.extend(int(x) for x in f.colaborador_ids)
    if f.apenas_natureza_produto:
        parts.append("s.natureza = 'Produto'")
    return " AND ".join(parts), params


SQL_FROM = """
FROM venda_itens vi
JOIN vendas v ON v.id = vi.venda_id
JOIN clientes c ON c.id = v.cliente_id
JOIN servicos s ON s.id = vi.servico_id
LEFT JOIN colaboradores col ON col.id = vi.colaborador_id
"""


def kpis(f: FiltrosDashboard) -> dict[str, int | float]:
    """
    - receita_itens_centavos: soma `total_linha_centavos` (após desconto de linha).
    - receita_cabecalhos_centavos: soma `total_final_centavos` por venda distinta (inclui desconto global).
    - n_vendas, n_linhas, quantidade_total, ticket_medio_centavos (receita cabeçalho / n_vendas).
    Fase A: «margem / lucro» = receita_itens (sem custos).
    """
    conn = get_connection()
    if not conn:
        return {}
    w, p = _where(f)
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT
              COALESCE(SUM(vi.total_linha_centavos), 0),
              COUNT(DISTINCT v.id),
              COUNT(*),
              COALESCE(SUM(vi.quantidade), 0)
            {SQL_FROM}
            WHERE {w}
            """,
            p,
        )
        r = cur.fetchone()
        rec_it = int(r[0] or 0)
        n_v = int(r[1] or 0)
        n_lin = int(r[2] or 0)
        q_tot = int(r[3] or 0)

        cur.execute(
            f"""
            SELECT COALESCE(SUM(sub.val), 0) FROM (
              SELECT DISTINCT v.id AS vid, v.total_final_centavos AS val
              {SQL_FROM}
              WHERE {w}
            ) sub
            """,
            p,
        )
        rec_cab = int(cur.fetchone()[0] or 0)
        ticket = int(rec_cab / n_v) if n_v else 0
        return {
            "receita_itens_centavos": rec_it,
            "receita_cabecalhos_centavos": rec_cab,
            "n_vendas": n_v,
            "n_linhas": n_lin,
            "quantidade_total": q_tot,
            "ticket_medio_centavos": ticket,
        }
    finally:
        conn.close()


def serie_receita_temporal(
    f: FiltrosDashboard,
    granularidade: GranularidadeTemporal,
) -> list[tuple[str, int]]:
    conn = get_connection()
    if not conn:
        return []
    w, p = _where(f)
    if granularidade == "dia":
        grp = "date(v.data_registo)"
    else:
        grp = "strftime('%Y-%m', v.data_registo)"
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT {grp} AS periodo, COALESCE(SUM(vi.total_linha_centavos), 0)
            {SQL_FROM}
            WHERE {w}
            GROUP BY periodo
            ORDER BY periodo
            """,
            p,
        )
        return [(str(a), int(b or 0)) for a, b in cur.fetchall()]
    finally:
        conn.close()


def top_n_dimensao(
    f: FiltrosDashboard,
    dimensao: DimensaoGroupBy,
    n: int,
) -> list[tuple[str, int, int]]:
    """
    Retorna lista (rótulo, receita_linhas_centavos, quantidade_somada).
    """
    n = max(1, min(100, int(n)))
    conn = get_connection()
    if not conn:
        return []
    w, p = _where(f)
    if dimensao == "servico":
        sel = "vi.nome_snapshot"
        grp = "vi.nome_snapshot, vi.servico_id"
    elif dimensao == "cliente":
        sel = "c.nome || ' (#' || c.id || ')'"
        grp = "c.id, c.nome"
    elif dimensao == "colaborador":
        sel = "COALESCE(col.nome, '(Sem colaborador)') || CASE WHEN col.id IS NULL THEN '' ELSE ' (#' || col.id || ')' END"
        grp = "col.id, col.nome"
    elif dimensao == "natureza":
        sel = "s.natureza"
        grp = "s.natureza"
    elif dimensao == "dia":
        sel = "date(v.data_registo)"
        grp = "date(v.data_registo)"
    else:
        sel = "strftime('%Y-%m', v.data_registo)"
        grp = "strftime('%Y-%m', v.data_registo)"
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT {sel} AS lbl,
                   COALESCE(SUM(vi.total_linha_centavos), 0) AS rec,
                   COALESCE(SUM(vi.quantidade), 0) AS qtd
            {SQL_FROM}
            WHERE {w}
            GROUP BY {grp}
            ORDER BY rec DESC
            LIMIT ?
            """,
            [*p, n],
        )
        return [(str(row[0]), int(row[1]), int(row[2])) for row in cur.fetchall()]
    finally:
        conn.close()


def pareto_dimensao(
    f: FiltrosDashboard,
    dimensao: DimensaoGroupBy,
    limite_barras: int = 15,
) -> list[tuple[str, int, float]]:
    """
    Pareto sobre receita de linhas: (rótulo, receita_centavos, pct_cumulativo_0_100).
    """
    limite_barras = max(5, min(50, int(limite_barras)))
    rows = top_n_dimensao(f, dimensao, limite_barras)
    if not rows:
        return []
    total = sum(r[1] for r in rows)
    if total <= 0:
        return [(lbl, rec, 0.0) for lbl, rec, _ in rows]
    acc = 0
    out: list[tuple[str, int, float]] = []
    for lbl, rec, _q in rows:
        acc += rec
        out.append((lbl, rec, round(100.0 * acc / total, 2)))
    return out


def tabela_agregada(
    f: FiltrosDashboard,
    group_by: DimensaoGroupBy,
) -> list[dict[str, Any]]:
    """Detalhe tabular para export / st.dataframe."""
    n = 500
    rows = top_n_dimensao(f, group_by, n)
    return [
        {
            "dimensão": lbl,
            "receita_linhas_€": round(rec / 100, 2),
            "quantidade": qtd,
        }
        for lbl, rec, qtd in rows
    ]


def listar_opcoes_filtro_clientes() -> list[tuple[int, str]]:
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, nome FROM clientes ORDER BY nome COLLATE NOCASE")
        return [(int(a), str(b)) for a, b in cur.fetchall()]
    finally:
        conn.close()


def listar_opcoes_filtro_servicos() -> list[tuple[int, str]]:
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, nome || ' (' || natureza || ')' FROM servicos
            ORDER BY natureza, nome COLLATE NOCASE
            """
        )
        return [(int(a), str(b)) for a, b in cur.fetchall()]
    finally:
        conn.close()


def listar_opcoes_filtro_colaboradores() -> list[tuple[int, str]]:
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, nome FROM colaboradores ORDER BY nome COLLATE NOCASE")
        return [(int(a), str(b)) for a, b in cur.fetchall()]
    finally:
        conn.close()


__all__ = [
    "DimensaoGroupBy",
    "FiltrosDashboard",
    "GranularidadeTemporal",
    "kpis",
    "listar_opcoes_filtro_clientes",
    "listar_opcoes_filtro_colaboradores",
    "listar_opcoes_filtro_servicos",
    "pareto_dimensao",
    "serie_receita_temporal",
    "tabela_agregada",
    "top_n_dimensao",
]
