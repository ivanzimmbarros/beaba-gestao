"""Agendamentos — ocorrências na agenda, buffer de créditos (venda) e máquina de estados (E09)."""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any, Literal

from src.database.connection import get_connection
from src.modules.catalogo import obter_servico_para_formulario
from src.modules.colaborador import nome_colaborador_sem_sufixo_id_ui
from src.modules.constants import ESTADO_AGENDAMENTO_REALIZADO_PENDENTE_LABEL_PT
from src.modules.credito_ledger import (
    obter_aberto_liquidacao_venda_centavos,
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


def _norm_tipo_atendimento_db(s: str) -> str | None:
    t = (s or "").strip().lower()
    if t == "presencial":
        return "presencial"
    if t == "virtual":
        return "virtual"
    return None


def validar_tipo_atendimento_e_sala(
    tipo_atendimento: str,
    sala_virtual_disponibilizada: int | None,
) -> tuple[bool, str, str | None, int | None]:
    """
    Presencial → sala_db sempre None (N/A nos indicadores).
    Virtual → obriga sala 0 ou 1.
    """
    td = _norm_tipo_atendimento_db(tipo_atendimento)
    if td is None:
        return False, "❌ Tipo de atendimento inválido.", None, None
    if td == "presencial":
        return True, "", "presencial", None
    if sala_virtual_disponibilizada is None:
        return (
            False,
            "❌ Indique se a sala virtual já foi disponibilizada (Sim ou Não).",
            None,
            None,
        )
    v = int(sala_virtual_disponibilizada)
    if v not in (0, 1):
        return False, "❌ Valor inválido para sala virtual.", None, None
    return True, "", "virtual", v


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


def promover_agendamentos_realizado_pendente_apos_liquidacao_venda(venda_id: int) -> None:
    """
    Quando a venda passa a totalmente liquidada, tenta concluir agendamentos que ficaram
    em REALIZADO_PENDENTE_PGTO por falta de pagamento (ex.: pacote parcial → integral).
    """
    conn = get_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id FROM agendamentos
            WHERE venda_id = ?
              AND modo_origem = 'credito_venda'
              AND IFNULL(UPPER(TRIM(status)), '') = 'REALIZADO_PENDENTE_PGTO'
            """,
            (int(venda_id),),
        )
        aids = [int(r[0]) for r in cur.fetchall()]
    finally:
        conn.close()
    for aid in aids:
        alterar_status(int(aid), "CONCLUIDO", actor="sync_pagamento_venda")


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
        return (
            "Parcialmente pago (Valor Pago: EUR "
            f"{pago/100:.2f} - Valor Catalogo: EUR {esperado_liq/100:.2f})"
        )
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


def analisar_sessoes_pacote_pendentes_cag(
    cliente_id: int, pacote_servico_id: int
) -> tuple[int, list[tuple[str, str]]]:
    """
    Para o pacote de catálogo `pacote_servico_id` e o cliente:
    - `total` = unidades de sessão (soma das quantidades das linhas do pacote) ainda **sem**
      agendamento com estado diferente de CANCELADO.
    - `opções` = uma entrada por unidade pendente: valor `pacote_sessao_id|sessao_servico_id|u{k}`
      (rótulo = nome da sessão, sem «×N»).
    Serve à UI CAG e a indicadores (usar `total` ou `len(opções)`).
    """
    cid = int(cliente_id)
    pid = int(pacote_servico_id)
    conn = get_connection()
    if not conn:
        return 0, []
    out: list[tuple[str, str]] = []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, sessao_servico_id, quantidade, ordem
            FROM servico_pacote_sessoes
            WHERE pacote_servico_id = ?
            ORDER BY ordem, id
            """,
            (pid,),
        )
        for psid, ssid, qty, _ord in cur.fetchall():
            cur.execute(
                """
                SELECT COUNT(*) FROM agendamentos
                WHERE cliente_id = ? AND pacote_sessao_id = ?
                  AND IFNULL(UPPER(TRIM(status)), '') != 'CANCELADO'
                """,
                (cid, int(psid)),
            )
            usados = int(cur.fetchone()[0])
            pend = max(0, int(qty) - usados)
            cur.execute("SELECT nome FROM servicos WHERE id = ?", (int(ssid),))
            rnm = cur.fetchone()
            nm = str(rnm[0]) if rnm else "Sessão"
            for k in range(1, pend + 1):
                out.append((f"{int(psid)}|{int(ssid)}|u{k}", nm))
        return len(out), out
    finally:
        conn.close()


def contar_total_sessoes_pacote_pendentes_agendamento(cliente_id: int, pacote_servico_id: int) -> int:
    """Total de unidades de sessão do pacote ainda pendentes de agendamento (≠ cancelado) — indicadores / relatórios."""
    tot, _ = analisar_sessoes_pacote_pendentes_cag(int(cliente_id), int(pacote_servico_id))
    return int(tot)


_STATUS_AGENDAMENTO_ATINGE_PRE: tuple[str, ...] = (
    "PRE_AGENDADO",
    "AGENDADO",
    "CONFIRMADO",
    "REALIZADO_PENDENTE_PGTO",
    "CONCLUIDO",
)


def _count_agendamentos_pos_compra_com_marco_pre_agendamento(
    cur,
    venda_item_id: int,
    pacote_sessao_id: int | None,
) -> int:
    """Agendamentos `credito_venda` já em estado ≥ Pré-agendado (exclui `CANCELADO`)."""
    ph = ",".join("?" * len(_STATUS_AGENDAMENTO_ATINGE_PRE))
    if pacote_sessao_id is None:
        cur.execute(
            f"""
            SELECT COUNT(*) FROM agendamentos
            WHERE venda_item_id = ?
              AND modo_origem = 'credito_venda'
              AND IFNULL(UPPER(TRIM(status)), '') IN ({ph})
            """,
            (int(venda_item_id), *_STATUS_AGENDAMENTO_ATINGE_PRE),
        )
    else:
        cur.execute(
            f"""
            SELECT COUNT(*) FROM agendamentos
            WHERE venda_item_id = ?
              AND modo_origem = 'credito_venda'
              AND pacote_sessao_id = ?
              AND IFNULL(UPPER(TRIM(status)), '') IN ({ph})
            """,
            (int(venda_item_id), int(pacote_sessao_id), *_STATUS_AGENDAMENTO_ATINGE_PRE),
        )
    return int(cur.fetchone()[0])


