"""Ledger append-only de crédito de loja (E18) e totais liquidados por venda."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from src.database.connection import get_connection


def total_liquidado_venda_centavos(cur: sqlite3.Cursor, venda_id: int) -> int:
    """Soma linhas E18; se vazio, legado `venda_pagamentos`."""
    vid = int(venda_id)
    cur.execute(
        "SELECT COALESCE(SUM(valor_centavos), 0) FROM venda_pagamento_linhas WHERE venda_id = ?",
        (vid,),
    )
    s = int(cur.fetchone()[0])
    if s > 0:
        return s
    cur.execute(
        "SELECT COALESCE(SUM(valor_centavos), 0) FROM venda_pagamentos WHERE venda_id = ?",
        (vid,),
    )
    return int(cur.fetchone()[0])


def total_esperado_liquidacao_venda_centavos(cur: sqlite3.Cursor, venda_id: int) -> int:
    cur.execute(
        """
        SELECT total_final_centavos, COALESCE(credito_abatido_centavos, 0)
        FROM vendas WHERE id = ?
        """,
        (int(venda_id),),
    )
    row = cur.fetchone()
    if not row:
        return 0
    return max(0, int(row[0]) - int(row[1]))


def venda_totalmente_liquidada(cur: sqlite3.Cursor, venda_id: int) -> bool:
    return total_liquidado_venda_centavos(cur, venda_id) >= total_esperado_liquidacao_venda_centavos(
        cur, venda_id
    )


def listar_pagamento_linhas_venda(venda_id: int) -> list[dict[str, Any]]:
    """
    Recebimentos já registados na venda, por ordem cronológica.

    Usa `venda_pagamento_linhas` (E18). Se ainda não existir linha E18, recua para
    `venda_pagamentos` legado, usando `date(data_registo)` da venda como data aproximada.
    """
    vid = int(venda_id)
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, valor_centavos, criado_em
            FROM venda_pagamento_linhas
            WHERE venda_id = ?
            ORDER BY datetime(criado_em), id
            """,
            (vid,),
        )
        rows = cur.fetchall()
        if rows:
            return [
                {
                    "id": int(r[0]),
                    "valor_centavos": int(r[1]),
                    "criado_em": str(r[2] or ""),
                }
                for r in rows
            ]
        cur.execute("SELECT date(data_registo) FROM vendas WHERE id = ?", (vid,))
        r0 = cur.fetchone()
        d0 = str(r0[0] or "")[:10] if r0 else ""
        cur.execute(
            """
            SELECT id, valor_centavos
            FROM venda_pagamentos
            WHERE venda_id = ? AND valor_centavos > 0
            ORDER BY ordem ASC, id ASC
            """,
            (vid,),
        )
        out: list[dict[str, Any]] = []
        for r in cur.fetchall():
            em = f"{d0} 12:00:00" if len(d0) == 10 else ""
            out.append(
                {
                    "id": int(r[0]),
                    "valor_centavos": int(r[1]),
                    "criado_em": em,
                }
            )
        return out
    finally:
        conn.close()


def obter_data_ultimo_pagamento_venda_dd_mm_yyyy(venda_id: int) -> str:
    """Data (dd-mm-aaaa) do último registo em `listar_pagamento_linhas_venda`, ou string vazia."""
    lines = listar_pagamento_linhas_venda(int(venda_id))
    if not lines:
        return ""
    last = max(
        lines,
        key=lambda ln: (str(ln.get("criado_em") or ""), int(ln.get("id") or 0)),
    )
    raw = str(last.get("criado_em") or "").strip()[:10]
    if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        try:
            d = datetime.strptime(raw, "%Y-%m-%d").date()
            return f"{d.day:02d}-{d.month:02d}-{d.year:04d}"
        except ValueError:
            pass
    return raw


def obter_aberto_liquidacao_venda_centavos(venda_id: int) -> int:
    """Valor ainda por liquidar na venda (total esperado − já pago), em centavos."""
    conn = get_connection()
    if not conn:
        return 0
    try:
        cur = conn.cursor()
        esp = total_esperado_liquidacao_venda_centavos(cur, int(venda_id))
        liq = total_liquidado_venda_centavos(cur, int(venda_id))
        return max(0, esp - liq)
    finally:
        conn.close()


def saldo_credito_cliente_centavos(cur: sqlite3.Cursor, cliente_id: int) -> int:
    cur.execute(
        "SELECT COALESCE(saldo_credito_centavos, 0) FROM vw_cliente_saldo_credito WHERE cliente_id = ?",
        (int(cliente_id),),
    )
    row = cur.fetchone()
    return int(row[0]) if row else 0


def registrar_uso_credito_em_venda(
    cur: sqlite3.Cursor,
    *,
    cliente_id: int,
    venda_id: int,
    valor_abatido_centavos: int,
    actor: str | None = None,
) -> None:
    """Débito no ledger; idempotente por (venda, USO_VENDA)."""
    if valor_abatido_centavos <= 0:
        return
    cur.execute(
        """
        INSERT OR IGNORE INTO credito_movimentos (
            cliente_id, tipo_movimento, valor_centavos,
            referencia_tipo, referencia_id, observacoes, actor
        ) VALUES (?, 'USO_VENDA', ?, 'venda', ?, ?, ?)
        """,
        (
            int(cliente_id),
            -int(valor_abatido_centavos),
            int(venda_id),
            "Abatimento na venda",
            actor,
        ),
    )


def registrar_credito_por_cancelamento_agendamento(
    cur: sqlite3.Cursor,
    *,
    cliente_id: int,
    agendamento_id: int,
    valor_centavos: int,
    actor: str | None = None,
    observacoes: str | None = None,
) -> bool:
    """Crédito positivo; idempotente por (agendamento, CREDITO_CANCELAMENTO). Retorna True se inseriu."""
    if valor_centavos <= 0:
        return False
    cur.execute(
        """
        INSERT OR IGNORE INTO credito_movimentos (
            cliente_id, tipo_movimento, valor_centavos,
            referencia_tipo, referencia_id, observacoes, actor
        ) VALUES (?, 'CREDITO_CANCELAMENTO', ?, 'agendamento', ?, ?, ?)
        """,
        (
            int(cliente_id),
            int(valor_centavos),
            int(agendamento_id),
            observacoes or "Crédito por cancelamento",
            actor,
        ),
    )
    return cur.rowcount > 0


def meio_legacy_para_tipo_linha(meio: str) -> str:
    m = str(meio).strip()
    if m in ("dinheiro", "mbway"):
        return "DINHEIRO_MBWAY"
    if m == "cartao_credito":
        return "CARTAO_CREDITO"
    if m == "iban":
        return "IBAN"
    return "DINHEIRO_MBWAY"


def obter_saldo_credito_cliente(cliente_id: int) -> int:
    conn = get_connection()
    if not conn:
        return 0
    try:
        cur = conn.cursor()
        return saldo_credito_cliente_centavos(cur, int(cliente_id))
    finally:
        conn.close()


__all__ = [
    "listar_pagamento_linhas_venda",
    "meio_legacy_para_tipo_linha",
    "obter_data_ultimo_pagamento_venda_dd_mm_yyyy",
    "obter_saldo_credito_cliente",
    "registrar_credito_por_cancelamento_agendamento",
    "registrar_uso_credito_em_venda",
    "saldo_credito_cliente_centavos",
    "total_esperado_liquidacao_venda_centavos",
    "total_liquidado_venda_centavos",
    "obter_aberto_liquidacao_venda_centavos",
    "venda_totalmente_liquidada",
]
