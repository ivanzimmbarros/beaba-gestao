"""Agendamentos — ocorrências na agenda, buffer de créditos (venda) e máquina de estados (E09)."""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Literal

from src.database.connection import get_connection
from src.modules.credito_ledger import (
    registrar_credito_por_cancelamento_agendamento,
    total_esperado_liquidacao_venda_centavos,
    total_liquidado_venda_centavos,
)

StatusAgendamento = Literal[
    "PRE_AGENDADO",
    "AGENDADO",
    "CONFIRMADO",
    "REALIZADO_PENDENTE_PGTO",
    "CONCLUIDO",
    "CANCELADO",
]
TipoOrigem = Literal["sessao_avulsa", "pacote", "coworking", "evento"]

_HHMM = re.compile(r"^\d{1,2}:\d{2}$")


def _norm_hhmm(s: str) -> str:
    t = (s or "").strip()
    if not _HHMM.match(t):
        raise ValueError("hora inválida (use HH:MM)")
    h, m = t.split(":")
    return f"{int(h):02d}:{int(m):02d}"


def minutos_desde_meia_noite(hhmm: str) -> int:
    hhmm = _norm_hhmm(hhmm)
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def validar_intervalo_horario(hora_inicio: str, hora_fim: str) -> tuple[bool, str]:
    try:
        a = minutos_desde_meia_noite(hora_inicio)
        b = minutos_desde_meia_noite(hora_fim)
    except ValueError as e:
        return False, str(e)
    if b <= a:
        return False, "❌ hora_fim deve ser posterior a hora_inicio (mesmo dia)."
    return True, ""


def _consome_credito(status: str, devolver: int) -> bool:
    if status in (
        "PRE_AGENDADO",
        "AGENDADO",
        "CONFIRMADO",
        "REALIZADO_PENDENTE_PGTO",
        "CONCLUIDO",
    ):
        return True
    if status == "CANCELADO" and int(devolver) == 0:
        return True
    return False


def _count_consumindo(
    cur,
    venda_item_id: int,
    pacote_sessao_id: int | None,
) -> int:
    cur.execute(
        """
        SELECT status, devolver_ao_buffer, pacote_sessao_id
        FROM agendamentos
        WHERE venda_item_id = ? AND modo_origem = 'credito_venda'
        """,
        (int(venda_item_id),),
    )
    n = 0
    for st, dev, psid in cur.fetchall():
        if pacote_sessao_id is None:
            if psid is not None:
                continue
        else:
            if psid != pacote_sessao_id:
                continue
        if _consome_credito(str(st), int(dev)):
            n += 1
    return n


def direito_total_bucket(
    cur,
    venda_item_id: int,
    pacote_sessao_id: int | None,
) -> int:
    cur.execute(
        """
        SELECT vi.quantidade, vi.servico_id, s.natureza
        FROM venda_itens vi
        JOIN servicos s ON s.id = vi.servico_id
        WHERE vi.id = ?
        """,
        (int(venda_item_id),),
    )
    row = cur.fetchone()
    if not row:
        return 0
    qty, sid, nat = int(row[0]), int(row[1]), str(row[2])
    if nat == "Produto":
        return 0
    if nat == "Pacote":
        if pacote_sessao_id is None:
            return 0
        cur.execute(
            """
            SELECT quantidade FROM servico_pacote_sessoes
            WHERE id = ? AND pacote_servico_id = ?
            """,
            (int(pacote_sessao_id), sid),
        )
        r2 = cur.fetchone()
        if not r2:
            return 0
        return int(r2[0]) * qty
    if nat in ("Sessão", "Coworking", "Evento"):
        if pacote_sessao_id is not None:
            return 0
        return qty
    return 0


def saldo_bucket(cur, venda_item_id: int, pacote_sessao_id: int | None) -> int:
    tot = direito_total_bucket(cur, venda_item_id, pacote_sessao_id)
    if tot <= 0:
        return 0
    return tot - _count_consumindo(cur, venda_item_id, pacote_sessao_id)


def _tipo_origem_para_natureza(
    natureza: str, pacote_sessao_id: int | None
) -> tuple[bool, str, TipoOrigem | None]:
    if pacote_sessao_id is not None:
        return True, "", "pacote"
    if natureza == "Sessão":
        return True, "", "sessao_avulsa"
    if natureza == "Coworking":
        return True, "", "coworking"
    if natureza == "Evento":
        return True, "", "evento"
    return False, "❌ Esta linha de venda não gera créditos agendáveis (ex.: Produto ou Pacote sem componente).", None


