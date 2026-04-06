"""Catálogo de serviços — E06: Sessão, Produto, Coworking (Fase 1) + Pacote (Fase 2)."""

from __future__ import annotations

import sqlite3

from src.database.connection import get_connection
from src.modules.colaborador import media_repasse_percentual_servico
from src.modules.constants import NATUREZAS_CATALOGO_FASE1


def euros_para_centavos(valor: float) -> int | None:
    if valor < 0:
        return None
    c = int(round(float(valor) * 100))
    return c if c >= 0 else None


def centavos_para_texto_euros(c: int | None) -> str:
    if c is None:
        return "—"
    return f"{c / 100:.2f} €"


def percentual_para_centesimos_ref(pct: float) -> int | None:
    c = int(round(float(pct) * 100))
    if c < 1 or c > 10000:
        return None
    return c


def repasse_medio_ponderado_pacote(linhas_sessao: list[tuple[int, int]]) -> float | None:
    """
    Média dos % de repasse (0–100) dos colaboradores habilitados,
    ponderada pelas quantidades de cada tipo de sessão no pacote.
    Ignora tipos de sessão sem colaboradores habilitados (sem média).
    """
    total_q = 0
    acc = 0.0
    for sid, q in linhas_sessao:
        q = int(q)
        if q < 1:
            continue
        m = media_repasse_percentual_servico(int(sid))
        if m is None:
            continue
        acc += float(m) * q
        total_q += q
    if total_q <= 0:
        return None
    return acc / total_q


def listar_servicos_sessao_para_pacote() -> list[tuple[int, str, float | None]]:
    """Sessões ativas: id, nome, duração base no catálogo (h)."""
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, nome, sessao_duracao_horas
            FROM servicos
            WHERE ativo = 1 AND natureza = 'Sessão'
            ORDER BY nome
            """
        )
        return [(int(r[0]), str(r[1]), r[2]) for r in cur.fetchall()]
    finally:
        conn.close()


def listar_servicos_produto_para_pacote() -> list[tuple[int, str]]:
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, nome FROM servicos
            WHERE ativo = 1 AND natureza = 'Produto'
            ORDER BY nome
            """
        )
        return [(int(r[0]), str(r[1])) for r in cur.fetchall()]
    finally:
        conn.close()


def _validar_sessao_para_linha_pacote(cur: sqlite3.Cursor, sessao_id: int) -> tuple[bool, str, float | None]:
    cur.execute(
        """
        SELECT natureza, ativo, sessao_duracao_horas
        FROM servicos WHERE id = ?
        """,
        (int(sessao_id),),
    )
    row = cur.fetchone()
    if not row:
        return False, "❌ Sessão inválida no pacote.", None
    nat, atv, sdh = row[0], row[1], row[2]
    if str(nat) != "Sessão" or not atv:
        return False, "❌ Cada linha do pacote deve referenciar uma sessão ativa do catálogo.", None
    return True, "", float(sdh) if sdh is not None else None


def _validar_produto_para_pacote(cur: sqlite3.Cursor, produto_id: int) -> tuple[bool, str]:
    cur.execute("SELECT natureza, ativo FROM servicos WHERE id = ?", (int(produto_id),))
    row = cur.fetchone()
    if not row:
        return False, "❌ Produto inválido no pacote."
    nat, atv = row[0], row[1]
    if str(nat) != "Produto" or not atv:
        return False, "❌ O produto associado deve ser um item ativo de natureza Produto."
    return True, ""


