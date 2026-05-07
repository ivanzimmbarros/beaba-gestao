"""Disponibilidade operacional dos colaboradores — planos, regras e calendário mestre."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from typing import Any

from src.database.connection import get_connection
from src.modules.agendamento import listar_agendamentos

_DIAS_PT = ("Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom")

# Agendamentos com slot «ocupado» no mapa da disponibilidade (exclui cancelados / encerrados).
_STATUS_AG_VISIVEL_CALENDARIO_DISP = (
    "PRE_AGENDADO",
    "AGENDADO",
    "CONFIRMADO",
    "REALIZADO_PENDENTE_PGTO",
)


def _parse_iso_date(s: str | None) -> date | None:
    if not s or not str(s).strip():
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def _ranges_overlap(a0: date, a1: date, b0: date, b1: date) -> bool:
    return a0 <= b1 and b0 <= a1


def dias_ate_fim_validade(*, hoje: date, valido_ate: date) -> int:
    """Dias completos até `valido_ate` (inclusive como último dia do plano)."""
    return (valido_ate - hoje).days


def niveis_alerta_validade(*, hoje: date, valido_ate: date) -> tuple[int, ...]:
    """Devolve subconjunto de (15, 10, 5) quando o fim está exactamente a N dias."""
    d = dias_ate_fim_validade(hoje=hoje, valido_ate=valido_ate)
    hits: list[int] = []
    for n in (15, 10, 5):
        if d == n:
            hits.append(n)
    return tuple(hits)


def iter_datas_intervalo(d0: date, d1: date) -> list[date]:
    out: list[date] = []
    cur = d0
    while cur <= d1:
        out.append(cur)
        cur += timedelta(days=1)
    return out


def _weekday_mon0(d: date) -> int:
    return int(d.weekday())


def _parse_dias_mascara(raw: str | None) -> set[int] | None:
    if raw is None or str(raw).strip() == "":
        return None
    parts = [p.strip() for p in str(raw).split(",") if p.strip() != ""]
    if not parts:
        return None
    return {int(p) for p in parts}


def expandir_slots_plano(
    *,
    valido_de: date,
    valido_ate: date,
    regras: list[dict[str, Any]],
) -> dict[str, list[tuple[str, str, str]]]:
    """
    Devolve mapa data_iso -> lista de (hora_inicio, hora_fim, tipo_regra).
    Corta intersecção com [valido_de, valido_ate]; funde intervalos sobrepostos por dia.
    """
    raw: dict[str, list[tuple[str, str]]] = {}
    for d in iter_datas_intervalo(valido_de, valido_ate):
        ds = d.isoformat()
        wd = _weekday_mon0(d)
        slots: list[tuple[str, str]] = []
        for r in regras:
            tipo = str(r.get("tipo") or "")
            hi = str(r.get("hora_inicio") or "").strip()
            hf = str(r.get("hora_fim") or "").strip()
            if not hi or not hf:
                continue
            if tipo == "semanal":
                if int(r.get("dia_semana") if r.get("dia_semana") is not None else -99) == wd:
                    slots.append((hi, hf))
            elif tipo == "excecao_dia":
                ex = str(r.get("data_especifica") or "")[:10]
                if ex == ds:
                    slots.append((hi, hf))
            elif tipo == "custom_intervalo":
                i0 = _parse_iso_date(str(r.get("intervalo_de") or ""))
                i1 = _parse_iso_date(str(r.get("intervalo_ate") or ""))
                if not i0 or not i1 or d < i0 or d > i1:
                    continue
                mask = _parse_dias_mascara(r.get("dias_mascara"))  # type: ignore[arg-type]
                if mask is not None and wd not in mask:
                    continue
                slots.append((hi, hf))
        if slots:
            merged = _fundir_intervalos_hhmm(slots)
            raw[ds] = merged
    out: dict[str, list[tuple[str, str, str]]] = {}
    for ds, pairs in raw.items():
        out[ds] = [(a, b, "slot") for a, b in pairs]
    return out


def _fundir_intervalos_hhmm(slots: list[tuple[str, str]]) -> list[tuple[str, str]]:
    def key_t(t: str) -> tuple[int, int]:
        h, m = t.split(":", 1)
        return int(h), int(m)

    items = sorted(slots, key=lambda x: (key_t(x[0]), key_t(x[1])))
    if not items:
        return []
    out: list[tuple[str, str]] = []
    cs, ce = items[0]
    for s, e in items[1:]:
        if key_t(s) <= key_t(ce):
            if key_t(e) > key_t(ce):
                ce = e
        else:
            out.append((cs, ce))
            cs, ce = s, e
    out.append((cs, ce))
    return out


def obter_rascunho_aberto(colaborador_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    if not conn:
        return None
    try:
        row = conn.execute(
            """
            SELECT id, colaborador_id, valido_de, valido_ate, estado, confirmado_em, criado_em
            FROM colaborador_disponibilidade_plano
            WHERE colaborador_id = ? AND estado = 'rascunho'
            ORDER BY id DESC LIMIT 1
            """,
            (int(colaborador_id),),
        ).fetchone()
        if not row:
            return None
        return {
            "id": int(row[0]),
            "colaborador_id": int(row[1]),
            "valido_de": str(row[2]),
            "valido_ate": str(row[3]),
            "estado": str(row[4]),
            "confirmado_em": row[5],
            "criado_em": str(row[6]),
        }
    finally:
        conn.close()


def obter_planos_confirmados_para_calendario(
    *,
    data_de: str,
    data_ate: str,
    colaborador_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    """Planos confirmados que intersectam o intervalo de visualização."""
    conn = get_connection()
    if not conn:
        return []
    try:
        q = """
            SELECT p.id, p.colaborador_id, c.nome, p.valido_de, p.valido_ate
            FROM colaborador_disponibilidade_plano p
            JOIN colaboradores c ON c.id = p.colaborador_id
            WHERE p.estado = 'confirmado'
              AND p.valido_de <= ? AND p.valido_ate >= ?
        """
        args: list[Any] = [data_ate, data_de]
        if colaborador_ids:
            q += f" AND p.colaborador_id IN ({','.join('?' * len(colaborador_ids))})"
            args.extend(int(x) for x in colaborador_ids)
        rows = conn.execute(q, args).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            pid = int(r[0])
            regras = listar_regras_plano(pid, conn=conn)
            esp = _especialidades_colaborador(conn, int(r[1]))
            out.append(
                {
                    "plano_id": pid,
                    "colaborador_id": int(r[1]),
                    "colaborador_nome": str(r[2]),
                    "valido_de": str(r[3])[:10],
                    "valido_ate": str(r[4])[:10],
                    "regras": regras,
                    "especialidades_txt": esp,
                }
            )
        return out
    finally:
        conn.close()


def _especialidades_colaborador(conn: sqlite3.Connection, colaborador_id: int) -> str:
    rows = conn.execute(
        """
        SELECT DISTINCT COALESCE(e.nome, '') AS en
        FROM colaborador_servicos cs
        JOIN servicos s ON s.id = cs.servico_id
        LEFT JOIN especialidades e ON e.id = s.especialidade_id
        WHERE cs.colaborador_id = ?
        ORDER BY en
        """,
        (int(colaborador_id),),
    ).fetchall()
    parts = sorted({str(x[0]).strip() for x in rows if str(x[0]).strip()})
    return ", ".join(parts) if parts else "—"


def listar_regras_plano(plano_id: int, *, conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    own = conn is None
    c = get_connection() if own else conn
    if not c:
        return []
    try:
        cur = c.execute(
            """
            SELECT id, tipo, dia_semana, data_especifica, intervalo_de, intervalo_ate,
                   dias_mascara, hora_inicio, hora_fim, ordem
            FROM colaborador_disponibilidade_regra
            WHERE plano_id = ?
            ORDER BY ordem ASC, id ASC
            """,
            (int(plano_id),),
        )
        out: list[dict[str, Any]] = []
        for row in cur.fetchall():
            out.append(
                {
                    "id": int(row[0]),
                    "tipo": str(row[1]),
                    "dia_semana": row[2],
                    "data_especifica": row[3],
                    "intervalo_de": row[4],
                    "intervalo_ate": row[5],
                    "dias_mascara": row[6],
                    "hora_inicio": str(row[7]),
                    "hora_fim": str(row[8]),
                    "ordem": int(row[9]),
                }
            )
        return out
    finally:
        if own and c:
            c.close()


def criar_ou_atualizar_rascunho(
    colaborador_id: int,
    *,
    valido_de: str,
    valido_ate: str,
) -> tuple[bool, str, int | None]:
    vd = _parse_iso_date(valido_de)
    va = _parse_iso_date(valido_ate)
    if not vd or not va:
        return False, "Datas de validade inválidas.", None
    if va < vd:
        return False, "«Válido até» deve ser ≥ «Válido de».", None
    conn = get_connection()
    if not conn:
        return False, "Sem ligação à base de dados.", None
    try:
        ex = conn.execute(
            """
            SELECT id FROM colaborador_disponibilidade_plano
            WHERE colaborador_id = ? AND estado = 'rascunho'
            ORDER BY id DESC LIMIT 1
            """,
            (int(colaborador_id),),
        ).fetchone()
        if ex:
            pid = int(ex[0])
            conn.execute(
                """
                UPDATE colaborador_disponibilidade_plano
                SET valido_de = ?, valido_ate = ?
                WHERE id = ?
                """,
                (vd.isoformat(), va.isoformat(), pid),
            )
            conn.commit()
            return True, "Rascunho actualizado.", pid
        cur = conn.execute(
            """
            INSERT INTO colaborador_disponibilidade_plano (
                colaborador_id, valido_de, valido_ate, estado
            ) VALUES (?, ?, ?, 'rascunho')
            """,
            (int(colaborador_id), vd.isoformat(), va.isoformat()),
        )
        conn.commit()
        return True, "Rascunho criado.", int(cur.lastrowid)
    except sqlite3.IntegrityError as e:
        return False, str(e), None
    finally:
        conn.close()


def adicionar_regra(
    plano_id: int,
    *,
    tipo: str,
    hora_inicio: str,
    hora_fim: str,
    dia_semana: int | None = None,
    data_especifica: str | None = None,
    intervalo_de: str | None = None,
    intervalo_ate: str | None = None,
    dias_mascara: str | None = None,
) -> tuple[bool, str]:
    if tipo not in ("semanal", "excecao_dia", "custom_intervalo"):
        return False, "Tipo de regra inválido."
    conn = get_connection()
    if not conn:
        return False, "Sem ligação à base de dados."
    try:
        st = conn.execute(
            "SELECT estado FROM colaborador_disponibilidade_plano WHERE id = ?",
            (int(plano_id),),
        ).fetchone()
        if not st or str(st[0]) != "rascunho":
            return False, "Só é possível editar regras em planos **rascunho**."
        mx = conn.execute(
            "SELECT COALESCE(MAX(ordem), -1) FROM colaborador_disponibilidade_regra WHERE plano_id = ?",
            (int(plano_id),),
        ).fetchone()
        ordem = int(mx[0]) + 1 if mx else 0
        conn.execute(
            """
            INSERT INTO colaborador_disponibilidade_regra (
                plano_id, tipo, dia_semana, data_especifica, intervalo_de, intervalo_ate,
                dias_mascara, hora_inicio, hora_fim, ordem
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(plano_id),
                tipo,
                dia_semana,
                data_especifica,
                intervalo_de,
                intervalo_ate,
                dias_mascara,
                hora_inicio.strip(),
                hora_fim.strip(),
                ordem,
            ),
        )
        conn.commit()
        return True, "Regra adicionada."
    finally:
        conn.close()