def _servico_ocorrencia(
    cur, venda_item_id: int, pacote_sessao_id: int | None
) -> tuple[bool, str, int | None]:
    cur.execute(
        """
        SELECT vi.servico_id, s.natureza
        FROM venda_itens vi
        JOIN servicos s ON s.id = vi.servico_id
        WHERE vi.id = ?
        """,
        (int(venda_item_id),),
    )
    row = cur.fetchone()
    if not row:
        return False, "❌ Linha de venda não encontrada.", None
    sid, nat = int(row[0]), str(row[1])
    if pacote_sessao_id is None:
        return True, "", sid
    cur.execute(
        """
        SELECT sessao_servico_id FROM servico_pacote_sessoes
        WHERE id = ? AND pacote_servico_id = ?
        """,
        (int(pacote_sessao_id), sid),
    )
    r2 = cur.fetchone()
    if not r2:
        return False, "❌ Componente de pacote inválido para esta linha.", None
    return True, "", int(r2[0])


def rotulo_pagamento_venda(cur, venda_id: int | None) -> str:
    if venda_id is None:
        return "Pré-venda (sem venda)"
    cur.execute(
        "SELECT estado_pagamento, total_final_centavos FROM vendas WHERE id = ?",
        (int(venda_id),),
    )
    row = cur.fetchone()
    if not row:
        return "—"
    est, total = str(row[0]), int(row[1])
    vid = int(venda_id)
    pago = total_liquidado_venda_centavos(cur, vid)
    esperado_liq = total_esperado_liquidacao_venda_centavos(cur, vid)
    hoje = date.today().isoformat()
    cur.execute(
        """
        SELECT COALESCE(SUM(valor_centavos), 0) FROM venda_recebimentos_previstos
        WHERE venda_id = ? AND data_prevista < ?
        """,
        (int(venda_id), hoje),
    )
    atrasado = int(cur.fetchone()[0])
    if pago >= esperado_liq and esperado_liq > 0:
        return "Pago"
    if pago > 0 and pago < esperado_liq:
        return f"Parcialmente pago ({pago/100:.2f}/{esperado_liq/100:.2f} € · {est})"
    if atrasado > 0:
        return f"Em aberto / atrasado ({est})"
    return f"Em aberto ({est})"


