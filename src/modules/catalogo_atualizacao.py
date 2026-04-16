"""Actualização de itens do catálogo (Sessão/Produto/Coworking, Pacote, Evento).

Implementação isolada com import preguiçoso de `catalogo` para evitar ciclos de importação
e garantir que `from src.modules.catalogo import atualizar_*` funcione de forma fiável.
"""

from __future__ import annotations

import sqlite3

from src.database.connection import get_connection
from src.modules.constants import NATUREZAS_CATALOGO_FASE1
from src.modules.validators import parse_data_iso


def _catalogo():
    import src.modules.catalogo as c

    return c


def atualizar_servico_fase1_existente(
    servico_id: int,
    natureza: str,
    nome: str,
    descritivo: str,
    ativo: bool,
    *,
    especialidade_id: int | None = None,
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
    c = _catalogo()
    euros_para_centavos = c.euros_para_centavos

    if natureza not in NATUREZAS_CATALOGO_FASE1:
        return False, "❌ Natureza inválida."
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
        cur.execute("SELECT natureza FROM servicos WHERE id = ?", (int(servico_id),))
        r = cur.fetchone()
        if not r:
            return False, "❌ Serviço não encontrado."
        if str(r[0] or "") != natureza:
            return False, "❌ A natureza do registo não corresponde ao formulário."
        import importlib

        cat = importlib.import_module("src.modules.catalogo")
        ok_e, msg_e, eid_ins = cat._resolver_especialidade_id_para_servico(cur, natureza, especialidade_id)
        if not ok_e:
            return False, msg_e
        cur.execute(
            """
            UPDATE servicos SET
                nome = ?, natureza = ?, ativo = ?, descritivo = ?, especialidade_id = ?,
                sessao_duracao_horas = ?, sessao_valor_centavos = ?,
                produto_tipo = ?, produto_descricao = ?, produto_valor_centavos = ?,
                produto_origem = ?, produto_repasse_pct_centesimos = ?, produto_repasse_valor_centavos = ?,
                cowork_sala_nome = ?, cowork_cobranca = ?, cowork_valor_centavos = ?
            WHERE id = ?
            """,
            (
                nome,
                natureza,
                ativo_i,
                desc,
                eid_ins,
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
                int(servico_id),
            ),
        )
        conn.commit()
        return True, "✅ Serviço actualizado no catálogo."
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, "⚠️ Já existe um serviço com este nome."
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao guardar: {e}"
    finally:
        conn.close()


def atualizar_pacote_existente(
    pacote_id: int,
    nome: str,
    descritivo: str,
    ativo: bool,
    linhas_sessao: list[tuple[int, int, float | None]],
    produto_opcional: tuple[int, int] | None,
    repasse_referencia_pct: float,
    valor_venda_euros: float,
) -> tuple[bool, str]:
    c = _catalogo()
    euros_para_centavos = c.euros_para_centavos
    percentual_para_centesimos_ref = c.percentual_para_centesimos_ref
    _vs = c._validar_sessao_para_linha_pacote
    _vp = c._validar_produto_para_pacote

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
    pid = int(pacote_id)

    conn = get_connection()
    if not conn:
        return False, "❌ Não foi possível ligar à base de dados."
    try:
        cur = conn.cursor()
        cur.execute("SELECT natureza FROM servicos WHERE id = ?", (pid,))
        row = cur.fetchone()
        if not row or str(row[0] or "") != "Pacote":
            return False, "❌ Pacote inválido."

        for sid, qty, dh_ov in linhas_sessao:
            sid = int(sid)
            qty = int(qty)
            if sid in vistos:
                return False, "❌ Não repita o mesmo tipo de sessão em linhas separadas — ajuste a quantidade numa única linha."
            vistos.add(sid)
            if qty < 1:
                return False, "❌ Cada quantidade de sessão deve ser ≥ 1."
            ok, msg, base_dh = _vs(cur, sid)
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
            prid, pq = int(produto_opcional[0]), int(produto_opcional[1])
            if pq < 1:
                return False, "❌ Quantidade do produto deve ser ≥ 1."
            okp, msgp = _vp(cur, prid)
            if not okp:
                return False, msgp
            prod_row = (prid, pq)

        cur.execute(
            """
            UPDATE servicos SET nome = ?, ativo = ?, descritivo = ?,
                pacote_valor_venda_centavos = ?, pacote_repasse_ref_pct_centesimos = ?
            WHERE id = ?
            """,
            (nome, ativo_i, desc, val_c, rep_c, pid),
        )
        cur.execute("DELETE FROM servico_pacote_sessoes WHERE pacote_servico_id = ?", (pid,))
        cur.execute("DELETE FROM servico_pacote_produtos WHERE pacote_servico_id = ?", (pid,))
        for ordem, (sid, qty, dh_stored) in enumerate(linhas_norm, start=1):
            cur.execute(
                """
                INSERT INTO servico_pacote_sessoes (
                    pacote_servico_id, sessao_servico_id, quantidade, duracao_horas, ordem
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (pid, sid, qty, dh_stored, ordem),
            )
        if prod_row is not None:
            cur.execute(
                """
                INSERT INTO servico_pacote_produtos (
                    pacote_servico_id, produto_servico_id, quantidade
                ) VALUES (?, ?, ?)
                """,
                (pid, prod_row[0], prod_row[1]),
            )
        conn.commit()
        return True, "✅ Pacote actualizado no catálogo."
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, "⚠️ Já existe um serviço com este nome."
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao guardar: {e}"
    finally:
        conn.close()


def atualizar_evento_existente(
    evento_id: int,
    nome: str,
    descritivo: str,
    ativo: bool,
    data_evento_iso: str,
    local: str,
    observacoes: str,
    escopo: str,
    preco_crianca_euros: float,
    preco_adulto_euros: float,
    desconto_filho_adicional_euros: float,
    participantes: list[tuple[str, int | None, str, str, float | None, float | None]],
) -> tuple[bool, str]:
    c = _catalogo()
    euros_para_centavos = c.euros_para_centavos
    percentual_para_centesimos_ref = c.percentual_para_centesimos_ref

    nome = (nome or "").strip()
    if not nome:
        return False, "❌ O nome do evento é obrigatório."
    desc = (descritivo or "").strip()
    if not desc:
        return False, "❌ O descritivo é obrigatório."
    d_iso = (data_evento_iso or "").strip()[:10]
    if not parse_data_iso(d_iso):
        return False, "❌ Indique a data do evento (formato AAAA-MM-DD)."
    loc = (local or "").strip()
    if not loc:
        return False, "❌ O local de realização é obrigatório."
    obs = (observacoes or "").strip()
    esc = (escopo or "").strip()
    if esc not in ("interno", "convidado"):
        return False, "❌ Indique se o evento é interno ou com convidado (parcerias externas)."
    pcc = euros_para_centavos(float(preco_crianca_euros))
    pca = euros_para_centavos(float(preco_adulto_euros))
    if pcc is None or pcc < 1 or pca is None or pca < 1:
        return False, "❌ Os preços de venda (criança e adulto) devem ser > 0 €."
    dfa = euros_para_centavos(float(desconto_filho_adicional_euros))
    if dfa is None or dfa < 0:
        return False, "❌ O desconto por filho adicional não pode ser negativo."
    if not participantes:
        return False, "❌ Inclua pelo menos um participante (colaborador ou parceiro) com o respetivo repasse."
    ativo_i = 1 if ativo else 0
    eid = int(evento_id)

    conn = get_connection()
    if not conn:
        return False, "❌ Não foi possível ligar à base de dados."
    try:
        cur = conn.cursor()
        cur.execute("SELECT natureza FROM servicos WHERE id = ?", (eid,))
        row = cur.fetchone()
        if not row or str(row[0] or "") != "Evento":
            return False, "❌ Evento inválido."

        vistos_colab: set[int] = set()
        linhas_db: list[tuple[str, int | None, str, int | None, int | None]] = []
        for tipo, cid, pnome, modo, pct, veur in participantes:
            tipo = (tipo or "").strip()
            if tipo not in ("colaborador", "parceiro"):
                return False, "❌ Tipo de participante inválido."
            modo = (modo or "").strip()
            if modo not in ("percentual", "valor"):
                return False, "❌ Indique repasse em percentual ou valor para cada participante."
            colab_id: int | None = None
            pn = (pnome or "").strip()
            if tipo == "colaborador":
                if cid is None:
                    return False, "❌ Selecione o colaborador em cada linha de participante."
                colab_id = int(cid)
                if colab_id in vistos_colab:
                    return False, "❌ Não repita o mesmo colaborador em linhas separadas."
                vistos_colab.add(colab_id)
                cur.execute("SELECT id FROM colaboradores WHERE id = ?", (colab_id,))
                if not cur.fetchone():
                    return False, "❌ Colaborador inválido na lista de participantes."
                pn = ""
            else:
                if not pn:
                    return False, "❌ Indique o nome do parceiro externo."
                colab_id = None
            rpct: int | None = None
            rval: int | None = None
            if modo == "percentual":
                if pct is None:
                    return False, "❌ Indique o percentual de repasse."
                rpct = percentual_para_centesimos_ref(float(pct))
                if rpct is None:
                    return False, "❌ Percentual de repasse deve estar entre 0,01% e 100,00%."
            else:
                if veur is None:
                    return False, "❌ Indique o valor de repasse acordado."
                rval = euros_para_centavos(float(veur))
                if rval is None or rval < 1:
                    return False, "❌ Valor de repasse inválido."
            linhas_db.append((tipo, colab_id, pn, rpct, rval))

        cur.execute(
            """
            UPDATE servicos SET nome = ?, ativo = ?, descritivo = ?,
                evento_data = ?, evento_local = ?, evento_observacoes = ?, evento_escopo = ?,
                evento_preco_crianca_centavos = ?, evento_preco_adulto_centavos = ?,
                evento_desconto_filho_adicional_centavos = ?
            WHERE id = ?
            """,
            (nome, ativo_i, desc, d_iso, loc, obs, esc, pcc, pca, dfa, eid),
        )
        cur.execute("DELETE FROM servico_evento_participantes WHERE evento_servico_id = ?", (eid,))
        for ordem, (tipo, colab_id, pn, rpct, rval) in enumerate(linhas_db, start=1):
            cur.execute(
                """
                INSERT INTO servico_evento_participantes (
                    evento_servico_id, tipo, colaborador_id, parceiro_nome,
                    repasse_pct_centesimos, repasse_valor_centavos, ordem
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (eid, tipo, colab_id, pn, rpct, rval, ordem),
            )
        conn.commit()
        return True, "✅ Evento actualizado no catálogo."
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, "⚠️ Já existe um serviço com este nome."
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao guardar: {e}"
    finally:
        conn.close()


__all__ = [
    "atualizar_evento_existente",
    "atualizar_pacote_existente",
    "atualizar_servico_fase1_existente",
]
