#!/usr/bin/env python3
"""
E19 — ETL Analytics de alta performance.

Gera tabelas prefixadas `dw_` no SQLite da aplicação. Toda a lógica pesada
(carga horária, recorrência por cliente_id, LTV real alinhado ao ledger E18)
fica aqui; a UI Streamlit deve limitar-se a `SELECT * FROM dw_...`.

Regras:
- `hora_inicio` / `hora_fim` (TEXT HH:MM) → `carga_horaria_h` (REAL, horas).
- Recorrência ancorada em `cliente_id` (visitas / média de dias entre visitas).
- LTV Real: exclui `vendas.estado_pagamento = 'pendente'`; liquidação =
  soma `venda_pagamento_linhas` se > 0, senão legado `venda_pagamentos`
  (igual a `credito_ledger.total_liquidado_venda_centavos`).
  Receita LTV = min(liquidado, esperado) com esperado = total_final − crédito abatido.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

__version__ = "1.0.0"

_HHMM = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*$")

DW_TABLES_DROP_ORDER = (
    "dw_etl_run",
    "dw_cliente_kpi",
    "dw_fact_venda",
    "dw_fact_agendamento",
)


def parse_hhmm_to_minutes(s: str) -> int | None:
    m = _HHMM.match((s or "").strip())
    if not m:
        return None
    h, mm = int(m.group(1)), int(m.group(2))
    if h > 23 or mm > 59:
        return None
    return h * 60 + mm


def carga_horaria_decimal(hora_inicio: str, hora_fim: str) -> float | None:
    a = parse_hhmm_to_minutes(hora_inicio)
    b = parse_hhmm_to_minutes(hora_fim)
    if a is None or b is None or b <= a:
        return None
    return round((b - a) / 60.0, 4)


def _liquidado_venda_centavos(cur: sqlite3.Cursor, venda_id: int) -> int:
    cur.execute(
        "SELECT COALESCE(SUM(valor_centavos), 0) FROM venda_pagamento_linhas WHERE venda_id = ?",
        (int(venda_id),),
    )
    s = int(cur.fetchone()[0])
    if s > 0:
        return s
    cur.execute(
        "SELECT COALESCE(SUM(valor_centavos), 0) FROM venda_pagamentos WHERE venda_id = ?",
        (int(venda_id),),
    )
    return int(cur.fetchone()[0])


def _esperado_liquidacao_centavos(cur: sqlite3.Cursor, venda_id: int) -> int:
    cur.execute(
        """
        SELECT total_final_centavos,
               COALESCE(credito_abatido_centavos, 0) AS cab
        FROM vendas WHERE id = ?
        """,
        (int(venda_id),),
    )
    row = cur.fetchone()
    if not row:
        return 0
    return max(0, int(row[0]) - int(row[1]))


def _table_exists(cur: sqlite3.Cursor, name: str) -> bool:
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ? LIMIT 1",
        (name,),
    )
    return cur.fetchone() is not None


def _drop_dw_tables(cur: sqlite3.Cursor) -> None:
    for t in DW_TABLES_DROP_ORDER:
        cur.execute(f"DROP TABLE IF EXISTS {t}")


def run_etl(conn: sqlite3.Connection) -> dict[str, int]:
    """
    Recria `dw_*` no alvo. Exige tabelas operacionais `agendamentos` e `vendas`
    (resto opcional). Retorna contagens por tabela fact/agregado.
    """
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = OFF")
    _drop_dw_tables(cur)

    cur.execute(
        """
        CREATE TABLE dw_fact_agendamento (
            agendamento_id INTEGER NOT NULL PRIMARY KEY,
            cliente_id INTEGER NOT NULL,
            servico_id INTEGER NOT NULL,
            venda_id INTEGER,
            venda_item_id INTEGER,
            data_agendamento TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fim TEXT NOT NULL,
            carga_horaria_h REAL,
            status TEXT NOT NULL,
            tipo_origem TEXT NOT NULL,
            modo_origem TEXT NOT NULL,
            preco_referencia_centavos INTEGER,
            is_cancelado INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE dw_fact_venda (
            venda_id INTEGER NOT NULL PRIMARY KEY,
            cliente_id INTEGER NOT NULL,
            data_registo TEXT,
            estado_pagamento TEXT NOT NULL,
            total_final_centavos INTEGER NOT NULL,
            credito_abatido_centavos INTEGER NOT NULL DEFAULT 0,
            esperado_liquidacao_centavos INTEGER NOT NULL,
            liquidado_centavos INTEGER NOT NULL,
            receita_ltv_real_centavos INTEGER NOT NULL,
            totalmente_liquidada INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE dw_cliente_kpi (
            cliente_id INTEGER NOT NULL PRIMARY KEY,
            visitas_todas_status INTEGER NOT NULL DEFAULT 0,
            visitas_nao_canceladas INTEGER NOT NULL DEFAULT 0,
            horas_carga_agendadas REAL,
            primeira_visita_data TEXT,
            ultima_visita_data TEXT,
            dias_primeira_ultima_visita INTEGER,
            media_dias_entre_visitas REAL,
            receita_ltv_real_total_centavos INTEGER NOT NULL DEFAULT 0,
            vendas_com_receita_ltv INTEGER NOT NULL DEFAULT 0,
            ticket_medio_ltv_real_centavos INTEGER
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE dw_etl_run (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            iniciado_em TEXT NOT NULL,
            concluido_em TEXT NOT NULL,
            versao_script TEXT NOT NULL,
            n_rows_fact_agendamento INTEGER NOT NULL,
            n_rows_fact_venda INTEGER NOT NULL,
            n_rows_cliente_kpi INTEGER NOT NULL
        )
        """
    )

    iniciado = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    n_ag = 0
    if _table_exists(cur, "agendamentos"):
        cur.execute(
            """
            SELECT id, cliente_id, servico_id, venda_id, venda_item_id,
                   data_agendamento, hora_inicio, hora_fim, status,
                   tipo_origem, modo_origem, preco_referencia_centavos
            FROM agendamentos
            """
        )
        for row in cur.fetchall():
            (
                ag_id,
                cid,
                sid,
                vid,
                viid,
                d_ag,
                hi,
                hf,
                st,
                tor,
                mor,
                pref,
            ) = row
            ch = carga_horaria_decimal(str(hi), str(hf))
            cancel = 1 if str(st) == "CANCELADO" else 0
            cur.execute(
                """
                INSERT INTO dw_fact_agendamento (
                    agendamento_id, cliente_id, servico_id, venda_id, venda_item_id,
                    data_agendamento, hora_inicio, hora_fim, carga_horaria_h,
                    status, tipo_origem, modo_origem, preco_referencia_centavos,
                    is_cancelado
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(ag_id),
                    int(cid),
                    int(sid),
                    int(vid) if vid is not None else None,
                    int(viid) if viid is not None else None,
                    str(d_ag),
                    str(hi),
                    str(hf),
                    ch,
                    str(st),
                    str(tor),
                    str(mor),
                    int(pref) if pref is not None else None,
                    cancel,
                ),
            )
            n_ag += 1

    n_v = 0
    if _table_exists(cur, "vendas"):
        cur.execute(
            """
            SELECT id, cliente_id, data_registo, estado_pagamento,
                   total_final_centavos,
                   COALESCE(credito_abatido_centavos, 0) AS cab
            FROM vendas
            """
        )
        for row in cur.fetchall():
            vid = int(row[0])
            esperado = _esperado_liquidacao_centavos(cur, vid)
            liq = _liquidado_venda_centavos(cur, vid)
            estado = str(row[3])
            if estado == "pendente":
                receita_ltv = 0
            else:
                receita_ltv = min(liq, esperado)
            totalmente = 1 if liq >= esperado and esperado > 0 else 0
            cur.execute(
                """
                INSERT INTO dw_fact_venda (
                    venda_id, cliente_id, data_registo, estado_pagamento,
                    total_final_centavos, credito_abatido_centavos,
                    esperado_liquidacao_centavos, liquidado_centavos,
                    receita_ltv_real_centavos, totalmente_liquidada
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    vid,
                    int(row[1]),
                    str(row[2]) if row[2] is not None else None,
                    estado,
                    int(row[4]),
                    int(row[5]),
                    esperado,
                    liq,
                    receita_ltv,
                    totalmente,
                ),
            )
            n_v += 1

    # --- Recorrência (âncora cliente_id): visitas não canceladas, ordenadas ---
    visitas_por_cliente: dict[int, list[tuple[str, str, int]]] = defaultdict(list)
    cur.execute(
        """
        SELECT cliente_id, data_agendamento, hora_inicio, agendamento_id
        FROM dw_fact_agendamento
        WHERE is_cancelado = 0
        ORDER BY cliente_id, data_agendamento, hora_inicio, agendamento_id
        """
    )
    for cid, d_ag, hi, ag_id in cur.fetchall():
        visitas_por_cliente[int(cid)].append((str(d_ag), str(hi), int(ag_id)))

    horas_por_cliente: dict[int, float] = defaultdict(float)
    cur.execute(
        """
        SELECT cliente_id, COALESCE(SUM(carga_horaria_h), 0)
        FROM dw_fact_agendamento
        WHERE is_cancelado = 0 AND carga_horaria_h IS NOT NULL
        GROUP BY cliente_id
        """
    )
    for cid, s in cur.fetchall():
        horas_por_cliente[int(cid)] = float(s)

    visitas_todas: dict[int, int] = defaultdict(int)
    cur.execute(
        "SELECT cliente_id, COUNT(*) FROM dw_fact_agendamento GROUP BY cliente_id"
    )
    for cid, c in cur.fetchall():
        visitas_todas[int(cid)] = int(c)

    ltv_por_cliente: dict[int, tuple[int, int]] = defaultdict(lambda: (0, 0))
    cur.execute(
        """
        SELECT cliente_id,
               COALESCE(SUM(receita_ltv_real_centavos), 0),
               SUM(CASE WHEN receita_ltv_real_centavos > 0 THEN 1 ELSE 0 END)
        FROM dw_fact_venda
        GROUP BY cliente_id
        """
    )
    for cid, total, nv in cur.fetchall():
        ltv_por_cliente[int(cid)] = (int(total), int(nv))

    all_clientes = set(visitas_todas.keys()) | set(visitas_por_cliente.keys()) | set(
        ltv_por_cliente.keys()
    )

    def _avg_gap_days(sorted_dates: list[date]) -> float | None:
        if len(sorted_dates) < 2:
            return None
        gaps: list[int] = []
        for i in range(1, len(sorted_dates)):
            gaps.append((sorted_dates[i] - sorted_dates[i - 1]).days)
        return round(sum(gaps) / len(gaps), 4)

    n_kpi = 0
    for cid in sorted(all_clientes):
        visits = visitas_por_cliente.get(cid, [])
        n_nc = len(visits)
        datas_ordenadas = []
        for d_s, _hi, _aid in visits:
            try:
                datas_ordenadas.append(datetime.strptime(d_s, "%Y-%m-%d").date())
            except ValueError:
                continue
        primeira = min(datas_ordenadas) if datas_ordenadas else None
        ultima = max(datas_ordenadas) if datas_ordenadas else None
        dias_pu = (
            (ultima - primeira).days if primeira and ultima and ultima >= primeira else None
        )
        media_gaps = _avg_gap_days(sorted(datas_ordenadas)) if datas_ordenadas else None

        rec_total, n_vendas_rec = ltv_por_cliente.get(cid, (0, 0))
        ticket = int(rec_total // n_vendas_rec) if n_vendas_rec > 0 else None

        cur.execute(
            """
            INSERT INTO dw_cliente_kpi (
                cliente_id,
                visitas_todas_status,
                visitas_nao_canceladas,
                horas_carga_agendadas,
                primeira_visita_data,
                ultima_visita_data,
                dias_primeira_ultima_visita,
                media_dias_entre_visitas,
                receita_ltv_real_total_centavos,
                vendas_com_receita_ltv,
                ticket_medio_ltv_real_centavos
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cid,
                visitas_todas.get(cid, 0),
                n_nc,
                round(horas_por_cliente.get(cid, 0.0), 4) if horas_por_cliente.get(cid) else None,
                primeira.isoformat() if primeira else None,
                ultima.isoformat() if ultima else None,
                dias_pu,
                media_gaps,
                rec_total,
                n_vendas_rec,
                ticket,
            ),
        )
        n_kpi += 1

    concluido = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cur.execute(
        """
        INSERT INTO dw_etl_run (
            iniciado_em, concluido_em, versao_script,
            n_rows_fact_agendamento, n_rows_fact_venda, n_rows_cliente_kpi
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (iniciado, concluido, __version__, n_ag, n_v, n_kpi),
    )

    cur.execute("PRAGMA foreign_keys = ON")
    conn.commit()

    return {
        "dw_fact_agendamento": n_ag,
        "dw_fact_venda": n_v,
        "dw_cliente_kpi": n_kpi,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="E19 — ETL tabelas dw_* (analytics)")
    p.add_argument(
        "--db",
        type=Path,
        default=Path("data/beaba_gestao.db"),
        help="Caminho para o SQLite (defeito: data/beaba_gestao.db)",
    )
    args = p.parse_args(argv)
    db_path: Path = args.db
    if not db_path.is_file():
        print(f"Base não encontrada: {db_path}", file=sys.stderr)
        return 1
    conn = sqlite3.connect(str(db_path))
    try:
        stats = run_etl(conn)
    except sqlite3.Error as e:
        print(f"ETL falhou: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    for k, v in stats.items():
        print(f"{k}: {v}")
    print("dw_etl_run: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