def listar_buckets_credito_cliente(cliente_id: int) -> list[dict[str, Any]]:
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT vi.id, vi.venda_id, vi.servico_id, vi.nome_snapshot, vi.quantidade, s.natureza
            FROM venda_itens vi
            JOIN vendas v ON v.id = vi.venda_id
            JOIN servicos s ON s.id = vi.servico_id
            WHERE v.cliente_id = ?
            ORDER BY vi.venda_id DESC, vi.ordem
            """,
            (int(cliente_id),),
        )
        out: list[dict[str, Any]] = []
        for iid, vid, sv_id, nome_snap, qty, nat in cur.fetchall():
            nat = str(nat)
            if nat == "Produto":
                continue
            if nat == "Pacote":
                cur.execute(
                    """
                    SELECT sps.id, sps.sessao_servico_id, sps.quantidade, se.nome
                    FROM servico_pacote_sessoes sps
                    JOIN servicos se ON se.id = sps.sessao_servico_id
                    WHERE sps.pacote_servico_id = ?
                    ORDER BY sps.ordem
                    """,
                    (int(sv_id),),
                )
                for psid, ssid, pq, sname in cur.fetchall():
                    total = int(pq) * int(qty)
                    usado = _count_consumindo(cur, int(iid), int(psid))
                    saldo = total - usado
                    if total <= 0:
                        continue
                    out.append(
                        {
                            "venda_item_id": int(iid),
                            "venda_id": int(vid),
                            "pacote_sessao_id": int(psid),
                            "servico_id": int(ssid),
                            "rotulo": f"{nome_snap} → {sname} (pacote)",
                            "tipo_origem": "pacote",
                            "total_direitos": total,
                            "saldo": saldo,
                            "pagamento": rotulo_pagamento_venda(cur, int(vid)),
                        }
                    )
                continue
            if nat in ("Sessão", "Coworking", "Evento"):
                total = int(qty)
                usado = _count_consumindo(cur, int(iid), None)
                saldo = total - usado
                ok, _, tor = _tipo_origem_para_natureza(nat, None)
                if not ok:
                    continue
                out.append(
                    {
                        "venda_item_id": int(iid),
                        "venda_id": int(vid),
                        "pacote_sessao_id": None,
                        "servico_id": int(sv_id),
                        "rotulo": f"{nome_snap} ({nat})",
                        "tipo_origem": tor,
                        "total_direitos": total,
                        "saldo": saldo,
                        "pagamento": rotulo_pagamento_venda(cur, int(vid)),
                    }
                )
        return out
    finally:
        conn.close()


def listar_agendamentos(
    *,
    data_de: str | None = None,
    data_ate: str | None = None,
    cliente_ids: list[int] | None = None,
    servico_ids: list[int] | None = None,
    colaborador_ids: list[int] | None = None,
    status_list: list[str] | None = None,
    tipo_origem: list[str] | None = None,
    modos_origem: list[str] | None = None,
) -> list[dict[str, Any]]:
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        sql = """
            SELECT DISTINCT a.id, a.venda_id, a.venda_item_id, a.cliente_id, a.servico_id,
                   a.pacote_sessao_id, a.tipo_origem, a.data_agendamento, a.hora_inicio,
                   a.hora_fim, a.status, a.devolver_ao_buffer, a.observacoes,
                   a.modo_origem, a.preco_referencia_centavos,
                   c.nome AS cliente_nome, s.nome AS servico_nome, s.natureza AS servico_natureza
            FROM agendamentos a
            JOIN clientes c ON c.id = a.cliente_id
            JOIN servicos s ON s.id = a.servico_id
        """
        joins = []
        where = ["1=1"]
        params: list[Any] = []
        if colaborador_ids:
            joins.append(
                "JOIN agendamento_colaboradores ac ON ac.agendamento_id = a.id "
                "AND ac.colaborador_id IN ({})".format(
                    ",".join("?" * len(colaborador_ids))
                )
            )
            params.extend(int(x) for x in colaborador_ids)
        if data_de:
            where.append("a.data_agendamento >= ?")
            params.append(str(data_de)[:10])
        if data_ate:
            where.append("a.data_agendamento <= ?")
            params.append(str(data_ate)[:10])
        if cliente_ids:
            where.append("a.cliente_id IN ({})".format(",".join("?" * len(cliente_ids))))
            params.extend(int(x) for x in cliente_ids)
        if servico_ids:
            where.append("a.servico_id IN ({})".format(",".join("?" * len(servico_ids))))
            params.extend(int(x) for x in servico_ids)
        if status_list:
            where.append("a.status IN ({})".format(",".join("?" * len(status_list))))
            params.extend(status_list)
        if tipo_origem:
            where.append("a.tipo_origem IN ({})".format(",".join("?" * len(tipo_origem))))
            params.extend(tipo_origem)
        if modos_origem:
            where.append("a.modo_origem IN ({})".format(",".join("?" * len(modos_origem))))
            params.extend(modos_origem)
        sql = sql + " " + " ".join(joins) + " WHERE " + " AND ".join(where)
        sql += " ORDER BY a.data_agendamento, a.hora_inicio, a.id"
        cur.execute(sql, params)
        rows = cur.fetchall()
        out = []
        for r in rows:
            aid = int(r[0])
            cur.execute(
                """
                SELECT colaborador_id FROM agendamento_colaboradores
                WHERE agendamento_id = ? ORDER BY ordem
                """,
                (aid,),
            )
            cids = [int(x[0]) for x in cur.fetchall()]
            nomes = []
            for cid in cids:
                cur.execute("SELECT nome FROM colaboradores WHERE id = ?", (cid,))
                rnm = cur.fetchone()
                nomes.append(str(rnm[0]) if rnm else "?")
            modo_o = str(r[13])
            preco_ref = int(r[14]) if r[14] is not None else None
            vid_raw = r[1]
            pag_lbl = (
                rotulo_pagamento_venda(cur, None)
                if modo_o == "pre_venda"
                else rotulo_pagamento_venda(cur, int(vid_raw))
            )
            out.append(
                {
                    "id": aid,
                    "venda_id": int(vid_raw) if vid_raw is not None else None,
                    "venda_item_id": int(r[2]) if r[2] is not None else None,
                    "cliente_id": int(r[3]),
                    "servico_id": int(r[4]),
                    "pacote_sessao_id": int(r[5]) if r[5] is not None else None,
                    "tipo_origem": str(r[6]),
                    "data_agendamento": str(r[7]),
                    "hora_inicio": str(r[8]),
                    "hora_fim": str(r[9]),
                    "status": str(r[10]),
                    "devolver_ao_buffer": int(r[11]),
                    "observacoes": str(r[12] or ""),
                    "modo_origem": modo_o,
                    "preco_referencia_centavos": preco_ref,
                    "cliente_nome": str(r[15]),
                    "servico_nome": str(r[16]),
                    "servico_natureza": str(r[17]),
                    "colaborador_ids": cids,
                    "colaboradores_nomes": nomes,
                    "pagamento": pag_lbl,
                }
            )
        return out
    finally:
        conn.close()


def obter_agendamento(ag_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT a.id, a.venda_id, a.venda_item_id, a.cliente_id, a.servico_id,
                   a.pacote_sessao_id, a.tipo_origem, a.data_agendamento, a.hora_inicio,
                   a.hora_fim, a.status, a.devolver_ao_buffer, a.observacoes,
                   a.modo_origem, a.preco_referencia_centavos,
                   c.nome, s.nome, s.natureza
            FROM agendamentos a
            JOIN clientes c ON c.id = a.cliente_id
            JOIN servicos s ON s.id = a.servico_id
            WHERE a.id = ?
            """,
            (int(ag_id),),
        )
        r = cur.fetchone()
        if not r:
            return None
        aid = int(r[0])
        cur.execute(
            """
            SELECT colaborador_id FROM agendamento_colaboradores
            WHERE agendamento_id = ? ORDER BY ordem
            """,
            (aid,),
        )
        cids = [int(x[0]) for x in cur.fetchall()]
        nomes: list[str] = []
        for cid in cids:
            cur.execute("SELECT nome FROM colaboradores WHERE id = ?", (cid,))
            rnm = cur.fetchone()
            nomes.append(str(rnm[0]) if rnm else "?")
        modo_o = str(r[13])
        preco_ref = int(r[14]) if r[14] is not None else None
        vid_raw = r[1]
        pag_lbl = (
            rotulo_pagamento_venda(cur, None)
            if modo_o == "pre_venda"
            else rotulo_pagamento_venda(cur, int(vid_raw))
        )
        return {
            "id": aid,
            "venda_id": int(vid_raw) if vid_raw is not None else None,
            "venda_item_id": int(r[2]) if r[2] is not None else None,
            "cliente_id": int(r[3]),
            "servico_id": int(r[4]),
            "pacote_sessao_id": int(r[5]) if r[5] is not None else None,
            "tipo_origem": str(r[6]),
            "data_agendamento": str(r[7]),
            "hora_inicio": str(r[8]),
            "hora_fim": str(r[9]),
            "status": str(r[10]),
            "devolver_ao_buffer": int(r[11]),
            "observacoes": str(r[12] or ""),
            "modo_origem": modo_o,
            "preco_referencia_centavos": preco_ref,
            "cliente_nome": str(r[15]),
            "servico_nome": str(r[16]),
            "servico_natureza": str(r[17]),
            "colaborador_ids": cids,
            "colaboradores_nomes": nomes,
            "pagamento": pag_lbl,
        }
    finally:
        conn.close()