def _sap_fmt_data_contratacao_dd_mm_yyyy(iso_date: str | None) -> str:
    """`YYYY-MM-DD` → `dd-mm-aaaa` para rótulos «Serviços adquiridos…»."""
    s = str(iso_date or "").strip()[:10]
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        try:
            y, m, d = int(s[0:4]), int(s[5:7]), int(s[8:10])
            return f"{d:02d}-{m:02d}-{y:04d}"
        except ValueError:
            pass
    return s if s else "—"


def _sap_data_criacao_min_credito_iso(cur, venda_item_id: int) -> str | None:
    """Data mínima (YYYY-MM-DD) de `data_criacao_registo` em créditos de venda não cancelados."""
    cur.execute(
        """
        SELECT MIN(date(data_criacao_registo))
        FROM agendamentos
        WHERE venda_item_id = ?
          AND modo_origem = 'credito_venda'
          AND IFNULL(UPPER(TRIM(status)), '') != 'CANCELADO'
        """,
        (int(venda_item_id),),
    )
    r = cur.fetchone()
    if not r or not r[0]:
        return None
    s = str(r[0]).strip()[:10]
    return s if len(s) == 10 else None


def _sap_data_registo_celula_cag(
    cur,
    *,
    nat_s: str,
    venda_item_id: int,
    data_contr_iso: object,
    pag_lab: str,
) -> str:
    """Regra CAG: pacote → data aquisição; avulso pago → aquisição; avulso não pago → 1.ª criação de registo."""
    dd_contr = _sap_fmt_data_contratacao_dd_mm_yyyy(
        str(data_contr_iso).strip()[:10] if data_contr_iso is not None else None
    )
    if str(nat_s or "").strip() == "Pacote":
        return dd_contr
    if str(pag_lab or "").strip() == "Pago":
        return dd_contr
    alt = _sap_data_criacao_min_credito_iso(cur, int(venda_item_id))
    return _sap_fmt_data_contratacao_dd_mm_yyyy(alt) if alt else dd_contr


def _sap_especialidade_servico_catalogo(servico_catalog_id: int) -> str:
    row = obter_servico_para_formulario(int(servico_catalog_id))
    if not row:
        return "—"
    en = str(row.get("especialidade_nome") or "").strip()
    return en if en else "—"


