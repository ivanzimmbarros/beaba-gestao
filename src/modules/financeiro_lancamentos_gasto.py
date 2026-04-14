"""Lançamentos de gastos operacionais (Real / Meta) ligados à hierarquia CC → Natureza → Tipo."""

from __future__ import annotations

import calendar
import re
import sqlite3
from datetime import date, datetime


def parse_valor_euro(text: str) -> int | None:
    """Converte texto (ex.: «12,50» ou «12.50 €») para centavos; None se inválido ou vazio."""
    t = (text or "").replace("€", "").replace("EUR", "").strip().replace(" ", "")
    if not t:
        return None
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".")
    try:
        v = float(t)
    except ValueError:
        return None
    if v < 0:
        return None
    return int(round(v * 100))


def parse_data_dd_mm_yyyy(text: str) -> str | None:
    """«dd/mm/aaaa» → «yyyy-mm-dd» ISO; None se inválido."""
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", (text or "").strip())
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        datetime(y, mo, d)
    except ValueError:
        return None
    return f"{y:04d}-{mo:02d}-{d:02d}"


def _iso_date_para_dm(iso: str | None) -> str:
    """yyyy-mm-dd ou prefixo yyyy-mm-dd → dd/mm/aaaa."""
    if not iso:
        return ""
    part = (iso or "").strip()[:10]
    if len(part) < 10 or part[4] != "-" or part[7] != "-":
        return str(iso).strip()
    y, m, d = part[0:4], part[5:7], part[8:10]
    return f"{d}/{m}/{y}"


def iso_para_dd_mm_yyyy(iso: str | None) -> str:
    """yyyy-mm-dd → dd/mm/aaaa (API pública para UI)."""
    s = _iso_date_para_dm(iso)
    if s and len(s) == 10 and s[2] == "/" and s[5] == "/":
        return s
    return ""


def _iso_datetime_para_dm_hm(iso: str | None) -> str:
    """yyyy-mm-dd HH:MM:SS ou data → dd/mm/aaaa HH:MM (se houver hora)."""
    if not iso:
        return ""
    s = (iso or "").strip()
    if len(s) >= 19 and s[10] == " ":
        return f"{s[8:10]}/{s[5:7]}/{s[0:4]} {s[11:16]}"
    return _iso_date_para_dm(s)


def _centavos_para_euro_txt(cent: int) -> str:
    v = int(cent) / 100.0
    s = f"{v:.2f}".replace(".", ",")
    return f"{s} €"


def _add_months_iso(iso: str, add_m: int) -> str:
    y, m, d = (int(x) for x in iso.split("-"))
    idx = (y * 12 + (m - 1)) + add_m
    ny, nm0 = divmod(idx, 12)
    nm = nm0 + 1
    last = calendar.monthrange(ny, nm)[1]
    nd = min(d, last)
    return f"{ny:04d}-{nm:02d}-{nd:02d}"


def tipos_gasto_coerentes_com_seleccao(
    conn: sqlite3.Connection,
    *,
    centro_ids: list[int],
    natureza_ids: list[int],
    tipo_ids: list[int],
) -> list[int]:
    """
    Tipos de gasto activos cuja hierarquia cai simultaneamente nas três listas.
    Listas vazias em qualquer dimensão produzem resultado vazio.
    """
    if not centro_ids or not natureza_ids or not tipo_ids:
        return []
    ph_cc = ",".join("?" for _ in centro_ids)
    ph_nat = ",".join("?" for _ in natureza_ids)
    ph_tip = ",".join("?" for _ in tipo_ids)
    cur = conn.execute(
        f"""
        SELECT t.id
        FROM financeiro_tipo_gasto t
        INNER JOIN financeiro_natureza n ON n.id = t.natureza_id AND n.ativo = 1
        INNER JOIN financeiro_centro_custo c ON c.id = n.centro_custo_id AND c.ativo = 1
        WHERE t.ativo = 1
          AND c.id IN ({ph_cc})
          AND n.id IN ({ph_nat})
          AND t.id IN ({ph_tip})
        ORDER BY c.nome COLLATE NOCASE, n.nome COLLATE NOCASE, t.nome COLLATE NOCASE
        """,
        [int(x) for x in centro_ids]
        + [int(x) for x in natureza_ids]
        + [int(x) for x in tipo_ids],
    )
    return [int(r[0]) for r in cur.fetchall()]


