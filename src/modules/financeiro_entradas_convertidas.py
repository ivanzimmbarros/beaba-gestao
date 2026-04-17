"""Financeiro — entradas convertidas (linhas de venda) para gestão de valores."""

from __future__ import annotations

import sqlite3

from src.modules.financeiro_saldos_clientes import (
    SALDO_ESP_SEM_LABEL,
    _iso_para_dd_mm_yyyy,
)


_MEIOS_VALOR_RECEBIDO: tuple[str, ...] = ("DINHEIRO_MBWAY", "IBAN", "CARTAO_CREDITO")


def _sum_valor_recebido_efectivo_venda_centavos(
    cur: sqlite3.Cursor, venda_id: int, *, cache: dict[int, int]
) -> int:
    """
    Soma já recebida em dinheiro / transferência / cartão (inclui cartão parcelado).

    Usa `venda_pagamento_linhas` quando existir qualquer linha para a venda; caso contrário
    recua para `venda_pagamentos` (legado, todos os meios são monetários). Exclui
    `CREDITO_LOJA` (abatimento de saldo, não entrada de tesouraria).
    """
    vid = int(venda_id)
    if vid in cache:
        return int(cache[vid])
    cur.execute(
        "SELECT COUNT(*) FROM venda_pagamento_linhas WHERE venda_id = ?",
        (vid,),
    )
    n_any = int(cur.fetchone()[0] or 0)
    if n_any > 0:
        ph = ",".join("?" * len(_MEIOS_VALOR_RECEBIDO))
        cur.execute(
            f"""
            SELECT COALESCE(SUM(valor_centavos), 0)
            FROM venda_pagamento_linhas
            WHERE venda_id = ? AND tipo_meio IN ({ph})
            """,
            (vid, *_MEIOS_VALOR_RECEBIDO),
        )
        s = int(cur.fetchone()[0] or 0)
        cache[vid] = s
        return s
    cur.execute(
        """
        SELECT COALESCE(SUM(valor_centavos), 0)
        FROM venda_pagamentos
        WHERE venda_id = ? AND valor_centavos > 0
        """,
        (vid,),
    )
    s2 = int(cur.fetchone()[0] or 0)
    cache[vid] = s2
    return s2


def _aloca_proporcional_centavos(total: int, weights: list[int]) -> list[int]:
    """Distribui `total` (>=0) proporcionalmente a `weights` (>=0); soma == total."""
    n = len(weights)
    if n == 0:
        return []
    t = max(0, int(total))
    ws = [max(0, int(w)) for w in weights]
    s = sum(ws)
    if s <= 0 or t == 0:
        return [0] * n
    out: list[int] = []
    acc = 0
    for i in range(n - 1):
        x = (t * ws[i]) // s
        out.append(int(x))
        acc += int(x)
    out.append(int(t - acc))
    return out


def fmt_estado_pagamento_ui(est: str) -> str:
    k = str(est or "").strip().lower()
    return {
        "integral": "Integral",
        "pendente": "Pendente",
        "parcial": "Parcial",
        "parcelado": "Parcelado",
    }.get(k, str(est or "").strip() or "—")


def listar_clientes_com_venda_para_filtro_entradas(
    conn: sqlite3.Connection,
) -> list[tuple[int, str]]:
    cur = conn.execute(
        """
        SELECT DISTINCT c.id, c.nome
        FROM vendas v
        INNER JOIN clientes c ON c.id = v.cliente_id
        ORDER BY c.nome COLLATE NOCASE
        """
    )
    return [(int(a), str(b or "")) for a, b in cur.fetchall()]