def criar_agendamento(
    venda_item_id: int,
    pacote_sessao_id: int | None,
    data_agendamento: str,
    hora_inicio: str,
    hora_fim: str,
    colaborador_ids: list[int],
    observacoes: str = "",
) -> tuple[bool, str]:
    ok_t, msg_t = validar_intervalo_horario(hora_inicio, hora_fim)
    if not ok_t:
        return False, msg_t
    try:
        hi = _norm_hhmm(hora_inicio)
        hf = _norm_hhmm(hora_fim)
    except ValueError as e:
        return False, f"❌ {e}"
    d = str(data_agendamento)[:10]

    conn = get_connection()
    if not conn:
        return False, "❌ Não foi possível ligar à base de dados."
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT vi.venda_id, vi.servico_id, s.natureza, v.cliente_id
            FROM venda_itens vi
            JOIN servicos s ON s.id = vi.servico_id
            JOIN vendas v ON v.id = vi.venda_id
            WHERE vi.id = ?
            """,
            (int(venda_item_id),),
        )
        row = cur.fetchone()
        if not row:
            return False, "❌ Linha de venda não encontrada."
        venda_id, sid_item, natureza, cliente_id = (
            int(row[0]),
            int(row[1]),
            str(row[2]),
            int(row[3]),
        )
        ok_o, msg_o, tipo = _tipo_origem_para_natureza(natureza, pacote_sessao_id)
        if not ok_o or tipo is None:
            return False, msg_o
        ok_s, msg_s, serv_occ = _servico_ocorrencia(cur, int(venda_item_id), pacote_sessao_id)
        if not ok_s or serv_occ is None:
            return False, msg_s
        saldo = saldo_bucket(cur, int(venda_item_id), pacote_sessao_id)
        if saldo < 1:
            return False, "❌ Sem saldo de crédito para agendar nesta linha/componente."

        for cid in colaborador_ids:
            cur.execute("SELECT id FROM colaboradores WHERE id = ?", (int(cid),))
            if cur.fetchone() is None:
                return False, f"❌ Colaborador {cid} não encontrado."

        cur.execute(
            """
            INSERT INTO agendamentos (
                venda_id, venda_item_id, cliente_id, servico_id, pacote_sessao_id,
                tipo_origem, data_agendamento, hora_inicio, hora_fim, status,
                devolver_ao_buffer, observacoes, data_alteracao,
                modo_origem, preco_referencia_centavos
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'AGENDADO', 0, ?, CURRENT_TIMESTAMP,
                'credito_venda', NULL)
            """,
            (
                venda_id,
                int(venda_item_id),
                cliente_id,
                serv_occ,
                pacote_sessao_id,
                tipo,
                d,
                hi,
                hf,
                (observacoes or "").strip(),
            ),
        )
        aid = int(cur.lastrowid)
        for ordem, cid in enumerate(colaborador_ids, start=1):
            cur.execute(
                """
                INSERT INTO agendamento_colaboradores (agendamento_id, colaborador_id, ordem)
                VALUES (?, ?, ?)
                """,
                (aid, int(cid), ordem),
            )
        conn.commit()
        return True, f"✅ Agendamento #{aid} criado (AGENDADO)."
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao criar: {e}"
    finally:
        conn.close()


def atualizar_agendamento(
    ag_id: int,
    *,
    data_agendamento: str | None = None,
    hora_inicio: str | None = None,
    hora_fim: str | None = None,
    colaborador_ids: list[int] | None = None,
    observacoes: str | None = None,
) -> tuple[bool, str]:
    conn = get_connection()
    if not conn:
        return False, "❌ Não foi possível ligar à base de dados."
    try:
        cur = conn.cursor()
        cur.execute("SELECT status, hora_inicio, hora_fim FROM agendamentos WHERE id = ?", (int(ag_id),))
        row = cur.fetchone()
        if not row:
            return False, "❌ Agendamento não encontrado."
        st = str(row[0])
        if st == "CANCELADO":
            return False, "❌ Agendamento cancelado — não é editável."
        if st == "CONCLUIDO":
            return False, "❌ Agendamento concluído — não é editável."
        hi = hora_inicio if hora_inicio is not None else str(row[1])
        hf = hora_fim if hora_fim is not None else str(row[2])
        ok_t, msg_t = validar_intervalo_horario(hi, hf)
        if not ok_t:
            return False, msg_t
        try:
            hi = _norm_hhmm(hi)
            hf = _norm_hhmm(hf)
        except ValueError as e:
            return False, f"❌ {e}"
        if data_agendamento is not None:
            d = str(data_agendamento)[:10]
            cur.execute(
                "UPDATE agendamentos SET data_agendamento = ?, data_alteracao = CURRENT_TIMESTAMP WHERE id = ?",
                (d, int(ag_id)),
            )
        cur.execute(
            """
            UPDATE agendamentos
            SET hora_inicio = ?, hora_fim = ?, data_alteracao = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (hi, hf, int(ag_id)),
        )
        if observacoes is not None:
            cur.execute(
                "UPDATE agendamentos SET observacoes = ?, data_alteracao = CURRENT_TIMESTAMP WHERE id = ?",
                ((observacoes or "").strip(), int(ag_id)),
            )
        if colaborador_ids is not None:
            for cid in colaborador_ids:
                cur.execute("SELECT id FROM colaboradores WHERE id = ?", (int(cid),))
                if cur.fetchone() is None:
                    return False, f"❌ Colaborador {cid} não encontrado."
            cur.execute("DELETE FROM agendamento_colaboradores WHERE agendamento_id = ?", (int(ag_id),))
            for ordem, cid in enumerate(colaborador_ids, start=1):
                cur.execute(
                    """
                    INSERT INTO agendamento_colaboradores (agendamento_id, colaborador_id, ordem)
                    VALUES (?, ?, ?)
                    """,
                    (int(ag_id), int(cid), ordem),
                )
        conn.commit()
        return True, "✅ Agendamento atualizado."
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao atualizar: {e}"
    finally:
        conn.close()


