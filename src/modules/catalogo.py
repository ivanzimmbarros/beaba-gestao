"""Catálogo de serviços — Fase 1: Sessão, Produto, Coworking (E06 incremental)."""

from __future__ import annotations

import sqlite3

from src.database.connection import get_connection
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
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, nome, natureza, ativo, descritivo,
                   sessao_duracao_horas, sessao_valor_centavos,
                   produto_tipo, produto_descricao, produto_valor_centavos,
                   produto_origem, produto_repasse_pct_centesimos, produto_repasse_valor_centavos,
                   cowork_sala_nome, cowork_cobranca, cowork_valor_centavos
            FROM servicos
            ORDER BY natureza, nome
            """
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    out: list[dict[str, str | int | float | None]] = []
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
    return out


__all__ = [
    "cadastrar_servico_fase1",
    "centavos_para_texto_euros",
    "euros_para_centavos",
    "listar_itens_catalogo",
]
