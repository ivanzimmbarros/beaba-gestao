"""Consultas Financeiro — saldos de crédito de clientes (cancelamentos vs uso em vendas, E18)."""

from __future__ import annotations

import sqlite3
from collections import defaultdict, deque
from datetime import date, datetime

# Alinhado a `financeiro_repasses_colaboradores.REPASSE_ESP_SEM_LABEL`
SALDO_ESP_SEM_LABEL = "(Sem especialidade)"


def _iso_para_dd_mm_yyyy(iso: str | None) -> str:
    if not iso:
        return ""
    part = (iso or "").strip()[:10]
    if len(part) < 10 or part[4] != "-" or part[7] != "-":
        return ""
    return f"{part[8:10]}/{part[5:7]}/{part[0:4]}"


def _parse_date_iso10(s: object | None) -> date | None:
    raw = str(s or "").strip()[:10]
    if len(raw) != 10 or raw[4] != "-" or raw[7] != "-":
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


def _linha_referente_a_pacote_vendido(
    tipo_origem: object | None, pacote_sessao_id: object | None
) -> bool:
    """Crédito de cancelamento ligado a agendamento consumido de pacote vendido (linha `venda_itens` Pacote)."""
    if str(tipo_origem or "").strip().lower() == "pacote":
        return True
    try:
        return int(pacote_sessao_id or 0) > 0
    except (TypeError, ValueError):
        return False


def _data_cancelamento_ui(
    *,
    status_ag: str,
    data_alteracao_raw: object | None,
    criado_em_credito: object | None,
) -> date | None:
    st = str(status_ag or "").strip().upper()
    if st == "CANCELADO":
        d = _parse_date_iso10(data_alteracao_raw)
        if d is not None:
            return d
    return _parse_date_iso10(criado_em_credito)


def _sql_condicao_referente_a_pacote_sim() -> str:
    """Equivalente a «Referente a Pacote?» = Sim na listagem de saldos."""
    return (
        "("
        "LOWER(TRIM(a.tipo_origem)) = 'pacote' "
        "OR (a.pacote_sessao_id IS NOT NULL AND CAST(a.pacote_sessao_id AS INTEGER) > 0)"
        ")"
    )


def _split_naturezas_filtro_pacote_vs_resto(
    naturezas: list[str],
) -> tuple[bool, list[str]]:
    """Separa «Pack» (ancora em referente-a-pacote) das demais naturezas (via serviço prestado)."""
    from src.modules.constants import NATUREZA_PACK, canon_natureza_catalogo

    fn = [str(x).strip() for x in naturezas if str(x).strip()]
    wants_pac = any(canon_natureza_catalogo(x) == NATUREZA_PACK for x in fn)
    outras = [x for x in fn if canon_natureza_catalogo(x) != NATUREZA_PACK]
    return wants_pac, outras


def _split_servico_ids_sessao_vs_pacote(
    conn: sqlite3.Connection, servico_ids: list[int]
) -> tuple[list[int], list[int]]:
    """Classifica IDs do filtro «Nome do serviço»: Pacote vs restantes (sessão, etc.)."""
    ids = sorted({int(x) for x in servico_ids if int(x) > 0})
    if not ids:
        return [], []
    ph = ",".join("?" * len(ids))
    cur = conn.execute(
        f"SELECT id, TRIM(natureza) FROM servicos WHERE id IN ({ph})",
        ids,
    )
    sess: list[int] = []
    pkg: list[int] = []
    for sid, nat in cur.fetchall():
        if str(nat or "").strip() in ("Pack", "Pacote"):
            pkg.append(int(sid))
        else:
            sess.append(int(sid))
    return sess, pkg


def listar_clientes_com_saldo_credito_positivo(conn: sqlite3.Connection) -> list[tuple[int, str]]:
    cur = conn.execute(
        """
        SELECT c.id, c.nome
        FROM clientes c
        INNER JOIN vw_cliente_saldo_credito v ON v.cliente_id = c.id
        WHERE COALESCE(v.saldo_credito_centavos, 0) > 0
        ORDER BY c.nome COLLATE NOCASE
        """
    )
    return [(int(a), str(b or "")) for a, b in cur.fetchall()]