def _append_ag_hist(
    cur,
    ag_id: int,
    campo: str,
    valor_anterior: str | None,
    valor_novo: str | None,
    *,
    motivo: str | None = None,
    actor: str | None = None,
) -> None:
    cur.execute(
        """
        INSERT INTO agendamento_historico (
            agendamento_id, campo, valor_anterior, valor_novo, motivo, actor
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (int(ag_id), campo, valor_anterior, valor_novo, motivo, actor),
    )


def _base_repasse_centavos(cur, ag_id: int) -> tuple[int, int]:
    cur.execute(
        """
        SELECT a.modo_origem, a.preco_referencia_centavos, a.venda_item_id, a.servico_id
        FROM agendamentos a WHERE a.id = ?
        """,
        (int(ag_id),),
    )
    r = cur.fetchone()
    if not r:
        return 0, 0
    modo, pref, viid, sid = str(r[0]), r[1], r[2], int(r[3])
    if modo == "pre_venda":
        return max(0, int(pref or 0)), sid
    if viid is None:
        return 0, sid
    cur.execute(
        "SELECT total_linha_centavos, quantidade FROM venda_itens WHERE id = ?",
        (int(viid),),
    )
    r2 = cur.fetchone()
    if not r2:
        return 0, sid
    tlin, q = int(r2[0]), max(1, int(r2[1]))
    return int(tlin // q), sid


def _gerar_repasse_linhas(cur, ag_id: int) -> None:
    base, servico_id = _base_repasse_centavos(cur, ag_id)
    if base <= 0 or servico_id <= 0:
        return
    cur.execute(
        """
        DELETE FROM repasse_linhas
        WHERE agendamento_id = ? AND status_repasse = 'PENDENTE_REPASSE'
        """,
        (int(ag_id),),
    )
    cur.execute(
        """
        SELECT ac.colaborador_id, cs.percentual_centesimos
        FROM agendamento_colaboradores ac
        LEFT JOIN colaborador_servicos cs
          ON cs.colaborador_id = ac.colaborador_id AND cs.servico_id = ?
        WHERE ac.agendamento_id = ?
        ORDER BY ac.ordem
        """,
        (servico_id, int(ag_id)),
    )
    for colab_id, pct in cur.fetchall():
        bp = int(pct or 0)
        if colab_id is None or bp <= 0:
            continue
        val = int(base * bp / 10000)
        if val <= 0:
            continue
        cur.execute(
            """
            INSERT INTO repasse_linhas (
                agendamento_id, colaborador_id, base_calculo_centavos,
                percentual_bp, valor_repasse_centavos, status_repasse
            ) VALUES (?, ?, ?, ?, ?, 'PENDENTE_REPASSE')
            """,
            (int(ag_id), int(colab_id), base, bp, val),
        )


def _valor_credito_cancelamento_sugerido_cur(cur, ag_id: int) -> int:
    cur.execute(
        """
        SELECT modo_origem, preco_referencia_centavos, venda_item_id
        FROM agendamentos WHERE id = ?
        """,
        (int(ag_id),),
    )
    r = cur.fetchone()
    if not r:
        return 0
    modo, pref, viid = str(r[0]), r[1], r[2]
    if modo == "pre_venda":
        return max(0, int(pref or 0))
    if viid is None:
        return 0
    cur.execute(
        "SELECT total_linha_centavos, quantidade FROM venda_itens WHERE id = ?",
        (int(viid),),
    )
    r2 = cur.fetchone()
    if not r2:
        return 0
    tlin, q = int(r2[0]), max(1, int(r2[1]))
    return int(tlin // q)


def alterar_status(
    ag_id: int, novo: StatusAgendamento, *, actor: str | None = None
) -> tuple[bool, str]:
    n = str(novo)
    if n == "CANCELADO":
        return False, "❌ Use cancelar_agendamento com a opção de buffer."
    permitidos = {
        "PRE_AGENDADO",
        "AGENDADO",
        "CONFIRMADO",
        "REALIZADO_PENDENTE_PGTO",
        "CONCLUIDO",
    }
    if n not in permitidos:
        return False, "❌ Estado inválido para esta operação."
    conn = get_connection()
    if not conn:
        return False, "❌ Não foi possível ligar à base de dados."
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT status, modo_origem, venda_id FROM agendamentos WHERE id = ?",
            (int(ag_id),),
        )
        row = cur.fetchone()
        if not row:
            return False, "❌ Agendamento não encontrado."
        atual, modo_o, vid_chk = str(row[0]), str(row[1]), row[2]
        if atual == "CANCELADO":
            return False, "❌ Já cancelado."
        if atual == "CONCLUIDO" and n != "CONCLUIDO":
            return False, "❌ Já concluído."
        if n == atual:
            return True, "Sem alteração."
        if n == "CONFIRMADO":
            if atual != "AGENDADO":
                return False, "❌ Só AGENDADO passa a CONFIRMADO."
        elif n == "REALIZADO_PENDENTE_PGTO":
            if atual not in ("AGENDADO", "CONFIRMADO"):
                return False, "❌ Só AGENDADO ou CONFIRMADO podem passar a REALIZADO_PENDENTE_PGTO."
        elif n == "CONCLUIDO":
            if atual not in ("AGENDADO", "CONFIRMADO", "REALIZADO_PENDENTE_PGTO"):
                return False, "❌ Estado atual não permite concluir."
            if modo_o == "pre_venda" and vid_chk is None:
                return False, "❌ Pré-venda sem venda associada — não pode concluir."
            if modo_o != "pre_venda" and vid_chk is None:
                return False, "❌ Sem venda associada."
            vid = int(vid_chk)
            esp = total_esperado_liquidacao_venda_centavos(cur, vid)
            liq = total_liquidado_venda_centavos(cur, vid)
            if liq < esp:
                cur.execute(
                    """
                    UPDATE agendamentos
                    SET status = 'REALIZADO_PENDENTE_PGTO', data_alteracao = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (int(ag_id),),
                )
                _append_ag_hist(
                    cur,
                    int(ag_id),
                    "status",
                    atual,
                    "REALIZADO_PENDENTE_PGTO",
                    motivo="gate_pagamento_incompleto",
                    actor=actor,
                )
                _gerar_repasse_linhas(cur, int(ag_id))
                conn.commit()
                return (
                    True,
                    f"⚠️ Pagamento incompleto ({liq / 100:.2f} € de {esp / 100:.2f} € a liquidar) — "
                    "estado REALIZADO_PENDENTE_PGTO.",
                )
        elif n == "PRE_AGENDADO":
            return False, "❌ Transição para PRE_AGENDADO não suportada neste fluxo."
        elif n == "AGENDADO":
            return False, "❌ Transição para AGENDADO não suportada neste fluxo."
        cur.execute(
            """
            UPDATE agendamentos
            SET status = ?, data_alteracao = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (n, int(ag_id)),
        )
        _append_ag_hist(cur, int(ag_id), "status", atual, n, actor=actor)
        if n in ("REALIZADO_PENDENTE_PGTO", "CONCLUIDO"):
            _gerar_repasse_linhas(cur, int(ag_id))
        conn.commit()
        return True, f"✅ Estado: {n}."
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {e}"
    finally:
        conn.close()


def cancelar_agendamento(
    ag_id: int,
    devolver_ao_buffer: bool,
    *,
    converter_valor_pago_em_credito_loja: bool = False,
    actor: str | None = None,
) -> tuple[bool, str]:
    conn = get_connection()
    if not conn:
        return False, "❌ Não foi possível ligar à base de dados."
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT status, modo_origem, cliente_id FROM agendamentos WHERE id = ?",
            (int(ag_id),),
        )
        row = cur.fetchone()
        if not row:
            return False, "❌ Agendamento não encontrado."
        atual, modo_o, cliente_id = str(row[0]), str(row[1]), int(row[2])
        if atual == "CANCELADO":
            return False, "❌ Já cancelado."
        if atual == "CONCLUIDO":
            return False, "❌ Não é possível cancelar concluído."
        dev = 0 if modo_o == "pre_venda" else (1 if devolver_ao_buffer else 0)
        _append_ag_hist(
            cur,
            int(ag_id),
            "status",
            atual,
            "CANCELADO",
            motivo="cancelamento",
            actor=actor,
        )
        cur.execute(
            """
            UPDATE agendamentos
            SET status = 'CANCELADO', devolver_ao_buffer = ?,
                data_alteracao = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (dev, int(ag_id)),
        )
        extra_cred = ""
        if converter_valor_pago_em_credito_loja:
            val = _valor_credito_cancelamento_sugerido_cur(cur, int(ag_id))
            if val > 0:
                ok_ins = registrar_credito_por_cancelamento_agendamento(
                    cur,
                    cliente_id=cliente_id,
                    agendamento_id=int(ag_id),
                    valor_centavos=val,
                    actor=actor,
                )
                if ok_ins:
                    extra_cred = f" Crédito de loja +{val / 100:.2f} € registado."
                else:
                    extra_cred = " (Crédito de cancelamento já existia — sem duplicar.)"
            else:
                extra_cred = " (Sem valor sugerido para crédito.)"
        conn.commit()
        if modo_o == "pre_venda":
            msg = "✅ Cancelado (pré-venda — sem crédito em buffer)." + extra_cred
        else:
            msg = (
                "✅ Cancelado — crédito devolvido ao buffer."
                if dev
                else "✅ Cancelado — crédito não devolvido ao buffer."
            )
            msg += extra_cred
        return True, msg
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {e}"
    finally:
        conn.close()