def remover_regra(regra_id: int) -> tuple[bool, str]:
    conn = get_connection()
    if not conn:
        return False, "Sem ligação à base de dados."
    try:
        row = conn.execute(
            """
            SELECT r.id, p.estado
            FROM colaborador_disponibilidade_regra r
            JOIN colaborador_disponibilidade_plano p ON p.id = r.plano_id
            WHERE r.id = ?
            """,
            (int(regra_id),),
        ).fetchone()
        if not row:
            return False, "Regra não encontrada."
        if str(row[1]) != "rascunho":
            return False, "Só pode remover regras de rascunhos."
        conn.execute("DELETE FROM colaborador_disponibilidade_regra WHERE id = ?", (int(regra_id),))
        conn.commit()
        return True, "Regra removida."
    finally:
        conn.close()


def confirmar_plano_publicado(plano_id: int) -> tuple[bool, str]:
    """Confirma o plano; arquiva outros confirmados sobrepostos no mesmo colaborador."""
    conn = get_connection()
    if not conn:
        return False, "Sem ligação à base de dados."
    try:
        row = conn.execute(
            """
            SELECT colaborador_id, valido_de, valido_ate, estado
            FROM colaborador_disponibilidade_plano WHERE id = ?
            """,
            (int(plano_id),),
        ).fetchone()
        if not row:
            return False, "Plano não encontrado."
        if str(row[3]) != "rascunho":
            return False, "Este plano já não é rascunho."
        cid = int(row[0])
        vd = _parse_iso_date(str(row[1]))  # type: ignore[arg-type]
        va = _parse_iso_date(str(row[2]))  # type: ignore[arg-type]
        if not vd or not va:
            return False, "Datas inválidas no plano."
        others = conn.execute(
            """
            SELECT id, valido_de, valido_ate FROM colaborador_disponibilidade_plano
            WHERE colaborador_id = ? AND estado = 'confirmado' AND id != ?
            """,
            (cid, int(plano_id)),
        ).fetchall()
        for oid, ovd, ova in others:
            od0 = _parse_iso_date(str(ovd))
            od1 = _parse_iso_date(str(ova))
            if od0 and od1 and _ranges_overlap(vd, va, od0, od1):
                conn.execute(
                    "UPDATE colaborador_disponibilidade_plano SET estado = 'arquivado' WHERE id = ?",
                    (int(oid),),
                )
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            """
            UPDATE colaborador_disponibilidade_plano
            SET estado = 'confirmado', confirmado_em = ?
            WHERE id = ?
            """,
            (now, int(plano_id)),
        )
        conn.commit()
        return True, "Plano confirmado e publicado no calendário mestre. Planos confirmados sobrepostos foram arquivados."
    finally:
        conn.close()