def _fifo_restante_por_movimento_credito_cancelamento(
    conn: sqlite3.Connection,
    *,
    cliente_ids: list[int] | None,
) -> dict[int, int]:
    """
    Por cliente, aplica débitos `USO_VENDA` (e outros movimentos negativos) aos créditos
    `CREDITO_CANCELAMENTO` por ordem cronológica (FIFO). Devolve mapa movimento_id -> centavos restantes.
    """
    params: list[int] = []
    wh = ""
    if cliente_ids:
        wh = " AND cliente_id IN (" + ",".join("?" * len(cliente_ids)) + ")"
        params.extend(int(x) for x in cliente_ids)
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT id, cliente_id, tipo_movimento, valor_centavos
        FROM credito_movimentos
        WHERE 1=1 {wh}
        ORDER BY datetime(criado_em), id
        """,
        params,
    )
    rows = cur.fetchall()
    remaining: dict[int, int] = {}
    fila: dict[int, deque[int]] = defaultdict(deque)
    for mid, cid, tipo, val in rows:
        tipo_s = str(tipo or "")
        v = int(val or 0)
        cid_i = int(cid)
        mid_i = int(mid)
        if tipo_s == "CREDITO_CANCELAMENTO" and v > 0:
            remaining[mid_i] = v
            fila[cid_i].append(mid_i)
        elif v < 0 and tipo_s in ("USO_VENDA", "USO_AGENDAMENTO"):
            need = -v
            q = fila[cid_i]
            while need > 0 and q:
                cmid = q[0]
                r = int(remaining.get(cmid, 0))
                if r <= 0:
                    q.popleft()
                    continue
                take = min(r, need)
                remaining[cmid] = r - take
                need -= take
                if int(remaining[cmid]) <= 0:
                    q.popleft()
    return remaining


def listar_linhas_gestao_saldos_clientes_ativos(
    conn: sqlite3.Connection,
    *,
    cliente_ids: list[int] | None = None,
    naturezas: list[str] | None = None,
    servico_ids: list[int] | None = None,
    mes: int | None = None,
    ano: int | None = None,
) -> list[dict[str, object]]:
    """
    Linhas de saldo «activo» por cancelamento (crédito E18), após consumo FIFO por `USO_VENDA`.
    `servico_ids`: ``None`` = sem filtro por serviço; ``[]`` = zero linhas; lista = restringe.
    IDs de natureza **Pacote** filtram pela linha de venda do pacote (`vi_pkg.servico_id`), alinhado
    à coluna «Nome do Pacote»; demais naturezas filtram por `agendamentos.servico_id` (sessão prestada).
    Filtro **Natureza = Pacote** usa a mesma regra que «Referente a Pacote?» = Sim (não `servicos.natureza`
    do agendamento, que na prática é a sessão cancelada).
    """
    rest = _fifo_restante_por_movimento_credito_cancelamento(
        conn, cliente_ids=cliente_ids
    )
    ids_pos = [mid for mid, cent in rest.items() if int(cent) > 0]
    if not ids_pos:
        return []
    ph = ",".join("?" * len(ids_pos))
    fn = [str(x).strip() for x in (naturezas or []) if str(x).strip()]
    ft_in = servico_ids
    ft = [int(x) for x in ft_in] if ft_in is not None else []

    sql = f"""
        SELECT
            cm.id,
            cl.nome,
            s.natureza,
            COALESCE(NULLIF(TRIM(e.nome), ''), '') AS esp_nome,
            s.nome AS servico_nome,
            a.data_criacao_registo,
            a.data_alteracao,
            a.status,
            cm.criado_em,
            cm.valor_centavos,
            a.tipo_origem,
            a.pacote_sessao_id,
            COALESCE(
                NULLIF(TRIM(vi_pkg.nome_snapshot), ''),
                NULLIF(TRIM(spkg.nome), ''),
                ''
            ) AS nome_pacote_adquirido
        FROM credito_movimentos cm
        INNER JOIN agendamentos a ON a.id = cm.referencia_id
        INNER JOIN clientes cl ON cl.id = cm.cliente_id
        INNER JOIN servicos s ON s.id = a.servico_id
        LEFT JOIN especialidades e ON e.id = s.especialidade_id
        LEFT JOIN venda_itens vi_pkg ON vi_pkg.id = a.venda_item_id
        LEFT JOIN servicos spkg
          ON spkg.id = vi_pkg.servico_id AND TRIM(spkg.natureza) IN ('Pack', 'Pacote')
        WHERE cm.tipo_movimento = 'CREDITO_CANCELAMENTO'
          AND cm.id IN ({ph})
    """
    params2: list = list(ids_pos)
    if fn:
        wants_pac, outras_nat = _split_naturezas_filtro_pacote_vs_resto(fn)
        parts_nat: list[str] = []
        if wants_pac:
            parts_nat.append(_sql_condicao_referente_a_pacote_sim())
        if outras_nat:
            parts_nat.append(
                "trim(s.natureza) IN (" + ",".join("?" for _ in outras_nat) + ")"
            )
            params2.extend(outras_nat)
        if len(parts_nat) > 1:
            sql += " AND (" + " OR ".join(parts_nat) + ")"
        elif len(parts_nat) == 1:
            sql += " AND " + parts_nat[0]
    if ft_in is not None:
        if not ft:
            sql += " AND 1=0"
        else:
            sess_ids, pkg_ids = _split_servico_ids_sessao_vs_pacote(conn, ft)
            parts: list[str] = []
            if sess_ids:
                parts.append(
                    "a.servico_id IN (" + ",".join("?" for _ in sess_ids) + ")"
                )
                params2.extend(sess_ids)
            if pkg_ids:
                parts.append(
                    "("
                    "LOWER(TRIM(a.tipo_origem)) = 'pacote' "
                    "AND vi_pkg.servico_id IN (" + ",".join("?" for _ in pkg_ids) + ")"
                    ")"
                )
                params2.extend(pkg_ids)
            if parts:
                sql += " AND (" + " OR ".join(parts) + ")"
            else:
                sql += " AND 1=0"

    cur = conn.execute(sql, params2)
    out: list[dict[str, object]] = []
    for (
        mid,
        nome_cli,
        nat,
        esp_nome,
        srv,
        dcria,
        dalt,
        st_ag,
        cemi,
        cred_orig,
        tipo_origem_row,
        pacote_sessao_row,
        nome_pacote_adquirido,
    ) in cur.fetchall():
        mid_i = int(mid)
        rem = int(rest.get(mid_i, 0))
        if rem <= 0:
            continue
        d_can = _data_cancelamento_ui(
            status_ag=str(st_ag or ""),
            data_alteracao_raw=dalt,
            criado_em_credito=cemi,
        )
        d_can_iso = d_can.isoformat() if d_can else ""
        if mes is not None and 1 <= int(mes) <= 12 and d_can is not None:
            if int(d_can.month) != int(mes):
                continue
        if ano is not None and d_can is not None:
            if int(d_can.year) != int(ano):
                continue
        if ano is not None and d_can is None:
            continue
        if mes is not None and d_can is None:
            continue

        esp_lbl = str(esp_nome or "").strip() or SALDO_ESP_SEM_LABEL
        ref_pac = _linha_referente_a_pacote_vendido(tipo_origem_row, pacote_sessao_row)
        nome_pacote_ui = (
            str(nome_pacote_adquirido or "").strip() if ref_pac else ""
        )
        out.append(
            {
                "credito_movimento_id": mid_i,
                "cliente_nome": str(nome_cli or ""),
                "natureza_servico": str(nat or ""),
                "especialidade": esp_lbl,
                "nome_servico": str(srv or ""),
                "referente_a_pacote": "Sim" if ref_pac else "Não",
                "nome_pacote": nome_pacote_ui,
                "saldo_restante_centavos": rem,
                "data_aquisicao_iso": str(dcria or "").strip()[:10],
                "data_aquisicao_dm": _iso_para_dd_mm_yyyy(str(dcria or "")),
                "data_cancelamento_iso": d_can_iso,
                "data_cancelamento_dm": _iso_para_dd_mm_yyyy(d_can_iso) if d_can_iso else "",
                "d_cancel_date": d_can,
            }
        )
    out.sort(
        key=lambda r: (
            str(r.get("data_cancelamento_iso") or ""),
            int(r.get("credito_movimento_id") or 0),
        ),
        reverse=True,
    )
    return out


def totais_saldos_ativos_por_antiguidade_cancelamento(
    linhas: list[dict[str, object]],
) -> tuple[int, int, int]:
    """
    (total_centavos, ate_15_dias_centavos, mais_15_dias_centavos).
    «Até 15 dias»: cancelamento há 0–14 dias (15 dias corridos incluindo hoje).
    «Mais de 15 dias»: há ≥15 dias.
    """
    tot = 0
    r15 = 0
    o15 = 0
    hoje = date.today()
    for r in linhas:
        c = int(r.get("saldo_restante_centavos") or 0)
        if c <= 0:
            continue
        tot += c
        d = r.get("d_cancel_date")
        if not isinstance(d, date):
            o15 += c
            continue
        dias = (hoje - d).days
        if dias <= 14:
            r15 += c
        else:
            o15 += c
    return tot, r15, o15


def listar_vendas_com_consumo_credito_loja(
    conn: sqlite3.Connection,
    *,
    cliente_ids: list[int] | None = None,
    naturezas: list[str] | None = None,
    servico_ids: list[int] | None = None,
    mes: int | None = None,
    ano: int | None = None,
) -> list[dict[str, object]]:
    """
    Vendas onde houve abatimento de crédito (`credito_abatido_centavos` > 0), alinhado ao ledger `USO_VENDA`.
    Filtros aplicam-se ao 1.º artigo da venda (serviço) e à data de registo da venda.
    """
    fn = [str(x).strip() for x in (naturezas or []) if str(x).strip()]
    ft_in = servico_ids
    ft = [int(x) for x in ft_in] if ft_in is not None else []

    sql = """
        SELECT
            v.id AS venda_id,
            c.nome AS cliente_nome,
            date(v.data_registo) AS data_venda_iso,
            v.total_final_centavos,
            v.credito_abatido_centavos,
            s.natureza,
            COALESCE(NULLIF(TRIM(e.nome), ''), '') AS esp_nome,
            s.nome AS servico_nome
        FROM credito_movimentos cm
        INNER JOIN vendas v ON v.id = cm.referencia_id
        INNER JOIN clientes c ON c.id = cm.cliente_id
        INNER JOIN venda_itens vi ON vi.venda_id = v.id AND vi.ordem = (
            SELECT MIN(ordem) FROM venda_itens WHERE venda_id = v.id
        )
        INNER JOIN servicos s ON s.id = vi.servico_id
        LEFT JOIN especialidades e ON e.id = s.especialidade_id
        WHERE cm.tipo_movimento = 'USO_VENDA'
          AND COALESCE(v.credito_abatido_centavos, 0) > 0
    """
    params: list = []
    if cliente_ids:
        sql += " AND cm.cliente_id IN (" + ",".join("?" * len(cliente_ids)) + ")"
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
    sql += " ORDER BY datetime(v.data_registo) DESC, v.id DESC"

    cur = conn.execute(sql, params)
    seen: set[int] = set()
    out: list[dict[str, object]] = []
    for row in cur.fetchall():
        vid = int(row[0])
        if vid in seen:
            continue
        seen.add(vid)
        tot = int(row[3] or 0)
        cab = int(row[4] or 0)
        esp_lbl = str(row[6] or "").strip() or SALDO_ESP_SEM_LABEL
        out.append(
            {
                "venda_id": vid,
                "cliente_nome": str(row[1] or ""),
                "data_venda_iso": str(row[2] or "")[:10],
                "data_venda_dm": _iso_para_dd_mm_yyyy(str(row[2] or "")),
                "natureza_servico": str(row[5] or ""),
                "especialidade": esp_lbl,
                "nome_servico": str(row[7] or ""),
                "valor_original_sem_saldo_centavos": tot,
                "valor_saldo_utilizado_centavos": cab,
                "valor_final_com_saldo_abatido_centavos": max(0, tot - cab),
            }
        )
    return out


__all__ = [
    "SALDO_ESP_SEM_LABEL",
    "listar_clientes_com_saldo_credito_positivo",
    "listar_linhas_gestao_saldos_clientes_ativos",
    "listar_vendas_com_consumo_credito_loja",
    "totais_saldos_ativos_por_antiguidade_cancelamento",
]