def criar_agendamento_pre_venda(
    cliente_id: int,
    servico_id: int,
    data_agendamento: str,
    hora_inicio: str,
    hora_fim: str,
    colaborador_ids: list[int],
    observacoes: str = "",
    preco_referencia_centavos: int | None = None,
) -> tuple[bool, str]:
    """MVP: só Sessão, Coworking, Evento — sem pacote (E11)."""
    ok_t, msg_t = validar_intervalo_horario(hora_inicio, hora_fim)
    if not ok_t:
        return False, msg_t
    try:
        hi = _norm_hhmm(hora_inicio)
        hf = _norm_hhmm(hora_fim)
    except ValueError as e:
        return False, f"❌ {e}"
    d = str(data_agendamento)[:10]
    cid = int(cliente_id)
    sid = int(servico_id)
    pr = preco_referencia_centavos
    if pr is not None and int(pr) < 0:
        return False, "❌ Preço de referência inválido."

    conn = get_connection()
    if not conn:
        return False, "❌ Não foi possível ligar à base de dados."
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM clientes WHERE id = ?", (cid,))
        if cur.fetchone() is None:
            return False, "❌ Cliente não encontrado."
        cur.execute("SELECT natureza FROM servicos WHERE id = ?", (sid,))
        rnat = cur.fetchone()
        if not rnat:
            return False, "❌ Serviço não encontrado."
        natureza = str(rnat[0])
        if natureza not in ("Sessão", "Coworking", "Evento"):
            return False, "❌ Pré-venda (MVP) só para Sessão, Coworking ou Evento."
        ok_o, msg_o, tipo = _tipo_origem_para_natureza(natureza, None)
        if not ok_o or tipo is None:
            return False, msg_o

        for colab in colaborador_ids:
            cur.execute("SELECT id FROM colaboradores WHERE id = ?", (int(colab),))
            if cur.fetchone() is None:
                return False, f"❌ Colaborador {colab} não encontrado."

        cur.execute(
            """
            INSERT INTO agendamentos (
                venda_id, venda_item_id, cliente_id, servico_id, pacote_sessao_id,
                tipo_origem, data_agendamento, hora_inicio, hora_fim, status,
                devolver_ao_buffer, observacoes, data_alteracao,
                modo_origem, preco_referencia_centavos
            ) VALUES (NULL, NULL, ?, ?, NULL, ?, ?, ?, ?, 'AGENDADO', 0, ?, CURRENT_TIMESTAMP,
                'pre_venda', ?)
            """,
            (
                cid,
                sid,
                tipo,
                d,
                hi,
                hf,
                (observacoes or "").strip(),
                pr,
            ),
        )
        aid = int(cur.lastrowid)
        for ordem, colab in enumerate(colaborador_ids, start=1):
            cur.execute(
                """
                INSERT INTO agendamento_colaboradores (agendamento_id, colaborador_id, ordem)
                VALUES (?, ?, ?)
                """,
                (aid, int(colab), ordem),
            )
        conn.commit()
        return True, f"✅ Pré-venda #{aid} criada (AGENDADO)."
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao criar pré-venda: {e}"
    finally:
        conn.close()


