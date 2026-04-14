"""Consultas para a área Financeiro — gestão de repasses a colaboradores (E18)."""

from __future__ import annotations

import sqlite3
from datetime import date

# Estados de agendamento: concluído ou realizado com pagamento ainda incompleto (parcial).
_STATUS_REPASSE_UI = ("CONCLUIDO", "REALIZADO_PENDENTE_PGTO")


def _iso_para_dd_mm_yyyy(iso: str | None) -> str:
    if not iso:
        return ""
    part = (iso or "").strip()[:10]
    if len(part) < 10 or part[4] != "-" or part[7] != "-":
        return ""
    return f"{part[8:10]}/{part[5:7]}/{part[0:4]}"


def listar_colaboradores_para_filtro_repasse(conn: sqlite3.Connection) -> list[tuple[int, str]]:
    cur = conn.execute(
        """
        SELECT id, nome FROM colaboradores
        ORDER BY nome COLLATE NOCASE
        """
    )
    return [(int(a), str(b)) for a, b in cur.fetchall()]


def listar_naturezas_servico_para_filtro_repasse(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute(
        """
        SELECT DISTINCT trim(natureza) AS n
        FROM servicos
        WHERE trim(coalesce(natureza, '')) != ''
        ORDER BY n COLLATE NOCASE
        """
    )
    return [str(r[0]) for r in cur.fetchall() if r[0]]


def listar_servicos_para_filtro_repasse(conn: sqlite3.Connection) -> list[tuple[int, str]]:
    cur = conn.execute(
        """
        SELECT id, nome FROM servicos
        ORDER BY nome COLLATE NOCASE
        """
    )
    return [(int(a), str(b)) for a, b in cur.fetchall()]


def listar_anos_com_repasses(conn: sqlite3.Connection) -> list[int]:
    ph = ",".join("?" for _ in _STATUS_REPASSE_UI)
    cur = conn.execute(
        f"""
        SELECT DISTINCT CAST(strftime('%Y', a.data_agendamento) AS INTEGER) AS y
        FROM repasse_linhas rl
        INNER JOIN agendamentos a ON a.id = rl.agendamento_id
        WHERE a.status IN ({ph})
        ORDER BY y DESC
        """,
        list(_STATUS_REPASSE_UI),
    )
    years = [int(r[0]) for r in cur.fetchall() if r[0] is not None]
    y0 = date.today().year
    if y0 not in years:
        years.append(y0)
    return sorted(set(years), reverse=True)


def listar_linhas_gestao_repasses(
    conn: sqlite3.Connection,
    *,
    colaborador_ids: list[int] | None = None,
    naturezas: list[str] | None = None,
    servico_ids: list[int] | None = None,
    mes: int | None = None,
    ano: int | None = None,
) -> list[dict[str, object]]:
    """
    Uma linha por `repasse_linhas`, apenas agendamentos concluídos ou com pagamento parcial
    (`REALIZADO_PENDENTE_PGTO`).
    """
    fc = [int(x) for x in (colaborador_ids or [])]
    fn = [str(x).strip() for x in (naturezas or []) if str(x).strip()]
    ft = [int(x) for x in (servico_ids or [])]

    sql = f"""
        SELECT
            co.nome,
            s.natureza,
            s.nome,
            rl.percentual_bp,
            rl.base_calculo_centavos,
            rl.valor_repasse_centavos,
            a.data_agendamento
        FROM repasse_linhas rl
        INNER JOIN agendamentos a ON a.id = rl.agendamento_id
        INNER JOIN colaboradores co ON co.id = rl.colaborador_id
        INNER JOIN servicos s ON s.id = a.servico_id
        WHERE a.status IN ({",".join("?" for _ in _STATUS_REPASSE_UI)})
    """
    params: list = list(_STATUS_REPASSE_UI)
    if fc:
        sql += " AND rl.colaborador_id IN (" + ",".join("?" for _ in fc) + ")"
        params.extend(fc)
    if fn:
        sql += " AND trim(s.natureza) IN (" + ",".join("?" for _ in fn) + ")"
        params.extend(fn)
    if ft:
        sql += " AND a.servico_id IN (" + ",".join("?" for _ in ft) + ")"
        params.extend(ft)
    if mes is not None and 1 <= int(mes) <= 12:
        sql += " AND CAST(strftime('%m', a.data_agendamento) AS INTEGER) = ?"
        params.append(int(mes))
    if ano is not None:
        sql += " AND CAST(strftime('%Y', a.data_agendamento) AS INTEGER) = ?"
        params.append(int(ano))
    sql += " ORDER BY a.data_agendamento DESC, a.id DESC, rl.id DESC"

    cur = conn.execute(sql, params)
    out: list[dict[str, object]] = []
    for r in cur.fetchall():
        bp = r[3]
        out.append(
            {
                "colaborador_nome": str(r[0] or ""),
                "natureza_servico": str(r[1] or ""),
                "nome_servico": str(r[2] or ""),
                "percentual_bp": int(bp) if bp is not None else None,
                "base_calculo_centavos": int(r[4] or 0),
                "valor_repasse_centavos": int(r[5] or 0),
                "data_execucao_iso": str(r[6] or "")[:10],
                "data_execucao_dm": _iso_para_dd_mm_yyyy(str(r[6] or "")),
            }
        )
    return out
