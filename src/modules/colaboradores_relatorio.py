"""E24 — consultas agregação relatório «realização + repasse» (repasse_linhas × agendas elegíveis)."""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import date
from typing import Any, Literal, TypedDict

from src.modules.colaborador import MAPA_EQUI_ESP_SEM_LABEL
from src.modules.constants import STATUS_AGENDAMENTO_REPASSE_CONTABILIZADO

ModoDimensaoRepasse = Literal["especialidade", "servico", "colaborador"]

LABEL_TECNICO_TZ_PT = "Europe/Lisbon"

MODOS_REPASSE_LEGIVEL_PT: dict[ModoDimensaoRepasse, str] = {
    "especialidade": "Por especialidade",
    "servico": "Por serviço",
    "colaborador": "Por colaborador",
}


class LinhaRelatorioRepasse(TypedDict, total=False):
    repasse_linha_id: int
    agendamento_id: int
    colaborador_nome: str
    cliente_nome: str
    servico_id: int
    servico_nome: str
    especialidade_nome: str
    percentual_bp: int | None
    percentual_repr_pt: str
    valor_base_centavos: int
    valor_repasse_centavos: int
    repasse_linha_status: str
    estado_pago_label_pt: str
    quando_display_pt_lisboa: str
    data_agendamento: str
    hora_inicio: str


def validar_periodo_repasse_relatorio(data_ini: date | None, data_fim: date | None) -> tuple[bool, str]:
    if data_ini is None or data_fim is None:
        return False, "Indique período (data início e data fim)."
    if data_ini > data_fim:
        return False, "Data início deve ser menor ou igual à data fim."
    return True, ""


def validar_dimensao_e_seleccao_repasse_relatorio(
    modo: ModoDimensaoRepasse | str,
    *,
    especialidades: list[str] | None,
    servico_ids: list[int] | None,
    colaborador_ids: list[int] | None,
) -> tuple[bool, str]:
    m = str(modo).strip().lower()
    if m not in MODOS_REPASSE_LEGIVEL_PT:
        return False, "Modo de filtro inválido."
    if m == "especialidade":
        raw = [str(x).strip() for x in (especialidades or []) if str(x).strip()]
        if not raw:
            return False, "Seleccione pelo menos uma especialidade (filtro obrigatório)."
        return True, ""
    if m == "servico":
        ids = [int(x) for x in servico_ids or [] if int(x) > 0]
        if not ids:
            return False, "Seleccione pelo menos um serviço (filtro obrigatório)."
        return True, ""
    ids_c = [int(x) for x in colaborador_ids or [] if int(x) > 0]
    if not ids_c:
        return False, "Seleccione pelo menos um colaborador (filtro obrigatório)."
    return True, ""


def formato_percentual_bp(bp: object | None) -> str:
    if bp is None or int(bp) <= 0:
        return "—"
    x = int(bp) / 100.0
    return f"{str(x).replace('.', ',')} %"


def formato_euro_centavos_pt(centesimos: object | None) -> str:
    n = int(centesimos or 0)
    neg = n < 0
    ax = abs(n)
    s = f"{ax / 100.0:.2f}".replace(".", ",")
    return f"-{s} €" if neg else f"{s} €"


def _str_strip_or_empty(x: object) -> str:
    return str(x or "").strip()


def quando_linha_civil_etiqueta_lisboa(*, data_ymd: str, hora_inicio: str) -> str:
    """
    Etiqueta explícita `Europe/Lisbon`: enquanto a BD usar `data_agendamento` + `hora_*` civis sem offset,
    interpretação operacional coincide com uso diário Portugal; migrações futuras para UTC apenas ajustam
    esta função.
    """
    d = (data_ymd or "")[:10]
    hh_raw = _str_strip_or_empty(hora_inicio)
    if len(hh_raw) >= 5 and hh_raw[2] == ":":
        hh = hh_raw[:5]
    elif len(hh_raw) >= 2:
        hh = f"{hh_raw[:2]}:00"
    else:
        hh = "—"
    if len(d) == 10 and d[4] == "-" and d[7] == "-":
        return f"{d[8:10]}/{d[5:7]}/{d[0:4]} {hh} ({LABEL_TECNICO_TZ_PT})"
    return f"{d} {hh} ({LABEL_TECNICO_TZ_PT})"