def listar_opcoes_servicos_adquiridos_pendente_pre_agendamento(
    cliente_id: int,
) -> list[dict[str, Any]]:
    """
    Linhas de venda com pagamento liquidado (integral/parcial) ou **pendente** (sessões,
    pacotes, etc.) com unidade ainda **sem** agendamento `credito_venda` em estado ≥
    «Pré-agendado» (cancelamentos não contam; o registo volta a aparecer).

    **Pacote:** uma única opção por `venda_item` com pendências (`token` …`|pkg`); as
    unidades pendentes aparecem na UI em «Lista de Sessoes do Pacote Pendente Agendamento».
    """
    cid = int(cliente_id)
    conn = get_connection()
    if not conn:
        return []
    out: list[dict[str, Any]] = []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT vi.id, vi.venda_id, vi.servico_id, vi.quantidade, vi.nome_snapshot,
                   s.natureza, s.nome AS nome_catalogo,
                   c.nome AS cliente_nome,
                   COALESCE(
                       (
                           SELECT MIN(date(vpl.criado_em))
                           FROM venda_pagamento_linhas vpl
                           WHERE vpl.venda_id = v.id
                             AND COALESCE(vpl.valor_centavos, 0) > 0
                       ),
                       date(v.data_registo)
                   ) AS data_contr_iso
            FROM venda_itens vi
            JOIN vendas v ON v.id = vi.venda_id
            JOIN servicos s ON s.id = vi.servico_id
            JOIN clientes c ON c.id = v.cliente_id
            WHERE v.cliente_id = ?
              AND IFNULL(LOWER(TRIM(v.estado_pagamento)), '') IN ('integral', 'parcial', 'pendente')
              AND IFNULL(s.natureza, '') != 'Produto'
            ORDER BY v.id ASC, vi.ordem, vi.id
            """,
            (cid,),
        )
        for vi_id, vid, sid_cat, qty, nome_snap, nat, nome_cat, cliente_nome, data_contr_iso in cur.fetchall():
            vi_id_i = int(vi_id)
            vid_i = int(vid)
            sid_i = int(sid_cat)
            qty_i = max(1, int(qty or 1))
            nat_s = str(nat or "").strip()
            nome_snap_s = str(nome_snap or nome_cat or "").strip() or str(nome_cat or "—")
            nome_cat_s = str(nome_cat or "").strip()
            dd_mm = _sap_fmt_data_contratacao_dd_mm_yyyy(
                str(data_contr_iso).strip()[:10] if data_contr_iso is not None else None
            )

            if nat_s == "Pacote":
                cur.execute(
                    """
                    SELECT sps.id, sps.sessao_servico_id, sps.quantidade, se.nome
                    FROM servico_pacote_sessoes sps
                    JOIN servicos se ON se.id = sps.sessao_servico_id
                    WHERE sps.pacote_servico_id = ?
                    ORDER BY sps.ordem, sps.id
                    """,
                    (sid_i,),
                )
                sps_rows = cur.fetchall()
                if not sps_rows:
                    continue
                synth = " & ".join(
                    f"{max(1, int(pq or 1))}x {str(sn or '').strip()}"
                    for _ps, _ss, pq, sn in sps_rows
                )
                pendencias: list[tuple[int, int, str, int]] = []
                for psid, ssid, pq_cat, snome in sps_rows:
                    psid_i = int(psid)
                    ssid_i = int(ssid)
                    snome_t = str(snome or "").strip() or "Sessão"
                    total_u = max(0, int(pq_cat or 0) * qty_i)
                    if total_u < 1:
                        continue
                    usados = _count_agendamentos_pos_compra_com_marco_pre_agendamento(
                        cur, vi_id_i, psid_i
                    )
                    pend = max(0, total_u - usados)
                    if pend > 0:
                        pendencias.append((psid_i, ssid_i, snome_t, pend))
                total_opts_pac = sum(p for *_, p in pendencias)
                if total_opts_pac > 0:
                    tok = f"sap|{vi_id_i}|pkg"
                    rot = f"(Pacote - {dd_mm}) {nome_snap_s} - {synth}"
                    if total_opts_pac != 1:
                        rot += f" — {total_opts_pac} pendentes"
                    out.append(
                        {
                            "token": tok,
                            "rotulo": rot,
                            "natureza": "Pacote",
                            "servico_esc": f"{sid_i}|{nome_snap_s}",
                            "pacote_sessao_esc": None,
                            "venda_item_id": vi_id_i,
                            "venda_id": vid_i,
                            "servico_catalog_id": sid_i,
                            "pacote_sessao_id": None,
                            "cliente_nome": str(cliente_nome or "").strip(),
                            "data_contr_iso": str(data_contr_iso or "").strip()[:10],
                            "nome_servico_tabela": nome_snap_s,
                            "nome_pacote_tabela": nome_snap_s,
                        }
                    )
                continue

            if nat_s not in ("Sessão", "Coworking", "Evento"):
                continue
            total_u = qty_i
            usados = _count_agendamentos_pos_compra_com_marco_pre_agendamento(cur, vi_id_i, None)
            pend = max(0, total_u - usados)
            esc_srv = f"{sid_i}|{nome_cat_s}"
            for k in range(1, pend + 1):
                tok = f"sap|{vi_id_i}|u{k}"
                rot = f"({nat_s} - {dd_mm}) {nome_snap_s}"
                if pend > 1:
                    rot += f" · {k}/{pend}"
                out.append(
                    {
                        "token": tok,
                        "rotulo": rot,
                        "natureza": nat_s,
                        "servico_esc": esc_srv,
                        "pacote_sessao_esc": None,
                        "venda_item_id": vi_id_i,
                        "venda_id": vid_i,
                        "servico_catalog_id": sid_i,
                        "pacote_sessao_id": None,
                        "cliente_nome": str(cliente_nome or "").strip(),
                        "data_contr_iso": str(data_contr_iso or "").strip()[:10],
                        "nome_servico_tabela": (nome_snap_s or nome_cat_s).strip() or nome_cat_s,
                        "nome_pacote_tabela": "—",
                    }
                )
        for d in out:
            vid_i = int(d["venda_id"])
            vi_id_i = int(d["venda_item_id"])
            nat_s = str(d.get("natureza") or "").strip()
            pag = rotulo_pagamento_venda(cur, vid_i)
            d["status_pagamento"] = pag
            d["data_do_registo"] = _sap_data_registo_celula_cag(
                cur,
                nat_s=nat_s,
                venda_item_id=vi_id_i,
                data_contr_iso=d.get("data_contr_iso"),
                pag_lab=pag,
            )
            sid_cat = int(d.get("servico_catalog_id") or 0)
            d["especialidade"] = (
                _sap_especialidade_servico_catalogo(sid_cat) if sid_cat > 0 else "—"
            )
            d.pop("data_contr_iso", None)
        out.sort(
            key=lambda r: (
                str(r.get("data_do_registo") or ""),
                str(r.get("rotulo") or "").casefold(),
                str(r.get("token") or ""),
            )
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
                   a.tipo_atendimento, a.sala_virtual_disponibilizada,
                   c.nome AS cliente_nome, s.nome AS servico_nome, s.natureza AS servico_natureza,
                   spac.nome AS nome_do_pacote,
                   a.data_criacao_registo
            FROM agendamentos a
            JOIN clientes c ON c.id = a.cliente_id
            JOIN servicos s ON s.id = a.servico_id
            LEFT JOIN servico_pacote_sessoes sps ON sps.id = a.pacote_sessao_id
            LEFT JOIN servicos spac ON spac.id = sps.pacote_servico_id
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
                nomes.append(
                    nome_colaborador_sem_sufixo_id_ui(str(rnm[0]) if rnm else "?")
                    or "?"
                )
            modo_o = str(r[13])
            preco_ref = int(r[14]) if r[14] is not None else None
            tipo_at = str(r[15] or "presencial")
            sala_v = r[16]
            sala_vi: int | None = int(sala_v) if sala_v is not None else None
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
                    "tipo_atendimento": tipo_at,
                    "sala_virtual_disponibilizada": sala_vi,
                    "cliente_nome": str(r[17]),
                    "servico_nome": str(r[18]),
                    "servico_natureza": str(r[19]),
                    "nome_do_pacote": str(r[20] or "").strip(),
                    "data_criacao_registo": str(r[21] or "").strip(),
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
                   a.tipo_atendimento, a.sala_virtual_disponibilizada,
                   c.nome, s.nome, s.natureza,
                   spac.nome AS nome_pacote_cat, sps.pacote_servico_id AS pacote_servico_cat_id,
                   a.data_criacao_registo
            FROM agendamentos a
            JOIN clientes c ON c.id = a.cliente_id
            JOIN servicos s ON s.id = a.servico_id
            LEFT JOIN servico_pacote_sessoes sps ON sps.id = a.pacote_sessao_id
            LEFT JOIN servicos spac ON spac.id = sps.pacote_servico_id
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
            nomes.append(
                nome_colaborador_sem_sufixo_id_ui(str(rnm[0]) if rnm else "?") or "?"
            )
        modo_o = str(r[13])
        preco_ref = int(r[14]) if r[14] is not None else None
        tipo_at = str(r[15] or "presencial")
        sala_raw = r[16]
        sala_vi: int | None = int(sala_raw) if sala_raw is not None else None
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
            "tipo_atendimento": tipo_at,
            "sala_virtual_disponibilizada": sala_vi,
            "cliente_nome": str(r[17]),
            "servico_nome": str(r[18]),
            "servico_natureza": str(r[19]),
            "nome_do_pacote": str(r[20] or "").strip(),
            "pacote_servico_catalogo_id": int(r[21]) if r[21] is not None else None,
            "data_criacao_registo": str(r[22] or "").strip(),
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
    *,
    tipo_atendimento: str = "presencial",
    sala_virtual_disponibilizada: int | None = None,
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

        ok_tv, msg_tv, tdb, sdb = validar_tipo_atendimento_e_sala(
            tipo_atendimento, sala_virtual_disponibilizada
        )
        if not ok_tv:
            return False, msg_tv

        cur.execute(
            """
            INSERT INTO agendamentos (
                venda_id, venda_item_id, cliente_id, servico_id, pacote_sessao_id,
                tipo_origem, data_agendamento, hora_inicio, hora_fim, status,
                devolver_ao_buffer, observacoes, data_alteracao,
                modo_origem, preco_referencia_centavos,
                tipo_atendimento, sala_virtual_disponibilizada,
                data_criacao_registo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'AGENDADO', 0, ?, CURRENT_TIMESTAMP,
                'credito_venda', NULL, ?, ?, datetime('now'))
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
                tdb,
                sdb,
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
    tipo_atendimento: str | None = None,
    sala_virtual_disponibilizada: int | None = None,
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
        if tipo_atendimento is not None:
            ok_tv, msg_tv, tdb, sdb = validar_tipo_atendimento_e_sala(
                tipo_atendimento,
                sala_virtual_disponibilizada,
            )
            if not ok_tv:
                return False, msg_tv
            cur.execute(
                """
                UPDATE agendamentos
                SET tipo_atendimento = ?, sala_virtual_disponibilizada = ?,
                    data_alteracao = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (tdb, sdb, int(ag_id)),
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


def _divisor_valor_unitario_credito_venda_item_cur(
    cur: sqlite3.Cursor, venda_item_id: int, tipo_origem: str | None
) -> int:
    """Unidades para repartir `total_linha_centavos` (crédito cancelamento / base repasse).

    Pacote (`tipo_origem` pacote + natureza Pacote): soma das quantidades oficiais no
    catálogo × quantidade vendida na linha — evita creditar o valor integral do pacote
    por cada sessão cancelada.
    Demais: quantidade da linha (ex.: várias sessões avulsas na mesma linha).
    """
    cur.execute(
        """
        SELECT vi.quantidade, s.natureza, vi.servico_id
        FROM venda_itens vi
        JOIN servicos s ON s.id = vi.servico_id
        WHERE vi.id = ?
        """,
        (int(venda_item_id),),
    )
    r = cur.fetchone()
    if not r:
        return 1
    qty_i, nat, sid_pkg = max(1, int(r[0] or 1)), str(r[1] or "").strip(), int(r[2])
    if str(tipo_origem or "").strip().lower() == "pacote" and nat == "Pacote":
        cur.execute(
            """
            SELECT COALESCE(SUM(sps.quantidade), 0)
            FROM servico_pacote_sessoes sps
            WHERE sps.pacote_servico_id = ?
            """,
            (int(sid_pkg),),
        )
        sum_pq = int(cur.fetchone()[0] or 0)
        return max(1, sum_pq * qty_i)
    return qty_i


def _base_repasse_centavos(cur, ag_id: int) -> tuple[int, int]:
    cur.execute(
        """
        SELECT a.modo_origem, a.preco_referencia_centavos, a.venda_item_id, a.servico_id,
               a.tipo_origem
        FROM agendamentos a WHERE a.id = ?
        """,
        (int(ag_id),),
    )
    r = cur.fetchone()
    if not r:
        return 0, 0
    modo, pref, viid, sid, tpo = str(r[0]), r[1], r[2], int(r[3]), str(r[4] or "")
    if modo == "pre_venda":
        return max(0, int(pref or 0)), sid
    if viid is None:
        return 0, sid
    cur.execute(
        "SELECT total_linha_centavos FROM venda_itens WHERE id = ?",
        (int(viid),),
    )
    r2 = cur.fetchone()
    if not r2:
        return 0, sid
    tlin = int(r2[0])
    divis = _divisor_valor_unitario_credito_venda_item_cur(cur, int(viid), tpo)
    return int(tlin // max(1, divis)), sid


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
        SELECT modo_origem, preco_referencia_centavos, venda_item_id, tipo_origem
        FROM agendamentos WHERE id = ?
        """,
        (int(ag_id),),
    )
    r = cur.fetchone()
    if not r:
        return 0
    modo, pref, viid, tpo = str(r[0]), r[1], r[2], str(r[3] or "")
    if modo == "pre_venda":
        return max(0, int(pref or 0))
    if viid is None:
        return 0
    cur.execute(
        "SELECT total_linha_centavos FROM venda_itens WHERE id = ?",
        (int(viid),),
    )
    r2 = cur.fetchone()
    if not r2:
        return 0
    tlin = int(r2[0])
    divis = _divisor_valor_unitario_credito_venda_item_cur(cur, int(viid), tpo)
    return int(tlin // max(1, divis))


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
            """
            SELECT status, modo_origem, venda_id, tipo_origem
            FROM agendamentos WHERE id = ?
            """,
            (int(ag_id),),
        )
        row = cur.fetchone()
        if not row:
            return False, "❌ Agendamento não encontrado."
        atual, modo_o, vid_chk = str(row[0]), str(row[1]), row[2]
        tipo_o = str(row[3] or "sessao_avulsa")
        if atual == "CANCELADO":
            return False, "❌ Já cancelado."
        if atual == "CONCLUIDO" and n != "CONCLUIDO":
            return False, "❌ Já concluído."
        if n == atual:
            return True, "Sem alteração."
        if n == "CONFIRMADO":
            if atual not in ("AGENDADO", "PRE_AGENDADO"):
                return False, "❌ Só Agendado ou Pré-agendado passam a Confirmado."
        elif n == "AGENDADO":
            if atual != "PRE_AGENDADO":
                return False, "❌ Só Pré-agendado pode passar a Agendado neste fluxo."
        elif n == "REALIZADO_PENDENTE_PGTO":
            if atual not in ("AGENDADO", "CONFIRMADO", "PRE_AGENDADO"):
                return (
                    False,
                    f"❌ Só Agendado, Confirmado ou Pré-agendado podem passar a {ESTADO_AGENDAMENTO_REALIZADO_PENDENTE_LABEL_PT}.",
                )
        elif n == "CONCLUIDO":
            if atual not in ("AGENDADO", "CONFIRMADO", "REALIZADO_PENDENTE_PGTO", "PRE_AGENDADO"):
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
                pac = " — venda do pacote ainda não totalmente liquidada." if tipo_o == "pacote" else ""
                return (
                    True,
                    f"⚠️ Pagamento incompleto ({liq / 100:.2f} € de {esp / 100:.2f} € a liquidar) — "
                    f"estado REALIZADO_PENDENTE_PGTO{pac}",
                )
        elif n == "PRE_AGENDADO":
            # O ecrã CAG permite «Pré-agendado» na lista de estados; antes era sempre rejeitado aqui.
            if atual not in ("AGENDADO", "CONFIRMADO"):
                return False, "❌ Só Agendado ou Confirmado podem voltar a Pré‑agendado neste fluxo."
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
    *,
    tipo_atendimento: str = "presencial",
    sala_virtual_disponibilizada: int | None = None,
    pacote_sessao_id: int | None = None,
) -> tuple[bool, str]:
    """Pré-venda: Sessão, Coworking, Evento; ou **componente de Pacote** (`servico_id` = sessão, `pacote_sessao_id` definido)."""
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
    p_psid: int | None = int(pacote_sessao_id) if pacote_sessao_id is not None else None

    conn = get_connection()
    if not conn:
        return False, "❌ Não foi possível ligar à base de dados."
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM clientes WHERE id = ?", (cid,))
        if cur.fetchone() is None:
            return False, "❌ Cliente não encontrado."
        if p_psid is not None:
            cur.execute(
                """
                SELECT sps.sessao_servico_id, sps.pacote_servico_id, sv.natureza
                FROM servico_pacote_sessoes sps
                JOIN servicos sv ON sv.id = sps.sessao_servico_id
                WHERE sps.id = ?
                """,
                (int(p_psid),),
            )
            rps = cur.fetchone()
            if not rps:
                return False, "❌ Linha de sessão do pacote inválida."
            sess_sid, _pkg_id, snat = int(rps[0]), int(rps[1]), str(rps[2])
            if sess_sid != sid:
                return False, "❌ O serviço seleccionado não corresponde à sessão do pacote."
            if snat != "Sessão":
                return False, "❌ O componente do pacote deve ser uma sessão."
            natureza = "Sessão"
        else:
            cur.execute("SELECT natureza FROM servicos WHERE id = ?", (sid,))
            rnat = cur.fetchone()
            if not rnat:
                return False, "❌ Serviço não encontrado."
            natureza = str(rnat[0])
            if natureza not in ("Sessão", "Coworking", "Evento"):
                if natureza in ("Produto", "Pacote"):
                    return (
                        False,
                        "❌ Neste ecrã a pré-venda só é suportada para Sessão, Coworking e Evento, "
                        "ou para uma **sessão de um Pacote** (indique a linha do pacote no catálogo). "
                        "Para Produto ou venda directa de Pacote, utilize o Painel de Vendas.",
                    )
                return False, "❌ Pré-venda só para Sessão, Coworking ou Evento."
        ok_o, msg_o, tipo = _tipo_origem_para_natureza(natureza, p_psid)
        if not ok_o or tipo is None:
            return False, msg_o

        for colab in colaborador_ids:
            cur.execute("SELECT id FROM colaboradores WHERE id = ?", (int(colab),))
            if cur.fetchone() is None:
                return False, f"❌ Colaborador {colab} não encontrado."

        ok_tv, msg_tv, tdb, sdb = validar_tipo_atendimento_e_sala(
            tipo_atendimento, sala_virtual_disponibilizada
        )
        if not ok_tv:
            return False, msg_tv

        cur.execute(
            """
            INSERT INTO agendamentos (
                venda_id, venda_item_id, cliente_id, servico_id, pacote_sessao_id,
                tipo_origem, data_agendamento, hora_inicio, hora_fim, status,
                devolver_ao_buffer, observacoes, data_alteracao,
                modo_origem, preco_referencia_centavos,
                tipo_atendimento, sala_virtual_disponibilizada,
                data_criacao_registo
            ) VALUES (NULL, NULL, ?, ?, ?, ?, ?, ?, ?, 'AGENDADO', 0, ?, CURRENT_TIMESTAMP,
                'pre_venda', ?, ?, ?, datetime('now'))
            """,
            (
                cid,
                sid,
                p_psid,
                tipo,
                d,
                hi,
                hf,
                (observacoes or "").strip(),
                pr,
                tdb,
                sdb,
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


def listar_agendamentos_elegiveis_associacao_linha_venda(
    *, cliente_id: int, servico_id: int
) -> list[dict[str, Any]]:
    """
    Agendamentos que podem ser associados a uma linha de venda (pré-venda → crédito),
    alinhado a `associar_agendamento_pre_venda_a_item` (exclui cancelado, concluído e RPP).
    """
    return listar_agendamentos(
        cliente_ids=[int(cliente_id)],
        servico_ids=[int(servico_id)],
        status_list=["PRE_AGENDADO", "AGENDADO", "CONFIRMADO"],
    )


def listar_buckets_pacote_com_saldo_disponivel(cliente_id: int) -> list[dict[str, Any]]:
    """Buckets `tipo_origem` pacote com saldo ≥ 1 (para UI de conversão do dia)."""
    out: list[dict[str, Any]] = []
    for b in listar_buckets_credito_cliente(int(cliente_id)):
        if str(b.get("tipo_origem") or "") != "pacote":
            continue
        if int(b.get("saldo") or 0) < 1:
            continue
        if b.get("pacote_sessao_id") is None:
            continue
        out.append(b)
    return out


def agendamento_elegivel_conversao_para_pacote_hoje(
    ag: dict[str, Any] | None,
    *,
    data_referencia: date | None = None,
) -> tuple[bool, str]:
    """
    Regra funcional: uma sessão por operação; `data_agendamento` = hoje;
    não `CONCLUIDO` nem `REALIZADO_PENDENTE_PGTO`; ainda não consumo de pacote.
    """
    ref = (data_referencia or date.today()).isoformat()[:10]
    if not ag:
        return False, "❌ Agendamento inexistente."
    st = str(ag.get("status") or "")
    if st in ("CONCLUIDO", "REALIZADO_PENDENTE_PGTO", "CANCELADO"):
        return (
            False,
            f"❌ Estado não permite converter (exclui Concluído e «{ESTADO_AGENDAMENTO_REALIZADO_PENDENTE_LABEL_PT}»).",
        )
    if str(ag.get("data_agendamento") or "")[:10] != ref:
        return False, "❌ Só é permitido converter agendamentos com data de hoje."
    tpo = str(ag.get("tipo_origem") or "")
    if tpo == "pacote":
        return False, "❌ Este agendamento já é consumo de pacote."
    if tpo not in ("sessao_avulsa", "coworking", "evento"):
        return False, "❌ Só sessões avulsas, coworking ou evento podem ser convertidas."
    return True, ""


def converter_agendamento_avulso_para_consumo_pacote(
    ag_id: int,
    venda_item_id_pacote: int,
    pacote_sessao_id: int,
    *,
    actor: str | None = None,
) -> tuple[bool, str]:
    """
    Liga um agendamento avulso (hoje, estado permitido) ao crédito de uma linha de **Pacote** vendida.
    """
    aid = int(ag_id)
    vi_pac = int(venda_item_id_pacote)
    psid = int(pacote_sessao_id)
    ag = obter_agendamento(aid)
    ok_e, msg_e = agendamento_elegivel_conversao_para_pacote_hoje(ag)
    if not ok_e:
        return False, msg_e
    if not ag:
        return False, "❌ Agendamento não encontrado."

    conn = get_connection()
    if not conn:
        return False, "❌ Não foi possível ligar à base de dados."
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*) FROM repasse_linhas
            WHERE agendamento_id = ?
              AND COALESCE(status_repasse, '') != 'PENDENTE_REPASSE'
            """,
            (aid,),
        )
        if int(cur.fetchone()[0] or 0) > 0:
            return (
                False,
                "❌ Existem linhas de repasse já fora de «PENDENTE_REPASSE» — conversão não permitida.",
            )
        cur.execute(
            """
            DELETE FROM repasse_linhas
            WHERE agendamento_id = ? AND status_repasse = 'PENDENTE_REPASSE'
            """,
            (aid,),
        )
        cur.execute(
            """
            SELECT vi.venda_id, vi.servico_id, s.natureza, v.cliente_id
            FROM venda_itens vi
            JOIN servicos s ON s.id = vi.servico_id
            JOIN vendas v ON v.id = vi.venda_id
            WHERE vi.id = ?
            """,
            (vi_pac,),
        )
        row = cur.fetchone()
        if not row:
            return False, "❌ Linha de venda do pacote não encontrada."
        venda_id, sid_item, natureza, cli_v = int(row[0]), int(row[1]), str(row[2]), int(row[3])
        if natureza != "Pacote":
            return False, "❌ A linha seleccionada não é um pacote."
        if int(ag["cliente_id"]) != cli_v:
            return False, "❌ Cliente do agendamento difere do cliente da venda do pacote."
        ok_s, msg_s, serv_occ = _servico_ocorrencia(cur, vi_pac, psid)
        if not ok_s or serv_occ is None:
            return False, msg_s
        if int(ag["servico_id"]) != int(serv_occ):
            return (
                False,
                "❌ O serviço do agendamento não coincide com o componente do pacote seleccionado.",
            )
        saldo = saldo_bucket(cur, vi_pac, psid)
        if saldo < 1:
            return False, "❌ Sem saldo disponível neste componente do pacote."

        old_tipo = str(ag.get("tipo_origem") or "")
        old_modo = str(ag.get("modo_origem") or "")
        old_vid = ag.get("venda_id")
        old_vi = ag.get("venda_item_id")
        old_ps = ag.get("pacote_sessao_id")
        old_srv = int(ag["servico_id"])

        cur.execute(
            """
            UPDATE agendamentos
            SET venda_id = ?, venda_item_id = ?, pacote_sessao_id = ?,
                tipo_origem = 'pacote', modo_origem = 'credito_venda',
                servico_id = ?, preco_referencia_centavos = NULL,
                data_alteracao = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (venda_id, vi_pac, psid, int(serv_occ), aid),
        )
        _append_ag_hist(
            cur,
            aid,
            "tipo_origem",
            old_tipo,
            "pacote",
            motivo="converter_para_consumo_pacote_hoje",
            actor=actor,
        )
        _append_ag_hist(
            cur,
            aid,
            "venda_item_id",
            str(old_vi) if old_vi is not None else "",
            str(vi_pac),
            motivo="converter_para_consumo_pacote_hoje",
            actor=actor,
        )
        _append_ag_hist(
            cur,
            aid,
            "modo_origem",
            old_modo,
            "credito_venda",
            motivo="converter_para_consumo_pacote_hoje",
            actor=actor,
        )
        if int(serv_occ) != old_srv:
            _append_ag_hist(
                cur,
                aid,
                "servico_id",
                str(old_srv),
                str(int(serv_occ)),
                motivo="converter_para_consumo_pacote_hoje",
                actor=actor,
            )
        conn.commit()
        return True, f"✅ Agendamento #{aid} convertido para consumo do pacote (linha #{vi_pac})."
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao converter: {e}"
    finally:
        conn.close()