def listar_lancamentos_controle(
    conn: sqlite3.Connection,
    *,
    filtro_centro_ids: list[int] | None = None,
    filtro_natureza_ids: list[int] | None = None,
    filtro_tipo_ids: list[int] | None = None,
) -> list[dict]:
    """Linhas para a tabela «Controle de Lançamentos» (filtros opcionais por CC / natureza / tipo)."""
    fc = [int(x) for x in (filtro_centro_ids or [])]
    fn = [int(x) for x in (filtro_natureza_ids or [])]
    ft = [int(x) for x in (filtro_tipo_ids or [])]
    sql = """
        SELECT
            g.id,
            c.id,
            n.id,
            t.id,
            c.nome,
            n.nome,
            t.nome,
            g.valor_centavos,
            g.classe_lancamento,
            g.status_lancamento,
            g.data_competencia,
            g.data_pagamento,
            COALESCE(NULLIF(g.data_criacao_registo, ''), g.data_registo) AS criacao,
            g.replica_para_outros_meses,
            g.numero_meses_planeados
        FROM financeiro_gasto_lancamentos g
        INNER JOIN financeiro_tipo_gasto t ON t.id = g.tipo_gasto_id
        INNER JOIN financeiro_natureza n ON n.id = t.natureza_id AND n.ativo = 1
        INNER JOIN financeiro_centro_custo c ON c.id = n.centro_custo_id AND c.ativo = 1
        WHERE 1 = 1
    """
    params: list = []
    if fc:
        sql += " AND c.id IN (" + ",".join("?" for _ in fc) + ")"
        params.extend(fc)
    if fn:
        sql += " AND n.id IN (" + ",".join("?" for _ in fn) + ")"
        params.extend(fn)
    if ft:
        sql += " AND t.id IN (" + ",".join("?" for _ in ft) + ")"
        params.extend(ft)
    sql += " ORDER BY g.id DESC"
    cur = conn.execute(sql, params)
    out: list[dict] = []
    for r in cur.fetchall():
        cl = str(r[8] or "").strip().lower()
        tipo_reg = "Meta" if cl == "meta" else "Real"
        st_raw = str(r[9] or "")
        dcomp = str(r[10] or "").strip()[:10] if r[10] else ""
        dp = r[11]
        cr = r[12]
        rep = int(r[13] or 0)
        nmes = int(r[14] or 1)
        out.append(
            {
                "lancamento_id": int(r[0]),
                "centro_custo_id": int(r[1]),
                "natureza_id": int(r[2]),
                "tipo_id": int(r[3]),
                "centro": str(r[4]),
                "natureza": str(r[5]),
                "tipo": str(r[6]),
                "valor": _centavos_para_euro_txt(int(r[7] or 0)),
                "valor_centavos": int(r[7] or 0),
                "tipo_registo": tipo_reg,
                "status": "Pago" if st_raw.lower().startswith("pago") else "Agendado",
                "data_pagamento": _iso_date_para_dm(str(dp) if dp else ""),
                "data_criacao": _iso_datetime_para_dm_hm(str(cr) if cr else ""),
                "data_competencia_iso": dcomp,
                "replica_flag": rep,
                "n_meses": nmes,
            }
        )
    return out


def inserir_lancamentos_operacionais(
    conn: sqlite3.Connection,
    tipo_ids: list[int],
    *,
    valor_centavos: int,
    data_competencia_iso: str,
    status_lancamento: str,
    classe_lancamento: str,
    replicar: bool,
    meses_duracao: int,
    observacao: str = "",
) -> tuple[int, str]:
    """
    Insere um registo por (tipo, mês de competência).
    `meses_duracao` ∈ [1,24]; se `replicar` é falso, usa-se apenas o primeiro mês.
    """
    if not tipo_ids:
        return 0, "Seleccione pelo menos um tipo de gasto coerente com centro e natureza."
    if valor_centavos < 0:
        return 0, "Valor inválido."
    st_raw = (status_lancamento or "").strip().lower()
    if st_raw.startswith("pago"):
        status_db = "pago"
    elif st_raw.startswith("agend"):
        status_db = "agendado"
    else:
        status_db = ""
    if status_db not in ("pago", "agendado"):
        return 0, "Indique o status: Pago ou Agendado."
    cl = (classe_lancamento or "").strip().lower()
    if cl not in ("real", "meta"):
        return 0, "Tipo de registo inválido."
    try:
        date.fromisoformat(data_competencia_iso)
    except ValueError:
        return 0, "Data de competência inválida."

    n_m = max(1, min(24, int(meses_duracao)))
    if not replicar:
        n_m = 1

    obs = (observacao or "").strip()
    criacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    n_ins = 0
    for tid in tipo_ids:
        for off in range(n_m):
            dcomp = _add_months_iso(data_competencia_iso, off)
            d_pag = dcomp
            conn.execute(
                """
                INSERT INTO financeiro_gasto_lancamentos (
                    tipo_gasto_id,
                    observacao,
                    valor_centavos,
                    data_registo,
                    classe_lancamento,
                    data_competencia,
                    status_lancamento,
                    replica_para_outros_meses,
                    numero_meses_planeados,
                    data_pagamento,
                    data_criacao_registo
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(tid),
                    obs,
                    int(valor_centavos),
                    criacao,
                    cl,
                    dcomp,
                    status_db,
                    1 if replicar else 0,
                    n_m,
                    d_pag,
                    criacao,
                ),
            )
            n_ins += 1
    return n_ins, ""