def listar_especialidades_opcoes_relatorio(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute(
        """
        SELECT DISTINCT trim(COALESCE(e.nome, '')) AS n
        FROM servicos s
        LEFT JOIN especialidades e ON e.id = s.especialidade_id
        WHERE s.id IS NOT NULL
        """
    )
    bag: set[str] = set()
    for (r,) in cur.fetchall():
        t = str(r or "").strip()
        if t:
            bag.add(t)
        else:
            bag.add(MAPA_EQUI_ESP_SEM_LABEL)
    return sorted(bag, key=lambda x: x.lower())


def listar_servicos_opcoes_relatorio(conn: sqlite3.Connection) -> list[tuple[int, str]]:
    cur = conn.execute(
        """
        SELECT s.id, trim(COALESCE(s.nome, ''))
        FROM servicos s
        ORDER BY trim(COALESCE(s.nome, '')) COLLATE NOCASE
        """
    )
    return [(int(a), str(b)) for a, b in cur.fetchall()]


def listar_colaboradores_opcoes_relatorio(conn: sqlite3.Connection) -> list[tuple[int, str]]:
    cur = conn.execute(
        """
        SELECT id, nome FROM colaboradores ORDER BY nome COLLATE NOCASE
        """
    )
    return [(int(a), str(b)) for a, b in cur.fetchall()]


def _hydrate_rows(cur: sqlite3.Cursor, *, permitidos_status: tuple[str, ...]) -> list[LinhaRelatorioRepasse]:
    allow = {s.upper() for s in permitidos_status}
    out_rows: list[LinhaRelatorioRepasse] = []
    for r in cur.fetchall():
        rlid = int(r[0])
        ag_id = int(r[1])
        esp_db = _str_strip_or_empty(r[6])
        esp_label = esp_db if esp_db else MAPA_EQUI_ESP_SEM_LABEL
        bp = r[7]
        rp_st = _str_strip_or_empty(r[10]).upper()
        pag = rp_st == "REPASSE_PAGO"

        st_agenda = _str_strip_or_empty(r[13]).upper()
        if st_agenda not in allow:
            continue

        d_ag = str(r[11] or "")[:10]
        hi_raw = str(r[12] or "").strip()

        out_rows.append(
            {
                "repasse_linha_id": rlid,
                "agendamento_id": ag_id,
                "colaborador_nome": str(r[2] or ""),
                "cliente_nome": str(r[3] or ""),
                "servico_id": int(r[4]),
                "servico_nome": str(r[5] or ""),
                "especialidade_nome": esp_label,
                "percentual_bp": int(bp) if bp is not None else None,
                "percentual_repr_pt": formato_percentual_bp(bp),
                "valor_base_centavos": int(r[8] or 0),
                "valor_repasse_centavos": int(r[9] or 0),
                "repasse_linha_status": rp_st,
                "estado_pago_label_pt": "Pago" if pag else "Pendente",
                "quando_display_pt_lisboa": quando_linha_civil_etiqueta_lisboa(data_ymd=d_ag, hora_inicio=hi_raw),
                "data_agendamento": d_ag,
                "hora_inicio": hi_raw,
            }
        )
    return out_rows


def listar_linhas_relatorio_repasse_global(
    conn: sqlite3.Connection,
    *,
    data_ini: date,
    data_fim: date,
    modo: ModoDimensaoRepasse | str,
    especialidades_escolhidas: list[str] | None,
    servico_ids: list[int] | None,
    colaborador_ids: list[int] | None,
) -> list[LinhaRelatorioRepasse]:
    okp, mp = validar_periodo_repasse_relatorio(data_ini, data_fim)
    if not okp:
        raise ValueError(mp)
    oks, ms = validar_dimensao_e_seleccao_repasse_relatorio(
        modo,
        especialidades=especialidades_escolhidas,
        servico_ids=servico_ids,
        colaborador_ids=colaborador_ids,
    )
    if not oks:
        raise ValueError(ms)

    m = str(modo).strip().lower()
    st_list = STATUS_AGENDAMENTO_REPASSE_CONTABILIZADO
    sql = f"""
        SELECT
            rl.id,
            a.id,
            co.nome,
            cl.nome,
            s.id,
            s.nome,
            trim(COALESCE(e.nome, '')) AS esp_nome,
            rl.percentual_bp,
            rl.base_calculo_centavos,
            rl.valor_repasse_centavos,
            rl.status_repasse,
            a.data_agendamento,
            a.hora_inicio,
            a.status
        FROM repasse_linhas rl
        INNER JOIN agendamentos a ON a.id = rl.agendamento_id
        INNER JOIN colaboradores co ON co.id = rl.colaborador_id
        INNER JOIN clientes cl ON cl.id = a.cliente_id
        INNER JOIN servicos s ON s.id = a.servico_id
        LEFT JOIN especialidades e ON e.id = s.especialidade_id
        WHERE a.status IN ({",".join("?" * len(st_list))})
          AND date(a.data_agendamento) >= date(?)
          AND date(a.data_agendamento) <= date(?)
    """
    params: list[Any] = list(st_list) + [
        data_ini.strftime("%Y-%m-%d"),
        data_fim.strftime("%Y-%m-%d"),
    ]

    if m == "especialidade":
        esps_raw = [_str_strip_or_empty(x) for x in especialidades_escolhidas or []]
        chunks: list[str] = []
        if MAPA_EQUI_ESP_SEM_LABEL in esps_raw:
            chunks.append("(e.id IS NULL OR trim(IFNULL(e.nome, '')) = '')")
        rest = [e for e in esps_raw if e != MAPA_EQUI_ESP_SEM_LABEL]
        if rest:
            ph_e = ",".join("?" for _ in rest)
            chunks.append(f"trim(IFNULL(e.nome,'')) IN ({ph_e})")
            params.extend(rest)
        sql += " AND (" + " OR ".join(chunks) + ")"
    elif m == "servico":
        sids = sorted({int(x) for x in servico_ids or [] if int(x) > 0})
        sql += " AND a.servico_id IN (" + ",".join("?" for _ in sids) + ")"
        params.extend(sids)
    else:
        cids = sorted({int(x) for x in colaborador_ids or [] if int(x) > 0})
        sql += " AND rl.colaborador_id IN (" + ",".join("?" for _ in cids) + ")"
        params.extend(cids)

    sql += """
        ORDER BY
            date(a.data_agendamento) ASC,
            trim(IFNULL(a.hora_inicio, '')) ASC,
            trim(COALESCE(co.nome, '')) COLLATE NOCASE,
            trim(COALESCE(cl.nome, '')) COLLATE NOCASE,
            rl.id ASC
    """
    cur = conn.execute(sql, params)
    return _hydrate_rows(cur, permitidos_status=st_list)


def linhas_para_grid_pdf(rows: list[LinhaRelatorioRepasse]) -> list[list[str]]:
    hdr = [
        "Colaborador",
        "Quando",
        "Área / Especialidade",
        "Serviço",
        "Cliente",
        "Repasse pactuado (%)",
        "Valor atend.",
        "Repasse (EUR)",
        "Estado pgto.",
    ]
    body: list[list[str]] = []
    for row in rows:
        body.append(
            [
                str(row.get("colaborador_nome") or ""),
                str(row.get("quando_display_pt_lisboa") or ""),
                str(row.get("especialidade_nome") or ""),
                str(row.get("servico_nome") or ""),
                str(row.get("cliente_nome") or ""),
                str(row.get("percentual_repr_pt") or "—"),
                formato_euro_centavos_pt(row.get("valor_base_centavos")),
                formato_euro_centavos_pt(row.get("valor_repasse_centavos")),
                str(row.get("estado_pago_label_pt") or ""),
            ]
        )
    return [hdr, *body]


def agregar_metricas_repasse_linhas(rows: list[LinhaRelatorioRepasse]) -> dict[str, Any]:
    """Totais e quebras coherentes UI/PDF sobre a mesma lista materializada."""

    por_esp: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "n_linhas": 0,
            "base_cent": 0,
            "repasse_cent": 0,
            "repasse_pago_cent": 0,
            "repasse_pend_cent": 0,
        }
    )
    por_srv: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "n_linhas": 0,
            "base_cent": 0,
            "repasse_cent": 0,
            "repasse_pago_cent": 0,
            "repasse_pend_cent": 0,
        }
    )

    glob = {
        "n_linhas": len(rows),
        "base_cent": 0,
        "repasse_cent": 0,
        "repasse_pago_cent": 0,
        "repasse_pend_cent": 0,
    }

    for row in rows:
        base_c = int(row.get("valor_base_centavos") or 0)
        rep_c = int(row.get("valor_repasse_centavos") or 0)
        pag = str(row.get("estado_pago_label_pt") or "") == "Pago"
        esp_k = str(row.get("especialidade_nome") or MAPA_EQUI_ESP_SEM_LABEL)
        srv_label = str(row.get("servico_nome") or "").strip()
        srv_k = srv_label if srv_label else "(Serviço —)"

        glob["base_cent"] += base_c
        glob["repasse_cent"] += rep_c
        if pag:
            glob["repasse_pago_cent"] += rep_c
        else:
            glob["repasse_pend_cent"] += rep_c

        bucket_e = por_esp[esp_k]
        bucket_e["n_linhas"] += 1
        bucket_e["base_cent"] += base_c
        bucket_e["repasse_cent"] += rep_c
        if pag:
            bucket_e["repasse_pago_cent"] += rep_c
        else:
            bucket_e["repasse_pend_cent"] += rep_c

        bucket_s = por_srv[srv_k]
        bucket_s["n_linhas"] += 1
        bucket_s["base_cent"] += base_c
        bucket_s["repasse_cent"] += rep_c
        if pag:
            bucket_s["repasse_pago_cent"] += rep_c
        else:
            bucket_s["repasse_pend_cent"] += rep_c

    return {
        "global": glob,
        "por_especialidade": dict(sorted(por_esp.items(), key=lambda kv: kv[0].lower())),
        "por_servico": dict(sorted(por_srv.items(), key=lambda kv: kv[0].lower())),
    }