def pos_venda_associar_agendamentos_por_linha(
    *,
    venda_id: int,
    cliente_id: int,
    agendamento_ids_por_linha: list[int | None],
) -> list[str]:
    """
    Após `registrar_venda`, para cada linha com `agendamento_id`:
    associa pré-venda à linha de venda correspondente e actualiza estado do agendamento
    (CONCLUIDO se a venda estiver totalmente liquidada; caso contrário REALIZADO_PENDENTE_PGTO).
    """
    from src.modules.venda import listar_venda_item_ids_em_ordem

    out: list[str] = []
    vi_ids = listar_venda_item_ids_em_ordem(int(venda_id))
    if len(agendamento_ids_por_linha) != len(vi_ids):
        out.append(
            f"⚠️ Inconsistência: {len(agendamento_ids_por_linha)} linhas no plano vs "
            f"{len(vi_ids)} itens na venda #{venda_id} — associação ignorada."
        )
        return out

    conn = get_connection()
    if not conn:
        out.append("❌ Sem ligação à BD para pós-processamento da venda.")
        return out
    try:
        cur = conn.cursor()
        esp = total_esperado_liquidacao_venda_centavos(cur, int(venda_id))
        liq = total_liquidado_venda_centavos(cur, int(venda_id))
        venda_totalmente_paga = liq >= esp
    finally:
        conn.close()

    for ag_id_raw, vi_id in zip(agendamento_ids_por_linha, vi_ids, strict=True):
        if ag_id_raw is None:
            continue
        ag_id = int(ag_id_raw)
        ag = obter_agendamento(ag_id)
        if not ag:
            out.append(f"⚠️ Agendamento #{ag_id} não encontrado — ignorado.")
            continue
        if int(ag["cliente_id"]) != int(cliente_id):
            out.append(f"⚠️ Agendamento #{ag_id} não pertence ao cliente da venda — ignorado.")
            continue
        conn2 = get_connection()
        if not conn2:
            out.append("❌ Sem ligação à BD ao validar linha de venda.")
            continue
        try:
            c2 = conn2.cursor()
            c2.execute(
                "SELECT servico_id FROM venda_itens WHERE id = ? AND venda_id = ?",
                (int(vi_id), int(venda_id)),
            )
            rvi = c2.fetchone()
            if not rvi:
                out.append(f"⚠️ Linha de venda #{vi_id} inválida para venda #{venda_id}.")
                continue
            if int(rvi[0]) != int(ag["servico_id"]):
                out.append(
                    f"⚠️ Serviço do agendamento #{ag_id} não coincide com a linha #{vi_id} — ignorado."
                )
                continue
        finally:
            conn2.close()

        modo = str(ag.get("modo_origem") or "")
        if modo == "pre_venda":
            ok_a, msg_a = associar_agendamento_pre_venda_a_item(ag_id, int(vi_id))
            if not ok_a:
                out.append(f"⚠️ Associação ag #{ag_id}: {msg_a}")
                continue
            out.append(f"✅ {msg_a} (ag #{ag_id})")
        else:
            out.append(
                f"ℹ️ Ag #{ag_id} não está em pré-venda ({modo}) — associação automática ignorada."
            )
            continue

        alvo: StatusAgendamento = "CONCLUIDO" if venda_totalmente_paga else "REALIZADO_PENDENTE_PGTO"
        ok_s, msg_s = alterar_status(ag_id, alvo, actor="pos_venda")
        if not ok_s:
            out.append(f"⚠️ Estado pós-venda ag #{ag_id}: {msg_s}")
        else:
            out.append(f"✅ Ag #{ag_id}: {msg_s}")

    return out


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