def associar_agendamento_pre_venda_a_item(
    ag_id: int, venda_item_id: int
) -> tuple[bool, str]:
    conn = get_connection()
    if not conn:
        return False, "❌ Não foi possível ligar à base de dados."
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT modo_origem, status, cliente_id, servico_id
            FROM agendamentos WHERE id = ?
            """,
            (int(ag_id),),
        )
        row = cur.fetchone()
        if not row:
            return False, "❌ Agendamento não encontrado."
        modo_o, st_ag, cli_ag, srv_ag = str(row[0]), str(row[1]), int(row[2]), int(row[3])
        if modo_o != "pre_venda":
            return False, "❌ Só agendamentos em pré-venda podem ser associados desta forma."
        if st_ag in ("CANCELADO", "CONCLUIDO", "REALIZADO_PENDENTE_PGTO"):
            return False, "❌ Estado não permite associação."
        cur.execute(
            """
            SELECT vi.venda_id, v.cliente_id, vi.servico_id
            FROM venda_itens vi
            JOIN vendas v ON v.id = vi.venda_id
            WHERE vi.id = ?
            """,
            (int(venda_item_id),),
        )
        r2 = cur.fetchone()
        if not r2:
            return False, "❌ Linha de venda não encontrada."
        venda_id, cli_v, srv_v = int(r2[0]), int(r2[1]), int(r2[2])
        if cli_v != cli_ag:
            return False, "❌ Cliente da venda difere do agendamento."
        if srv_v != srv_ag:
            return False, "❌ Serviço da linha de venda deve coincidir com o agendamento."
        cur.execute(
            """
            UPDATE agendamentos
            SET venda_id = ?, venda_item_id = ?, modo_origem = 'credito_venda',
                data_alteracao = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (venda_id, int(venda_item_id), int(ag_id)),
        )
        conn.commit()
        return True, "✅ Pré-venda associada à linha de venda — modo crédito."
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao associar: {e}"
    finally:
        conn.close()