def listar_linhas_gestao_entradas_convertidas_vendas(
    conn: sqlite3.Connection,
    *,
    cliente_ids: list[int] | None = None,
    naturezas: list[str] | None = None,
    servico_ids: list[int] | None = None,
    mes: int | None = None,
    ano: int | None = None,
    estados_pagamento: list[str] | None = None,
) -> list[dict[str, object]]:
    """
    Uma linha por `venda_itens` (pacote = uma linha na venda, não explode componentes).
    Alocações de desconto global e crédito de loja proporcionais a `total_linha_centavos`.

    Inclui `total_valor_recebido_centavos`: em **integral**, coincide com o valor final da linha;
    noutros estados, reparte a soma já recebida em dinheiro / IBAN / MBWay / cartão
    (`venda_pagamento_linhas`, excluindo `CREDITO_LOJA`) proporcionalmente ao valor final
    de cada linha; sem linhas E18, usa `venda_pagamentos` (legado).
    """
    fn = [str(x).strip() for x in (naturezas or []) if str(x).strip()]
    ft_in = servico_ids
    ft = [int(x) for x in ft_in] if ft_in is not None else []
    fe = [str(x).strip().lower() for x in (estados_pagamento or []) if str(x).strip()]

    sql = """
        SELECT
            vi.id AS venda_item_id,
            v.id AS venda_id,
            c.nome AS cliente_nome,
            date(v.data_registo) AS data_registo_iso,
            v.estado_pagamento,
            v.subtotal_apos_descontos_linha_centavos,
            v.desconto_global_centavos_aplicado,
            COALESCE(v.credito_abatido_centavos, 0) AS credito_abatido_centavos,
            v.total_final_centavos,
            vi.ordem,
            vi.servico_id,
            vi.colaborador_id,
            vi.subtotal_bruto_centavos,
            vi.desconto_linha_centavos,
            vi.total_linha_centavos,
            TRIM(IFNULL(s.natureza, '')) AS natureza_servico,
            COALESCE(NULLIF(TRIM(e.nome), ''), '') AS esp_nome,
            vi.nome_snapshot,
            s.nome AS nome_servico_catalogo
        FROM venda_itens vi
        INNER JOIN vendas v ON v.id = vi.venda_id
        INNER JOIN clientes c ON c.id = v.cliente_id
        INNER JOIN servicos s ON s.id = vi.servico_id
        LEFT JOIN especialidades e ON e.id = s.especialidade_id
        WHERE 1=1
    """
    params: list = []
    if cliente_ids:
        sql += " AND v.cliente_id IN (" + ",".join("?" * len(cliente_ids)) + ")"
        params.extend(int(x) for x in cliente_ids)
    if fn:
        sql += " AND trim(s.natureza) IN (" + ",".join("?" for _ in fn) + ")"
        params.extend(fn)
    if ft_in is not None:
        if not ft:
            sql += " AND 1=0"
        else:
            sql += " AND vi.servico_id IN (" + ",".join("?" for _ in ft) + ")"
            params.extend(ft)
    if mes is not None and 1 <= int(mes) <= 12:
        sql += " AND CAST(strftime('%m', v.data_registo) AS INTEGER) = ?"
        params.append(int(mes))
    if ano is not None:
        sql += " AND CAST(strftime('%Y', v.data_registo) AS INTEGER) = ?"
        params.append(int(ano))
    if fe:
        sql += " AND lower(trim(v.estado_pagamento)) IN (" + ",".join("?" for _ in fe) + ")"
        params.extend(fe)

    sql += " ORDER BY datetime(v.data_registo) DESC, v.id DESC, vi.ordem ASC"

    cur = conn.execute(sql, params)
    raw_rows = [
        {
            "venda_item_id": int(r[0]),
            "venda_id": int(r[1]),
            "cliente_nome": str(r[2] or ""),
            "data_registo_iso": str(r[3] or "")[:10],
            "estado_pagamento": str(r[4] or ""),
            "subtotal_apos_descontos_linha_centavos": int(r[5] or 0),
            "desconto_global_centavos_aplicado": int(r[6] or 0),
            "credito_abatido_centavos": int(r[7] or 0),
            "total_final_centavos": int(r[8] or 0),
            "ordem": int(r[9] or 0),
            "servico_id": int(r[10] or 0),
            "colaborador_id": int(r[11]) if r[11] is not None else None,
            "subtotal_bruto_centavos": int(r[12] or 0),
            "desconto_linha_centavos": int(r[13] or 0),
            "total_linha_centavos": int(r[14] or 0),
            "natureza_servico": str(r[15] or ""),
            "esp_nome": str(r[16] or ""),
            "nome_snapshot": str(r[17] or ""),
            "nome_servico_catalogo": str(r[18] or ""),
        }
        for r in cur.fetchall()
    ]

    groups: list[list[dict[str, object]]] = []
    cur_vid: int | None = None
    for row in raw_rows:
        vid = int(row["venda_id"])
        if cur_vid != vid:
            groups.append([])
            cur_vid = vid
        groups[-1].append(row)

    pct_cache: dict[tuple[int, int], int] = {}

    def _percent_repasse(sid: int, cid: int | None) -> int:
        if cid is None or cid < 1:
            return 0
        k = (int(sid), int(cid))
        if k in pct_cache:
            return pct_cache[k]
        cur2 = conn.execute(
            """
            SELECT COALESCE(percentual_centesimos, 0)
            FROM colaborador_servicos
            WHERE servico_id = ? AND colaborador_id = ?
            """,
            (int(sid), int(cid)),
        )
        rowp = cur2.fetchone()
        bp = int(rowp[0] or 0) if rowp else 0
        pct_cache[k] = bp
        return bp

    cur = conn.cursor()
    _recv_v_cache: dict[int, int] = {}
    out: list[dict[str, object]] = []
    for items in groups:
        items.sort(key=lambda r: int(r["ordem"] or 0))
        w = [int(r["total_linha_centavos"] or 0) for r in items]
        gtot = int(items[0]["desconto_global_centavos_aplicado"] or 0)
        cab = int(items[0]["credito_abatido_centavos"] or 0)
        glob_al = _aloca_proporcional_centavos(gtot, w)
        cab_al = _aloca_proporcional_centavos(cab, w)
        buf: list[dict[str, object]] = []
        vfins: list[int] = []
        for i, r in enumerate(items):
            bruto = int(r["subtotal_bruto_centavos"] or 0)
            dlin = int(r["desconto_linha_centavos"] or 0)
            tlin = int(r["total_linha_centavos"] or 0)
            ga = int(glob_al[i]) if i < len(glob_al) else 0
            ca = int(cab_al[i]) if i < len(cab_al) else 0
            desc_total = dlin + ga
            vfin = max(0, tlin - ga - ca)
            pct_desc = 0.0
            if bruto > 0:
                pct_desc = round(100.0 * float(desc_total) / float(bruto), 2)
            sid = int(r["servico_id"] or 0)
            cob = r.get("colaborador_id")
            cob_i = int(cob) if cob is not None else None
            bp = _percent_repasse(sid, cob_i)
            repasse = int(vfin * bp / 10000) if vfin > 0 and bp > 0 else 0
            resultado = max(0, vfin - repasse)
            nome_tab = str(r["nome_snapshot"] or "").strip() or str(
                r["nome_servico_catalogo"] or ""
            ).strip()
            esp_lbl = str(r["esp_nome"] or "").strip() or SALDO_ESP_SEM_LABEL
            dreg = str(r["data_registo_iso"] or "").strip()[:10]
            vfins.append(vfin)
            buf.append(
                {
                    "venda_id": int(r["venda_id"]),
                    "venda_item_id": int(r["venda_item_id"]),
                    "cliente_nome": str(r["cliente_nome"] or ""),
                    "natureza_servico": str(r["natureza_servico"] or ""),
                    "especialidade": esp_lbl,
                    "nome_servico": nome_tab,
                    "valor_bruto_centavos": bruto,
                    "descontos_centavos": desc_total,
                    "pct_descontos": pct_desc,
                    "saldo_aplicado_centavos": ca,
                    "valor_final_venda_centavos": vfin,
                    "repasse_colaborador_centavos": repasse,
                    "resultado_final_apurado_centavos": resultado,
                    "estado_pagamento": str(r["estado_pagamento"] or ""),
                    "estado_pagamento_ui": fmt_estado_pagamento_ui(
                        str(r["estado_pagamento"] or "")
                    ),
                    "data_registo_iso": dreg,
                    "data_registo_dm": _iso_para_dd_mm_yyyy(dreg),
                }
            )
        est_l = str(items[0]["estado_pagamento"] or "").strip().lower()
        vid_g = int(items[0]["venda_id"])
        sum_eff = _sum_valor_recebido_efectivo_venda_centavos(cur, vid_g, cache=_recv_v_cache)
        if est_l == "integral":
            recv_alloc = [int(x) for x in vfins]
        else:
            recv_alloc = _aloca_proporcional_centavos(sum_eff, vfins)
        for j, rowd in enumerate(buf):
            rowd["total_valor_recebido_centavos"] = (
                int(recv_alloc[j]) if j < len(recv_alloc) else 0
            )
            out.append(rowd)

    return out


__all__ = [
    "fmt_estado_pagamento_ui",
    "listar_clientes_com_venda_para_filtro_entradas",
    "listar_linhas_gestao_entradas_convertidas_vendas",
]