def _empty_resumo_setor2_proposta() -> dict[str, Any]:
    return {
        "previstos_30d_por_natureza": [],
        "previstos_10d_por_natureza": [],
        "pendente_pgto_por_natureza": [],
        "pendente_pgto_valor_total_centavos": 0,
        "cancelados_60d_total": 0,
    }


def obter_resumo_agendamentos_cliente_setor2_proposta(cliente_id: int) -> dict[str, Any]:
    """
    Setor 2 «Resumo Geral: Agendamentos» — lógica alinhada à Proposta (naturezas + estados).
    """
    cid = int(cliente_id)
    if cid < 1:
        return _empty_resumo_setor2_proposta()
    today = date.today()
    today_s = today.isoformat()
    lim_30 = (today + timedelta(days=30)).isoformat()
    lim_10 = (today + timedelta(days=10)).isoformat()
    lim_60 = (today - timedelta(days=60)).isoformat()

    conn = get_connection()
    if not conn:
        return _empty_resumo_setor2_proposta()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT s.natureza, COUNT(*)
            FROM agendamentos a
            JOIN servicos s ON s.id = a.servico_id
            WHERE a.cliente_id = ?
              AND a.status IN ('PRE_AGENDADO', 'AGENDADO', 'CONFIRMADO')
              AND date(a.data_agendamento) >= date(?)
              AND date(a.data_agendamento) <= date(?)
            GROUP BY s.natureza
            ORDER BY s.natureza COLLATE NOCASE
            """,
            (cid, today_s, lim_30),
        )
        c30 = [(str(r[0]), int(r[1])) for r in cur.fetchall()]

        cur.execute(
            """
            SELECT s.natureza, COUNT(*)
            FROM agendamentos a
            JOIN servicos s ON s.id = a.servico_id
            WHERE a.cliente_id = ?
              AND a.status IN ('PRE_AGENDADO', 'AGENDADO', 'CONFIRMADO')
              AND date(a.data_agendamento) >= date(?)
              AND date(a.data_agendamento) <= date(?)
            GROUP BY s.natureza
            ORDER BY s.natureza COLLATE NOCASE
            """,
            (cid, today_s, lim_10),
        )
        c10 = [(str(r[0]), int(r[1])) for r in cur.fetchall()]

        cur.execute(
            """
            SELECT s.natureza, COUNT(*)
            FROM agendamentos a
            JOIN servicos s ON s.id = a.servico_id
            WHERE a.cliente_id = ? AND a.status = 'REALIZADO_PENDENTE_PGTO'
            GROUP BY s.natureza
            ORDER BY s.natureza COLLATE NOCASE
            """,
            (cid,),
        )
        pend_n = [(str(r[0]), int(r[1])) for r in cur.fetchall()]

        cur.execute(
            """
            SELECT COALESCE(SUM(COALESCE(a.preco_referencia_centavos, 0)), 0)
            FROM agendamentos a
            WHERE a.cliente_id = ? AND a.status = 'REALIZADO_PENDENTE_PGTO'
            """,
            (cid,),
        )
        pend_val = int(cur.fetchone()[0] or 0)

        cur.execute(
            """
            SELECT COUNT(*) FROM agendamentos
            WHERE cliente_id = ?
              AND status = 'CANCELADO'
              AND date(
                COALESCE(
                  nullif(substr(data_alteracao, 1, 10), ''),
                  data_agendamento
                )
              ) >= date(?)
            """,
            (cid, lim_60),
        )
        n_can = int(cur.fetchone()[0] or 0)

        return {
            "previstos_30d_por_natureza": c30,
            "previstos_10d_por_natureza": c10,
            "pendente_pgto_por_natureza": pend_n,
            "pendente_pgto_valor_total_centavos": pend_val,
            "cancelados_60d_total": n_can,
        }
    finally:
        conn.close()


def listar_agendamentos_realizado_pendente_liquidacao_cliente(
    cliente_id: int,
) -> list[dict[str, Any]]:
    """
    Atendimentos com dívida em aberto na venda associada, para liquidação no PDV.

    Inclui:
    - `REALIZADO_PENDENTE_PGTO` (fluxo clássico);
    - `CONCLUIDO` quando a linha está marcada como pagamento parcial (`pagamento_parcial`)
      ou a venda ainda está `parcial` / `pendente` — cobre desalinhamentos e o modo
      «Pagamento Parcial» sem recebimentos previstos.

    Não inclui vendas com `estado_pagamento = 'parcelado'` (pagamento parcelado planeado).
    """
    cid = int(cliente_id)
    if cid < 1:
        return []
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                a.id,
                a.venda_id,
                a.venda_item_id,
                a.servico_id,
                s.nome AS servico_nome,
                a.data_agendamento,
                COALESCE(vi.total_linha_centavos, 0) AS total_linha_centavos
            FROM agendamentos a
            JOIN vendas v ON v.id = a.venda_id
            JOIN servicos s ON s.id = a.servico_id
            LEFT JOIN venda_itens vi ON vi.id = a.venda_item_id
            WHERE a.cliente_id = ?
              AND a.modo_origem = 'credito_venda'
              AND a.venda_id IS NOT NULL
              AND v.estado_pagamento != 'parcelado'
              AND (
                    a.status = 'REALIZADO_PENDENTE_PGTO'
                 OR (
                      a.status = 'CONCLUIDO'
                      AND (
                          COALESCE(vi.pagamento_parcial, 0) = 1
                          OR v.estado_pagamento IN ('parcial', 'pendente')
                      )
                   )
              )
            ORDER BY a.data_agendamento DESC, a.id DESC
            """,
            (cid,),
        )
        out: list[dict[str, Any]] = []
        for r in cur.fetchall():
            ag_id = int(r[0])
            vid = int(r[1])
            vi_id = int(r[2]) if r[2] is not None else None
            sid = int(r[3])
            nome = str(r[4] or "")
            d_ag = str(r[5] or "")
            tlin = int(r[6] or 0)
            aberto = obter_aberto_liquidacao_venda_centavos(vid)
            if aberto < 1:
                continue
            out.append(
                {
                    "agendamento_id": ag_id,
                    "venda_id": vid,
                    "venda_item_id": vi_id,
                    "servico_id": sid,
                    "servico_nome": nome,
                    "data_agendamento": d_ag,
                    "valor_linha_venda_centavos": tlin,
                    "aberto_venda_centavos": aberto,
                }
            )
        return out
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
    "agendamento_elegivel_conversao_para_pacote_hoje",
    "alterar_status",
    "associar_agendamento_pre_venda_a_item",
    "atualizar_agendamento",
    "cancelar_agendamento",
    "converter_agendamento_avulso_para_consumo_pacote",
    "analisar_sessoes_pacote_pendentes_cag",
    "contar_por_status_periodo",
    "contar_pre_venda_futuros",
    "contar_total_sessoes_pacote_pendentes_agendamento",
    "criar_agendamento",
    "criar_agendamento_pre_venda",
    "listar_agendamentos",
    "listar_agendamentos_elegiveis_associacao_linha_venda",
    "listar_agendamentos_realizado_pendente_liquidacao_cliente",
    "listar_opcoes_servicos_adquiridos_pendente_pre_agendamento",
    "listar_buckets_credito_cliente",
    "listar_buckets_pacote_com_saldo_disponivel",
    "minutos_desde_meia_noite",
    "obter_agendamento",
    "obter_resumo_agendamentos_cliente_setor2_proposta",
    "obter_primeiro_item_venda_por_servico",
    "pos_venda_associar_agendamentos_por_linha",
    "promover_agendamentos_realizado_pendente_apos_liquidacao_venda",
    "rotulo_pagamento_venda",
    "saldo_bucket",
    "validar_intervalo_horario",
    "validar_tipo_atendimento_e_sala",
]