def cadastrar_pacote(
    nome: str,
    descritivo: str,
    ativo: bool,
    linhas_sessao: list[tuple[int, int, float | None]],
    produto_opcional: tuple[int, int] | None,
    repasse_referencia_pct: float,
    valor_venda_euros: float,
) -> tuple[bool, str]:
    """
    `linhas_sessao`: (servico_sessao_id, quantidade, duracao_horas_override ou None).
    Duração efetiva por linha: override > 0, senão duração da sessão no catálogo (obrigatória).
    `produto_opcional`: (produto_servico_id, quantidade) ou None.
    `repasse_referencia_pct`: valor confirmado pelo utilizador (auto-sugestão + editável na UI).
    """
    nome = (nome or "").strip()
    if not nome:
        return False, "❌ O nome do pacote é obrigatório."
    desc = (descritivo or "").strip()
    if not desc:
        return False, "❌ O descritivo é obrigatório."
    if not linhas_sessao:
        return False, "❌ Inclua pelo menos um tipo de sessão no pacote."

    rep_c = percentual_para_centesimos_ref(repasse_referencia_pct)
    if rep_c is None:
        return False, "❌ O repasse médio de referência deve estar entre 0,01% e 100,00%."

    val_c = euros_para_centavos(float(valor_venda_euros))
    if val_c is None or val_c < 1:
        return False, "❌ Indique o valor de venda do pacote (> 0 €)."

    ativo_i = 1 if ativo else 0
    vistos: set[int] = set()
    linhas_norm: list[tuple[int, int, float | None]] = []

    conn = get_connection()
    if not conn:
        return False, "❌ Não foi possível ligar à base de dados."

    try:
        cur = conn.cursor()
        for sid, qty, dh_ov in linhas_sessao:
            sid = int(sid)
            qty = int(qty)
            if sid in vistos:
                return False, "❌ Não repita o mesmo tipo de sessão em linhas separadas — ajuste a quantidade numa única linha."
            vistos.add(sid)
            if qty < 1:
                return False, "❌ Cada quantidade de sessão deve ser ≥ 1."
            ok, msg, base_dh = _validar_sessao_para_linha_pacote(cur, sid)
            if not ok:
                return False, msg
            if dh_ov is not None and float(dh_ov) > 0:
                dh_stored = float(dh_ov)
            else:
                if base_dh is None or float(base_dh) <= 0:
                    return False, "❌ Defina duração em horas na linha ou complete a sessão no catálogo (duração > 0)."
                dh_stored = None
            linhas_norm.append((sid, qty, dh_stored))

        prod_row: tuple[int, int] | None = None
        if produto_opcional is not None:
            pid, pq = int(produto_opcional[0]), int(produto_opcional[1])
            if pq < 1:
                return False, "❌ Quantidade do produto deve ser ≥ 1."
            okp, msgp = _validar_produto_para_pacote(cur, pid)
            if not okp:
                return False, msgp
            prod_row = (pid, pq)

        cur.execute(
            """
            INSERT INTO servicos (
                nome, natureza, ativo, descritivo,
                pacote_valor_venda_centavos, pacote_repasse_ref_pct_centesimos
            ) VALUES (?, 'Pacote', ?, ?, ?, ?)
            """,
            (nome, ativo_i, desc, val_c, rep_c),
        )
        pid_pac = int(cur.lastrowid)
        for ordem, (sid, qty, dh_stored) in enumerate(linhas_norm, start=1):
            cur.execute(
                """
                INSERT INTO servico_pacote_sessoes (
                    pacote_servico_id, sessao_servico_id, quantidade, duracao_horas, ordem
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (pid_pac, sid, qty, dh_stored, ordem),
            )
        if prod_row is not None:
            cur.execute(
                """
                INSERT INTO servico_pacote_produtos (
                    pacote_servico_id, produto_servico_id, quantidade
                ) VALUES (?, ?, ?)
                """,
                (pid_pac, prod_row[0], prod_row[1]),
            )
        conn.commit()
        return True, "✅ Pacote registado no catálogo."
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, "⚠️ Já existe um serviço com este nome."
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao guardar: {e}"
    finally:
        conn.close()


def _detalhe_pacote(cur: sqlite3.Cursor, pacote_id: int, rep_cent: int | None, val_cent: int | None) -> str:
    cur.execute(
        """
        SELECT psi.quantidade,
               COALESCE(psi.duracao_horas, s.sessao_duracao_horas),
               s.nome
        FROM servico_pacote_sessoes psi
        JOIN servicos s ON s.id = psi.sessao_servico_id
        WHERE psi.pacote_servico_id = ?
        ORDER BY psi.ordem
        """,
        (int(pacote_id),),
    )
    parts: list[str] = []
    for qty, dh, nm in cur.fetchall():
        h = dh if dh is not None else 0
        parts.append(f"{qty}× {nm} ({h} h)")
    cur.execute(
        """
        SELECT ppi.quantidade, s.nome
        FROM servico_pacote_produtos ppi
        JOIN servicos s ON s.id = ppi.produto_servico_id
        WHERE ppi.pacote_servico_id = ?
        """,
        (int(pacote_id),),
    )
    for qty, nm in cur.fetchall():
        parts.append(f"+ {qty}× prod. {nm}")
    core = " · ".join(parts) if parts else "—"
    ref = f" · ref. repasse {rep_cent / 100:.2f}%" if rep_cent else ""
    vv = f" · venda {centavos_para_texto_euros(val_cent)}" if val_cent else ""
    return core + ref + vv


def cadastrar_servico_fase1(
    natureza: str,
    nome: str,
    descritivo: str,
    ativo: bool,
    *,
    sessao_duracao_horas: float | None = None,
    sessao_valor_euros: float | None = None,
    produto_tipo: str = "",
    produto_descricao: str = "",
    produto_valor_euros: float | None = None,
    produto_origem: str = "",
    produto_repasse_pct: float | None = None,
    produto_repasse_valor_euros: float | None = None,
    cowork_sala_nome: str = "",
    cowork_cobranca: str = "",
    cowork_valor_euros: float | None = None,
) -> tuple[bool, str]:
    if natureza not in NATUREZAS_CATALOGO_FASE1:
        return False, "❌ Natureza inválida para esta fase do catálogo."

    nome = (nome or "").strip()
    if not nome:
        return False, "❌ O nome do serviço é obrigatório."

    desc = (descritivo or "").strip()
    if not desc:
        return False, "❌ O descritivo do serviço / produto é obrigatório."
    ativo_i = 1 if ativo else 0

    sessao_d: float | None = None
    sessao_vc: int | None = None
    ptipo = ""
    pdesc = ""
    pvc: int | None = None
    porig = ""
    pr_pct: int | None = None
    pr_val: int | None = None
    cws = ""
    cwc = ""
    cwv: int | None = None

    if natureza == "Sessão":
        if sessao_duracao_horas is None or float(sessao_duracao_horas) <= 0:
            return False, "❌ Indique a duração da sessão em horas (> 0)."
        sessao_d = float(sessao_duracao_horas)
        vc = euros_para_centavos(float(sessao_valor_euros or -1))
        if vc is None or vc < 1:
            return False, "❌ Indique o valor por sessão (> 0 €)."
        sessao_vc = vc

    elif natureza == "Produto":
        ptipo = (produto_tipo or "").strip()
        if not ptipo:
            return False, "❌ O tipo do produto é obrigatório."
        pdesc = (produto_descricao or "").strip()
        pvc = euros_para_centavos(float(produto_valor_euros or -1))
        if pvc is None or pvc < 1:
            return False, "❌ Indique o valor de venda do produto (> 0 €)."
        porig = (produto_origem or "").strip()
        if porig not in ("proprio", "repasse"):
            return False, "❌ Indique se o produto é de estoque próprio ou repasse/consignado."
        if porig == "repasse":
            if produto_repasse_pct is not None and float(produto_repasse_pct) > 0:
                pr_pct = int(round(float(produto_repasse_pct) * 100))
                if pr_pct < 1 or pr_pct > 10000:
                    return False, "❌ O percentual de repasse deve estar entre 0,01% e 100,00%."
            elif produto_repasse_valor_euros is not None and float(produto_repasse_valor_euros) > 0:
                pr_val = euros_para_centavos(float(produto_repasse_valor_euros))
                if pr_val is None or pr_val < 1:
                    return False, "❌ Indique um valor de repasse válido."
            else:
                return False, "❌ Em repasse, indique percentual ou valor acordado com o proprietário."

    elif natureza == "Coworking":
        cws = (cowork_sala_nome or "").strip()
        if not cws:
            return False, "❌ O nome da sala é obrigatório."
        cwc = (cowork_cobranca or "").strip()
        if cwc not in ("hora", "dia"):
            return False, "❌ Indique se a cobrança é por hora ou por dia."
        cwv = euros_para_centavos(float(cowork_valor_euros or -1))
        if cwv is None or cwv < 1:
            return False, "❌ Indique o valor (> 0 €)."

    conn = get_connection()
    if not conn:
        return False, "❌ Não foi possível ligar à base de dados."

    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO servicos (
                nome, natureza, ativo, descritivo,
                sessao_duracao_horas, sessao_valor_centavos,
                produto_tipo, produto_descricao, produto_valor_centavos,
                produto_origem, produto_repasse_pct_centesimos, produto_repasse_valor_centavos,
                cowork_sala_nome, cowork_cobranca, cowork_valor_centavos
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nome,
                natureza,
                ativo_i,
                desc,
                sessao_d,
                sessao_vc,
                ptipo,
                pdesc,
                pvc,
                porig,
                pr_pct,
                pr_val,
                cws,
                cwc,
                cwv,
            ),
        )
        conn.commit()
        return True, "✅ Serviço registado no catálogo."
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, "⚠️ Já existe um serviço com este nome."
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao guardar: {e}"
    finally:
        conn.close()


def listar_itens_catalogo() -> list[dict[str, str | int | float | None]]:
    conn = get_connection()
    if not conn:
        return []
    out: list[dict[str, str | int | float | None]] = []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, nome, natureza, ativo, descritivo,
                   sessao_duracao_horas, sessao_valor_centavos,
                   produto_tipo, produto_descricao, produto_valor_centavos,
                   produto_origem, produto_repasse_pct_centesimos, produto_repasse_valor_centavos,
                   cowork_sala_nome, cowork_cobranca, cowork_valor_centavos,
                   pacote_valor_venda_centavos, pacote_repasse_ref_pct_centesimos
            FROM servicos
            ORDER BY natureza, nome
            """
        )
        rows = cur.fetchall()

        for r in rows:
            (
                sid,
                nome,
                natureza,
                ativo,
                descritivo,
                sdh,
                svc,
                ptipo,
                pdesc,
                pvc,
                porig,
                prpct,
                prval,
                cws,
                cwc,
                cwv,
                pvalc,
                prefc,
            ) = r
            detalhe = ""
            if natureza == "Sessão":
                if sdh and svc:
                    detalhe = f"{sdh} h · {centavos_para_texto_euros(svc)}"
                else:
                    detalhe = "Completar no catálogo (ex.: seed sem duração/valor)"
            elif natureza == "Produto":
                orig = "Próprio" if porig == "proprio" else "Repasse" if porig == "repasse" else porig or "—"
                extra = ""
                if prpct:
                    extra = f" · repasse {prpct / 100:.2f}%"
                elif prval:
                    extra = f" · repasse {centavos_para_texto_euros(prval)}"
                detalhe = f"{ptipo} · {centavos_para_texto_euros(pvc)} · {orig}{extra}"
            elif natureza == "Coworking":
                un = "hora" if cwc == "hora" else "dia" if cwc == "dia" else cwc or "—"
                detalhe = f"{cws} · {un} · {centavos_para_texto_euros(cwv)}"
            elif natureza == "Pacote":
                detalhe = _detalhe_pacote(cur, int(sid), prefc, pvalc)

            out.append(
                {
                    "id": sid,
                    "nome": nome,
                    "natureza": natureza,
                    "ativo": "Sim" if ativo else "Não",
                    "descritivo": descritivo or "—",
                    "detalhes": detalhe or "—",
                }
            )
    finally:
        conn.close()
    return out


__all__ = [
    "cadastrar_pacote",
    "cadastrar_servico_fase1",
    "centavos_para_texto_euros",
    "euros_para_centavos",
    "listar_itens_catalogo",
    "listar_servicos_produto_para_pacote",
    "listar_servicos_sessao_para_pacote",
    "percentual_para_centesimos_ref",
    "repasse_medio_ponderado_pacote",
]