def listar_alertas_confirmados(colaborador_id: int | None, *, hoje: date | None = None) -> list[dict[str, Any]]:
    """Alertas 15/10/5 dias antes do fim da validade (planos confirmados)."""
    h = hoje or date.today()
    conn = get_connection()
    if not conn:
        return []
    try:
        q = """
            SELECT p.id, p.colaborador_id, c.nome, p.valido_ate
            FROM colaborador_disponibilidade_plano p
            JOIN colaboradores c ON c.id = p.colaborador_id
            WHERE p.estado = 'confirmado'
        """
        args: list[Any] = []
        if colaborador_id is not None:
            q += " AND p.colaborador_id = ?"
            args.append(int(colaborador_id))
        rows = conn.execute(q, args).fetchall()
        out: list[dict[str, Any]] = []
        for pid, cid, nome, vate in rows:
            va = _parse_iso_date(str(vate))
            if not va:
                continue
            for n in niveis_alerta_validade(hoje=h, valido_ate=va):
                out.append(
                    {
                        "plano_id": int(pid),
                        "colaborador_id": int(cid),
                        "colaborador_nome": str(nome),
                        "dias": n,
                        "valido_ate": va.isoformat(),
                    }
                )
        return out
    finally:
        conn.close()


def agregar_slots_calendario_mestre(
    *,
    data_de: str,
    data_ate: str,
    colaborador_ids: list[int] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """
    Por data ISO: lista de blocos com horários de disponibilidade (plano confirmado) e de agendamentos activos.

    Cada entrada inclui ``bloco``: ``\"disponibilidade\"`` | ``\"agendamento\"``. Agendamentos trazem
    ``cliente_nome`` e ``servico_nome`` para destaque visual no calendário.
    """
    d0 = _parse_iso_date(data_de)
    d1 = _parse_iso_date(data_ate)
    if not d0 or not d1:
        return {}
    planos = obter_planos_confirmados_para_calendario(
        data_de=data_de, data_ate=data_ate, colaborador_ids=colaborador_ids
    )
    by_day: dict[str, list[dict[str, Any]]] = {}
    for p in planos:
        vd = _parse_iso_date(p["valido_de"])
        va = _parse_iso_date(p["valido_ate"])
        if not vd or not va:
            continue
        r0 = max(vd, d0)
        r1 = min(va, d1)
        if r1 < r0:
            continue
        slots = expandir_slots_plano(valido_de=vd, valido_ate=va, regras=p["regras"])
        cid = int(p["colaborador_id"])
        cor_idx = abs(cid) % 5
        for ds, triples in slots.items():
            if ds < r0.isoformat() or ds > r1.isoformat():
                continue
            for hi, hf, _ in triples:
                by_day.setdefault(ds, []).append(
                    {
                        "colaborador_id": cid,
                        "nome": p["colaborador_nome"],
                        "hora_inicio": hi,
                        "hora_fim": hf,
                        "especialidades_txt": p["especialidades_txt"],
                        "cor_idx": cor_idx,
                        "bloco": "disponibilidade",
                    }
                )

    cols_pos: set[int] | None = None
    ag_cids_arg: list[int] | None = None
    if colaborador_ids is not None:
        cols_pos = {int(x) for x in colaborador_ids if int(x) > 0}
        ag_cids_arg = sorted(cols_pos) if cols_pos else [-1]

    if ag_cids_arg != [-1]:
        ag_rows = listar_agendamentos(
            data_de=str(data_de)[:10],
            data_ate=str(data_ate)[:10],
            colaborador_ids=ag_cids_arg if ag_cids_arg is not None else None,
            status_list=list(_STATUS_AG_VISIVEL_CALENDARIO_DISP),
        )
        cfilter = cols_pos if colaborador_ids is not None else None
        for ag in ag_rows:
            ds = str(ag.get("data_agendamento") or "")[:10]
            if len(ds) < 10:
                continue
            hi = str(ag.get("hora_inicio") or "").strip()
            hf = str(ag.get("hora_fim") or "").strip()
            if not hi or not hf:
                continue
            cids_ag: list[int] = list(ag.get("colaborador_ids") or [])
            nomes_ag: list[str] = list(ag.get("colaboradores_nomes") or [])
            cliente_nm = str(ag.get("cliente_nome") or "").strip()
            srv_nm = str(ag.get("servico_nome") or "").strip()
            for j, cid_raw in enumerate(cids_ag):
                cid = int(cid_raw)
                if cfilter is not None and cid not in cfilter:
                    continue
                nome_col = nomes_ag[j].strip() if j < len(nomes_ag) and nomes_ag[j] else "—"
                cor_idx = abs(cid) % 5
                by_day.setdefault(ds, []).append(
                    {
                        "colaborador_id": cid,
                        "nome": nome_col,
                        "hora_inicio": hi,
                        "hora_fim": hf,
                        "especialidades_txt": srv_nm or "—",
                        "cor_idx": cor_idx,
                        "bloco": "agendamento",
                        "cliente_nome": cliente_nm,
                        "servico_nome": srv_nm,
                    }
                )

    for ds in by_day:
        by_day[ds].sort(
            key=lambda x: (
                0 if str(x.get("bloco")) == "agendamento" else 1,
                str(x["hora_inicio"]),
                str(x["nome"]).lower(),
            )
        )
    return by_day


def exportar_estado_planos_json(colaborador_id: int | None = None) -> str:
    """Útil para testes e auditoria leve."""
    conn = get_connection()
    if not conn:
        return "[]"
    try:
        q = "SELECT id, colaborador_id, valido_de, valido_ate, estado, confirmado_em FROM colaborador_disponibilidade_plano"
        args: list[Any] = []
        if colaborador_id is not None:
            q += " WHERE colaborador_id = ?"
            args.append(int(colaborador_id))
        rows = conn.execute(q, args).fetchall()
        data = [
            {
                "id": int(r[0]),
                "colaborador_id": int(r[1]),
                "valido_de": str(r[2])[:10],
                "valido_ate": str(r[3])[:10],
                "estado": str(r[4]),
                "confirmado_em": r[5],
            }
            for r in rows
        ]
        return json.dumps(data, ensure_ascii=False)
    finally:
        conn.close()