def obter_primeiro_item_venda_por_servico(
    venda_id: int, servico_id: int
) -> int | None:
    conn = get_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id FROM venda_itens
            WHERE venda_id = ? AND servico_id = ?
            ORDER BY ordem ASC, id ASC
            LIMIT 1
            """,
            (int(venda_id), int(servico_id)),
        )
        row = cur.fetchone()
        return int(row[0]) if row else None
    finally:
        conn.close()


def contar_pre_venda_futuros(data_referencia: str | None = None) -> int:
    ref = (data_referencia or date.today().isoformat())[:10]
    conn = get_connection()
    if not conn:
        return 0
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*) FROM agendamentos
            WHERE modo_origem = 'pre_venda'
              AND data_agendamento >= ?
              AND status IN ('AGENDADO', 'CONFIRMADO')
            """,
            (ref,),
        )
        return int(cur.fetchone()[0])
    finally:
        conn.close()


def contar_por_status_periodo(data_de: str, data_ate: str) -> dict[str, int]:
    conn = get_connection()
    if not conn:
        return {}
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT status, COUNT(*) FROM agendamentos
            WHERE data_agendamento >= ? AND data_agendamento <= ?
            GROUP BY status
            """,
            (str(data_de)[:10], str(data_ate)[:10]),
        )
        return {str(k): int(v) for k, v in cur.fetchall()}
    finally:
        conn.close()


__all__ = [
    "alterar_status",
    "associar_agendamento_pre_venda_a_item",
    "atualizar_agendamento",
    "cancelar_agendamento",
    "contar_por_status_periodo",
    "contar_pre_venda_futuros",
    "criar_agendamento",
    "criar_agendamento_pre_venda",
    "listar_agendamentos",
    "listar_buckets_credito_cliente",
    "minutos_desde_meia_noite",
    "obter_agendamento",
    "obter_primeiro_item_venda_por_servico",
    "rotulo_pagamento_venda",
    "saldo_bucket",
    "validar_intervalo_horario",
]
