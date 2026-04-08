"""Ledger append-only de crédito de loja (E18) e totais liquidados por venda."""

from __future__ import annotations

import sqlite3
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
    "meio_legacy_para_tipo_linha",
    "obter_saldo_credito_cliente",
    "registrar_credito_por_cancelamento_agendamento",
    "registrar_uso_credito_em_venda",
    "saldo_credito_cliente_centavos",
    "total_esperado_liquidacao_venda_centavos",
    "total_liquidado_venda_centavos",
    "venda_totalmente_liquidada",
]
