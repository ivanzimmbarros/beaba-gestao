"""Catálogo de serviços — E06: Fases 1–3 (Sessão, Produto, Coworking, Pack, Evento)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from src.database.connection import get_connection
from src.modules.colaborador import media_repasse_percentual_servico
from src.modules.constants import (
    ESPECIALIDADE_PADRAO_NOME,
    NATUREZA_PACK,
    NATUREZAS_CATALOGO_FASE1,
    NATUREZAS_CATALOGO_FASE3,
    canon_natureza_catalogo,
)
from src.modules.validators import parse_data_iso

MSG_REGISTRO_DUPLICADO = "Não é possível concluir a operação. Registro já cadastrado."
CAT_MSG_SUCESSO = "Catálogo atualizado com sucesso"


def _notify_cloud_sync() -> None:
    try:
        from scripts.sync_trigger import notify_data_changed

        notify_data_changed()
    except Exception:
        pass


def _audit_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_audit_ts(iso: str | None) -> str:
    raw = (iso or "").strip()
    if not raw:
        return "—"
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return raw


def _existe_nome_ci(
    cur: sqlite3.Cursor,
    table: str,
    column: str,
    nome: str,
    *,
    exclude_id: int | None = None,
    extra_sql: str = "",
    extra_params: tuple[object, ...] = (),
) -> bool:
    nm = (nome or "").strip()
    if not nm:
        return False
    sql = (
        f"SELECT 1 FROM {table} WHERE LOWER(TRIM({column})) = LOWER(TRIM(?))"
        f"{extra_sql} LIMIT 1"
    )
    params: list[object] = [nm, *extra_params]
    if exclude_id is not None:
        sql = (
            f"SELECT 1 FROM {table} WHERE LOWER(TRIM({column})) = LOWER(TRIM(?))"
            f" AND id != ?{extra_sql} LIMIT 1"
        )
        params = [nm, int(exclude_id), *extra_params]
    cur.execute(sql, params)
    return cur.fetchone() is not None


def _ensure_catalogo_naturezas_seed(cur: sqlite3.Cursor) -> None:
    for i, nat in enumerate(NATUREZAS_CATALOGO_FASE3):
        cur.execute(
            """
            INSERT OR IGNORE INTO catalogo_naturezas (nome, ativo, ordem)
            VALUES (?, 1, ?)
            """,
            (nat, i),
        )


def listar_naturezas_catalogo() -> list[dict[str, int | str]]:
    conn = get_connection()
    if not conn:
        return [{"id": 0, "nome": n} for n in NATUREZAS_CATALOGO_FASE3]
    try:
        cur = conn.cursor()
        _ensure_catalogo_naturezas_seed(cur)
        conn.commit()
        cur.execute(
            """
            SELECT id, nome FROM catalogo_naturezas
            WHERE ativo = 1
            ORDER BY ordem, nome COLLATE NOCASE
            """
        )
        rows = [{"id": int(r[0]), "nome": canon_natureza_catalogo(str(r[1]))} for r in cur.fetchall()]
        return rows or [{"id": 0, "nome": n} for n in NATUREZAS_CATALOGO_FASE3]
    except Exception:
        return [{"id": 0, "nome": n} for n in NATUREZAS_CATALOGO_FASE3]
    finally:
        conn.close()


def salvar_natureza_catalogo(
    nome: str, *, natureza_id: int | None = None
) -> tuple[bool, str]:
    nm = (nome or "").strip()
    if not nm:
        return False, "❌ O nome da natureza é obrigatório."
    conn = get_connection()
    if not conn:
        return False, "❌ Não foi possível ligar à base de dados."
    try:
        cur = conn.cursor()
        _ensure_catalogo_naturezas_seed(cur)
        if _existe_nome_ci(cur, "catalogo_naturezas", "nome", nm, exclude_id=natureza_id):
            conn.rollback()
            return False, MSG_REGISTRO_DUPLICADO
        if natureza_id:
            cur.execute("SELECT nome FROM catalogo_naturezas WHERE id = ?", (int(natureza_id),))
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return False, "❌ Natureza não encontrada."
            old = canon_natureza_catalogo(str(row[0]))
            new = canon_natureza_catalogo(nm)
            cur.execute("UPDATE catalogo_naturezas SET nome = ? WHERE id = ?", (new, int(natureza_id)))
            if old != new:
                cur.execute(
                    "UPDATE especialidades SET natureza = ? WHERE natureza = ?",
                    (new, old),
                )
                cur.execute(
                    "UPDATE servicos SET natureza = ? WHERE natureza = ?",
                    (new, old),
                )
        else:
            cur.execute(
                "INSERT INTO catalogo_naturezas (nome, ativo, ordem) VALUES (?, 1, 999)",
                (canon_natureza_catalogo(nm),),
            )
            nat_ins = canon_natureza_catalogo(nm)
            cur.execute(
                """
                INSERT OR IGNORE INTO especialidades (natureza, nome, descritivo, ativo, ordem)
                VALUES (?, ?, '', 1, 0)
                """,
                (nat_ins, ESPECIALIDADE_PADRAO_NOME),
            )
        conn.commit()
        _notify_cloud_sync()
        return True, CAT_MSG_SUCESSO
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, MSG_REGISTRO_DUPLICADO
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao guardar: {e}"
    finally:
        conn.close()


def salvar_especialidade_catalogo(
    natureza: str,
    nome: str,
    *,
    especialidade_id: int | None = None,
    descritivo: str = "",
) -> tuple[bool, str]:
    nat = canon_natureza_catalogo(natureza)
    if not nat:
        return False, "❌ A selecção da natureza é obrigatória para cadastrar uma nova especialidade."
    nm = (nome or "").strip()
    if not nm:
        return False, "❌ O nome da especialidade é obrigatório."
    desc = (descritivo or "").strip()
    conn = get_connection()
    if not conn:
        return False, "❌ Não foi possível ligar à base de dados."
    try:
        cur = conn.cursor()
        extra = " AND natureza = ?"
        if _existe_nome_ci(
            cur,
            "especialidades",
            "nome",
            nm,
            exclude_id=especialidade_id,
            extra_sql=extra,
            extra_params=(nat,),
        ):
            conn.rollback()
            return False, MSG_REGISTRO_DUPLICADO
        if especialidade_id:
            cur.execute(
                """
                UPDATE especialidades
                SET natureza = ?, nome = ?, descritivo = ?
                WHERE id = ?
                """,
                (nat, nm, desc, int(especialidade_id)),
            )
            if cur.rowcount < 1:
                conn.rollback()
                return False, "❌ Especialidade não encontrada."
        else:
            cur.execute(
                """
                INSERT INTO especialidades (natureza, nome, descritivo, ativo, ordem)
                VALUES (?, ?, ?, 1, 0)
                """,
                (nat, nm, desc),
            )
        conn.commit()
        _notify_cloud_sync()
        return True, CAT_MSG_SUCESSO
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, MSG_REGISTRO_DUPLICADO
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao guardar: {e}"
    finally:
        conn.close()


def _resolver_especialidade_id_para_servico(
    cur: sqlite3.Cursor, natureza: str, especialidade_id: int | None
) -> tuple[bool, str, int]:
    """Garante linhas «Geral» por natureza canónica; valida ou usa especialidade explícita."""
    pad = ESPECIALIDADE_PADRAO_NOME
    for nat in NATUREZAS_CATALOGO_FASE3:
        cur.execute(
            """
            INSERT OR IGNORE INTO especialidades (natureza, nome, descritivo, ativo, ordem)
            VALUES (?, ?, '', 1, 0)
            """,
            (nat, pad),
        )
    if especialidade_id is None:
        cur.execute(
            "SELECT id FROM especialidades WHERE natureza = ? AND nome = ? LIMIT 1",
            (natureza, pad),
        )
        r = cur.fetchone()
        if not r:
            return False, "❌ Especialidade padrão em falta para esta natureza.", 0
        return True, "", int(r[0])
    cur.execute(
        "SELECT id, natureza, ativo FROM especialidades WHERE id = ?",
        (int(especialidade_id),),
    )
    r = cur.fetchone()
    if not r:
        return False, "❌ Especialidade inválida.", 0
    if not int(r[2] or 0):
        return False, "❌ Especialidade inativa.", 0
    if str(r[1]) != natureza:
        return False, "❌ A especialidade não pertence à natureza seleccionada.", 0
    return True, "", int(r[0])


def listar_especialidades_por_natureza(natureza: str) -> list[dict[str, int | str | bool]]:
    """Especialidades activas de uma natureza (ordem, nome)."""
    nat = (natureza or "").strip()
    if not nat:
        return []
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, nome, descritivo, ativo, ordem
            FROM especialidades
            WHERE natureza = ? AND ativo = 1
            ORDER BY ordem, nome
            """,
            (nat,),
        )
        return [
            {
                "id": int(rid),
                "nome": str(nm or ""),
                "descritivo": str(ds or ""),
                "ativo": bool(av),
                "ordem": int(ordem or 0),
            }
            for rid, nm, ds, av, ordem in cur.fetchall()
        ]
    finally:
        conn.close()


def cadastrar_especialidade(
    natureza: str, nome: str, descritivo: str = "", *, ativo: bool = True, ordem: int = 0
) -> tuple[bool, str]:
    """Nova especialidade sob uma natureza (nome único por natureza)."""
    nat = (natureza or "").strip()
    if nat not in NATUREZAS_CATALOGO_FASE3:
        return False, "❌ Natureza inválida para especialidade."
    nm = (nome or "").strip()
    if not nm:
        return False, "❌ O nome da especialidade é obrigatório."
    desc = (descritivo or "").strip()
    ativo_i = 1 if ativo else 0
    ord_v = int(ordem)
    conn = get_connection()
    if not conn:
        return False, "❌ Não foi possível ligar à base de dados."
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO especialidades (natureza, nome, descritivo, ativo, ordem)
            VALUES (?, ?, ?, ?, ?)
            """,
            (nat, nm, desc, ativo_i, ord_v),
        )
        conn.commit()
        _notify_cloud_sync()
        return True, "✅ Especialidade registada."
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, "⚠️ Já existe uma especialidade com este nome nesta natureza."
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao guardar: {e}"
    finally:
        conn.close()


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

        if _existe_nome_ci(cur, "servicos", "nome", nome):
            conn.rollback()
            return False, MSG_REGISTRO_DUPLICADO
        ok_e, msg_e, eid_pac = _resolver_especialidade_id_para_servico(cur, NATUREZA_PACK, None)
        if not ok_e:
            return False, msg_e
        ts = _audit_now_iso()
        cur.execute(
            """
            INSERT INTO servicos (
                nome, natureza, ativo, descritivo,
                pacote_valor_venda_centavos, pacote_repasse_ref_pct_centesimos,
                especialidade_id, criado_em, alterado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (nome, NATUREZA_PACK, ativo_i, desc, val_c, rep_c, eid_pac, ts, ts),
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
        _notify_cloud_sync()
        return True, CAT_MSG_SUCESSO
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, MSG_REGISTRO_DUPLICADO
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao guardar: {e}"
    finally:
        conn.close()


def cadastrar_evento(
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
    """
    `participantes`: lista de
    (tipo 'colaborador'|'parceiro', colaborador_id|None, parceiro_nome,
     modo_repasse 'percentual'|'valor', pct|None, valor_euros|None).
    """
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
    vistos_colab: set[int] = set()
    linhas_db: list[tuple[str, int | None, str, int | None, int | None]] = []

    conn = get_connection()
    if not conn:
        return False, "❌ Não foi possível ligar à base de dados."

    try:
        cur = conn.cursor()
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

        ok_e, msg_e, eid_evt = _resolver_especialidade_id_para_servico(cur, "Evento", None)
        if not ok_e:
            return False, msg_e
        cur.execute(
            """
            INSERT INTO servicos (
                nome, natureza, ativo, descritivo,
                evento_data, evento_local, evento_observacoes, evento_escopo,
                evento_preco_crianca_centavos, evento_preco_adulto_centavos,
                evento_desconto_filho_adicional_centavos,
                especialidade_id
            ) VALUES (?, 'Evento', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (nome, ativo_i, desc, d_iso, loc, obs, esc, pcc, pca, dfa, eid_evt),
        )
        eid = int(cur.lastrowid)
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
        _notify_cloud_sync()
        return True, "✅ Evento registado no catálogo."
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, "⚠️ Já existe um serviço com este nome."
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao guardar: {e}"
    finally:
        conn.close()


def _detalhe_evento(cur: sqlite3.Cursor, evento_id: int) -> str:
    cur.execute(
        """
        SELECT evento_data, evento_local, evento_escopo,
               evento_preco_crianca_centavos, evento_preco_adulto_centavos,
               evento_desconto_filho_adicional_centavos
        FROM servicos WHERE id = ?
        """,
        (int(evento_id),),
    )
    er = cur.fetchone()
    if not er:
        return "—"
    ed, el, es, pcc, pca, dfa = er
    esc_l = "Interno" if es == "interno" else "Com convidado" if es == "convidado" else str(es or "—")
    preços = f"c:{centavos_para_texto_euros(pcc)} a:{centavos_para_texto_euros(pca)} desc.filho:{centavos_para_texto_euros(dfa)}"
    cur.execute(
        """
        SELECT sep.tipo, sep.parceiro_nome, c.nome, sep.repasse_pct_centesimos, sep.repasse_valor_centavos
        FROM servico_evento_participantes sep
        LEFT JOIN colaboradores c ON c.id = sep.colaborador_id
        WHERE sep.evento_servico_id = ?
        ORDER BY sep.ordem
        """,
        (int(evento_id),),
    )
    pp: list[str] = []
    for t, pnom, cnom, rpc, rvl in cur.fetchall():
        if t == "colaborador":
            label = (cnom or "?").strip()
        else:
            label = (pnom or "?").strip()
        if rpc:
            pp.append(f"{label} ({rpc / 100:.2f}%)")
        elif rvl:
            pp.append(f"{label} ({centavos_para_texto_euros(rvl)})")
        else:
            pp.append(label)
    part = "; ".join(pp) if pp else "—"
    return f"{ed or '—'} · {el or '—'} · {esc_l} · {preços} · [{part}]"


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
    cadastrado_por: str = "",
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
        if _existe_nome_ci(cur, "servicos", "nome", nome):
            conn.rollback()
            return False, MSG_REGISTRO_DUPLICADO
        ok_e, msg_e, eid_ins = _resolver_especialidade_id_para_servico(cur, natureza, especialidade_id)
        if not ok_e:
            conn.rollback()
            return False, msg_e
        ts = _audit_now_iso()
        cur.execute(
            """
            INSERT INTO servicos (
                nome, natureza, ativo, descritivo, especialidade_id,
                sessao_duracao_horas, sessao_valor_centavos,
                produto_tipo, produto_descricao, produto_valor_centavos,
                produto_origem, produto_repasse_pct_centesimos, produto_repasse_valor_centavos,
                cowork_sala_nome, cowork_cobranca, cowork_valor_centavos,
                cadastrado_por, criado_em, alterado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nome,
                canon_natureza_catalogo(natureza),
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
                (cadastrado_por or "").strip(),
                ts,
                ts,
            ),
        )
        conn.commit()
        _notify_cloud_sync()
        return True, CAT_MSG_SUCESSO
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, MSG_REGISTRO_DUPLICADO
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
            SELECT s.id, s.nome, s.natureza, s.ativo, s.descritivo,
                   COALESCE(e.nome, '') AS especialidade_nome,
                   s.sessao_duracao_horas, s.sessao_valor_centavos,
                   s.produto_tipo, s.produto_descricao, s.produto_valor_centavos,
                   s.produto_origem, s.produto_repasse_pct_centesimos, s.produto_repasse_valor_centavos,
                   s.cowork_sala_nome, s.cowork_cobranca, s.cowork_valor_centavos,
                   s.pacote_valor_venda_centavos, s.pacote_repasse_ref_pct_centesimos,
                   s.evento_data, s.evento_local, s.evento_observacoes, s.evento_escopo,
                   s.evento_preco_crianca_centavos, s.evento_preco_adulto_centavos,
                   s.evento_desconto_filho_adicional_centavos,
                   s.cadastrado_por, s.criado_em, s.alterado_por, s.alterado_em
            FROM servicos s
            LEFT JOIN especialidades e ON e.id = s.especialidade_id
            ORDER BY s.natureza, e.nome, s.nome
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
                esp_nome,
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
                _edata,
                _eloc,
                _eobs,
                _eesc,
                _epcc,
                _epca,
                _edfa,
                cad_por,
                criado_em,
                alt_por,
                alterado_em,
            ) = r
            natureza = canon_natureza_catalogo(str(natureza))
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
            elif canon_natureza_catalogo(str(natureza)) == NATUREZA_PACK:
                detalhe = _detalhe_pacote(cur, int(sid), prefc, pvalc)
            elif natureza == "Evento":
                detalhe = _detalhe_evento(cur, int(sid))

            v_cent: int | None = None
            if natureza == "Sessão":
                v_cent = int(svc) if svc is not None else None
            elif natureza == "Produto":
                v_cent = int(pvc) if pvc is not None else None
            elif natureza == "Coworking":
                v_cent = int(cwv) if cwv is not None else None
            elif canon_natureza_catalogo(str(natureza)) == NATUREZA_PACK:
                v_cent = int(pvalc) if pvalc is not None else None
            elif natureza == "Evento":
                ea = int(_epca) if _epca is not None else None
                ec = int(_epcc) if _epcc is not None else None
                if ea is not None and ea > 0:
                    v_cent = ea
                elif ec is not None and ec > 0:
                    v_cent = ec
                else:
                    v_cent = None
            valor_venda_txt = (
                centavos_para_texto_euros(v_cent) if v_cent is not None and v_cent > 0 else "—"
            )

            ult_ts = (alterado_em or criado_em or "").strip()
            ult_user = (alt_por or cad_por or "").strip()
            out.append(
                {
                    "id": sid,
                    "nome": nome,
                    "valor_venda": valor_venda_txt,
                    "natureza": natureza,
                    "especialidade": str(esp_nome or "") or "—",
                    "ativo": "Sim" if ativo else "Não",
                    "descritivo": descritivo or "—",
                    "detalhes": detalhe or "—",
                    "cadastrado_por": (cad_por or "").strip() or "—",
                    "ultima_alteracao": _format_audit_ts(ult_ts),
                    "ultima_alteracao_por": ult_user or "—",
                }
            )
    finally:
        conn.close()
    return out


def obter_duracao_referencia_agendamento_horas(servico_id: int) -> float:
    """
    Duração em horas definida no catálogo para cálculo de hora fim (CAG / agendamentos).
    Usa `sessao_duracao_horas` quando preenchida; caso contrário 1,0 h (mínimo 0,25 h, máximo 24 h).
    """
    sid = int(servico_id)
    conn = get_connection()
    if not conn:
        return 1.0
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT sessao_duracao_horas FROM servicos WHERE id = ? AND ativo = 1",
            (sid,),
        )
        row = cur.fetchone()
        if not row or row[0] is None:
            return 1.0
        h = float(row[0])
        if h <= 0:
            return 1.0
        return max(0.25, min(24.0, h))
    finally:
        conn.close()


def listar_sessoes_do_pacote_catalogo(pacote_servico_id: int) -> list[dict[str, str | int]]:
    """Sessões componentes definidas no catálogo para o serviço Pacote `pacote_servico_id`."""
    pid = int(pacote_servico_id)
    conn = get_connection()
    if not conn:
        return []
    out: list[dict[str, str | int]] = []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT sps.id, sps.sessao_servico_id, sps.ordem, sps.quantidade, sv.nome AS sessao_nome,
                   COALESCE(NULLIF(TRIM(sv.descritivo), ''), '') AS sessao_descritivo
            FROM servico_pacote_sessoes sps
            JOIN servicos sv ON sv.id = sps.sessao_servico_id
            WHERE sps.pacote_servico_id = ?
            ORDER BY sps.ordem, sps.id
            """,
            (pid,),
        )
        for rid, ssid, ordem, qty, snm, sdesc in cur.fetchall():
            out.append(
                {
                    "pacote_sessao_id": int(rid),
                    "sessao_servico_id": int(ssid),
                    "ordem": int(ordem),
                    "quantidade": int(qty),
                    "sessao_nome": str(snm or ""),
                    "sessao_descritivo": str(sdesc or "").strip(),
                }
            )
    finally:
        conn.close()
    return out


def listar_servicos_para_venda() -> list[dict[str, str | int]]:
    """Serviços ativos de todas as naturezas (inclui Pacote e Evento) para o Painel de Vendas."""
    conn = get_connection()
    if not conn:
        return []
    out: list[dict[str, str | int]] = []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT s.id, s.nome, s.natureza, s.descritivo,
                   s.especialidade_id, COALESCE(e.nome, '') AS especialidade_nome
            FROM servicos s
            LEFT JOIN especialidades e ON e.id = s.especialidade_id
            WHERE s.ativo = 1
            ORDER BY s.natureza, e.nome, s.nome
            """
        )
        for sid, nome, nat, desc, eid, enm in cur.fetchall():
            out.append(
                {
                    "id": int(sid),
                    "nome": str(nome),
                    "natureza": str(nat or ""),
                    "descritivo": str(desc or ""),
                    "especialidade_id": int(eid) if eid is not None else None,
                    "especialidade": str(enm or ""),
                }
            )
    finally:
        conn.close()
    return out


def resolver_snapshot_venda(
    servico_id: int,
    *,
    evento_preco: str | None = None,
    is_bonus: bool = False,
) -> tuple[bool, str, dict[str, str | int]]:
    """
    Preço e texto de venda a partir do catálogo (serviço ativo).
    Evento: exige `evento_preco` em ('adulto', 'crianca').
    Bónus: `preco_unitario_centavos` = 0 (mantém `servico_id` na linha).
    """
    conn = get_connection()
    if not conn:
        return False, "❌ Não foi possível ligar à base de dados.", {}
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, nome, natureza, ativo, descritivo,
                   sessao_valor_centavos,
                   produto_valor_centavos,
                   cowork_cobranca, cowork_valor_centavos,
                   pacote_valor_venda_centavos,
                   evento_preco_crianca_centavos, evento_preco_adulto_centavos
            FROM servicos WHERE id = ?
            """,
            (int(servico_id),),
        )
        row = cur.fetchone()
        if not row:
            return False, "❌ Serviço não encontrado.", {}
        (
            sid,
            nome,
            natureza,
            ativo,
            descritivo,
            svc_sess,
            svc_prod,
            cw_cob,
            cw_val,
            pac_val,
            ev_cc,
            ev_ca,
        ) = row
        if not ativo:
            return False, "❌ Serviço inativo — não pode ser vendido.", {}
        nat = str(natureza or "")
        desc = (descritivo or "").strip()
        unidade = "unidade"
        preco: int | None = None
        if nat == "Sessão":
            unidade = "sessão"
            preco = int(svc_sess) if svc_sess is not None else None
        elif nat == "Produto":
            unidade = "un"
            preco = int(svc_prod) if svc_prod is not None else None
        elif nat == "Coworking":
            unidade = "hora" if cw_cob == "hora" else "dia" if cw_cob == "dia" else str(cw_cob or "unidade")
            preco = int(cw_val) if cw_val is not None else None
        elif canon_natureza_catalogo(str(nat)) == NATUREZA_PACK:
            unidade = "pacote"
            preco = int(pac_val) if pac_val is not None else None
        elif nat == "Evento":
            unidade = "ingresso"
            ep = (evento_preco or "").strip()
            if ep == "adulto":
                preco = int(ev_ca) if ev_ca is not None else None
            elif ep == "crianca":
                preco = int(ev_cc) if ev_cc is not None else None
            else:
                return (
                    False,
                    "❌ Para serviço Evento, indique preço adulto ou criança.",
                    {},
                )
        else:
            return False, f"❌ Natureza «{nat}» não suportada na venda.", {}

        if preco is None or preco < 0:
            return False, "❌ Preço de venda incompleto no catálogo para este item.", {}

        if is_bonus:
            preco = 0

        snap: dict[str, str | int] = {
            "servico_id": int(sid),
            "natureza": nat,
            "nome": str(nome),
            "descricao": desc,
            "unidade_medida": unidade,
            "preco_unitario_centavos": int(preco),
        }
        return True, "", snap
    finally:
        conn.close()


def obter_servico_para_formulario(servico_id: int) -> dict | None:
    """
    Carrega um serviço para preencher o formulário do catálogo (todos os tipos).
    Chaves devolvidas alinhadas com `render_page_catalogo` / cadastro.
    """
    sid = int(servico_id)
    conn = get_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT s.id, s.nome, s.natureza, s.ativo, s.descritivo,
                   s.especialidade_id, COALESCE(e.nome, '') AS especialidade_nome,
                   s.sessao_duracao_horas, s.sessao_valor_centavos,
                   s.produto_tipo, s.produto_descricao, s.produto_valor_centavos,
                   s.produto_origem, s.produto_repasse_pct_centesimos, s.produto_repasse_valor_centavos,
                   s.cowork_sala_nome, s.cowork_cobranca, s.cowork_valor_centavos,
                   s.pacote_valor_venda_centavos, s.pacote_repasse_ref_pct_centesimos,
                   s.evento_data, s.evento_local, s.evento_observacoes, s.evento_escopo,
                   s.evento_preco_crianca_centavos, s.evento_preco_adulto_centavos,
                   s.evento_desconto_filho_adicional_centavos
            FROM servicos s
            LEFT JOIN especialidades e ON e.id = s.especialidade_id
            WHERE s.id = ?
            """,
            (sid,),
        )
        row = cur.fetchone()
        if not row:
            return None
        (
            rid,
            nome,
            natureza,
            ativo,
            descritivo,
            esp_id,
            esp_nome,
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
            edata,
            eloc,
            eobs,
            eesc,
            epcc,
            epca,
            edfa,
        ) = row
        nat = str(natureza or "")
        out: dict = {
            "id": int(rid),
            "nome": str(nome or ""),
            "natureza": nat,
            "ativo": bool(ativo),
            "descritivo": str(descritivo or ""),
            "especialidade_id": int(esp_id) if esp_id is not None else None,
            "especialidade_nome": str(esp_nome or ""),
        }
        if nat == "Sessão":
            out["sessao_duracao_horas"] = float(sdh) if sdh is not None else 1.0
            out["sessao_valor_euros"] = (int(svc) / 100.0) if svc is not None else 45.0
        elif nat == "Produto":
            out["produto_tipo"] = str(ptipo or "")
            out["produto_descricao"] = str(pdesc or "")
            out["produto_valor_euros"] = (int(pvc) / 100.0) if pvc is not None else 10.0
            po = str(porig or "proprio")
            out["produto_origem"] = po
            if po == "repasse":
                if prpct:
                    out["produto_repasse_modo"] = "percentual"
                    out["produto_repasse_pct"] = int(prpct) / 100.0
                elif prval:
                    out["produto_repasse_modo"] = "valor"
                    out["produto_repasse_valor_euros"] = int(prval) / 100.0
                else:
                    out["produto_repasse_modo"] = "percentual"
                    out["produto_repasse_pct"] = 30.0
        elif nat == "Coworking":
            out["cowork_sala_nome"] = str(cws or "")
            out["cowork_cobranca"] = str(cwc or "hora")
            out["cowork_valor_euros"] = (int(cwv) / 100.0) if cwv is not None else 8.0
        elif canon_natureza_catalogo(str(nat)) == NATUREZA_PACK:
            out["pacote_valor_euros"] = (int(pvalc) / 100.0) if pvalc is not None else 100.0
            out["pacote_repasse_ref_pct"] = (int(prefc) / 100.0) if prefc is not None else 50.0
            cur.execute(
                """
                SELECT psi.sessao_servico_id, s.nome, psi.quantidade,
                       COALESCE(psi.duracao_horas, 0.0)
                FROM servico_pacote_sessoes psi
                JOIN servicos s ON s.id = psi.sessao_servico_id
                WHERE psi.pacote_servico_id = ?
                ORDER BY psi.ordem
                """,
                (sid,),
            )
            out["pacote_linhas"] = [
                {"sessao_id": int(a), "sessao_nome": str(b), "quantidade": int(c), "duracao_horas": float(d or 0)}
                for a, b, c, d in cur.fetchall()
            ]
            cur.execute(
                """
                SELECT ppi.produto_servico_id, s.nome, ppi.quantidade
                FROM servico_pacote_produtos ppi
                JOIN servicos s ON s.id = ppi.produto_servico_id
                WHERE ppi.pacote_servico_id = ?
                """,
                (sid,),
            )
            prow = cur.fetchone()
            if prow:
                out["pacote_produto_opcional"] = {
                    "produto_id": int(prow[0]),
                    "nome": str(prow[1]),
                    "quantidade": int(prow[2]),
                }
        elif nat == "Evento":
            ds = (edata or "").strip()[:10]
            out["evento_data_iso"] = ds
            out["evento_local"] = str(eloc or "")
            out["evento_observacoes"] = str(eobs or "")
            out["evento_escopo"] = str(eesc or "interno")
            out["evento_preco_crianca_euros"] = (int(epcc) / 100.0) if epcc is not None else 10.0
            out["evento_preco_adulto_euros"] = (int(epca) / 100.0) if epca is not None else 15.0
            out["evento_desconto_filho_euros"] = (int(edfa) / 100.0) if edfa is not None else 0.0
            cur.execute(
                """
                SELECT sep.tipo, sep.colaborador_id, sep.parceiro_nome,
                       sep.repasse_pct_centesimos, sep.repasse_valor_centavos,
                       c.nome
                FROM servico_evento_participantes sep
                LEFT JOIN colaboradores c ON c.id = sep.colaborador_id
                WHERE sep.evento_servico_id = ?
                ORDER BY sep.ordem
                """,
                (sid,),
            )
            parts: list[tuple[str, int | None, str, str, float | None, float | None]] = []
            for t, cid, pn, rpc, rvl, cnom in cur.fetchall():
                tipo = str(t or "")
                modo = "percentual" if rpc else "valor"
                pct_e = float(rpc) / 100.0 if rpc else None
                ve_e = float(rvl) / 100.0 if rvl else None
                if tipo == "colaborador":
                    parts.append((tipo, int(cid) if cid is not None else None, "", modo, pct_e, ve_e))
                else:
                    parts.append((tipo, None, str(pn or ""), modo, pct_e, ve_e))
            out["evento_participantes"] = parts
        return out
    finally:
        conn.close()


# Re-export: implementação em módulo dedicado (import preguiçoso interno evita ciclos).
from src.modules.catalogo_atualizacao import (
    atualizar_evento_existente,
    atualizar_pacote_existente,
    atualizar_servico_fase1_existente,
)


__all__ = [
    "CAT_MSG_SUCESSO",
    "MSG_REGISTRO_DUPLICADO",
    "atualizar_evento_existente",
    "atualizar_pacote_existente",
    "atualizar_servico_fase1_existente",
    "cadastrar_especialidade",
    "cadastrar_evento",
    "cadastrar_pacote",
    "cadastrar_servico_fase1",
    "centavos_para_texto_euros",
    "euros_para_centavos",
    "listar_especialidades_por_natureza",
    "listar_itens_catalogo",
    "listar_naturezas_catalogo",
    "salvar_especialidade_catalogo",
    "salvar_natureza_catalogo",
    "listar_servicos_para_venda",
    "listar_sessoes_do_pacote_catalogo",
    "obter_duracao_referencia_agendamento_horas",
    "listar_servicos_produto_para_pacote",
    "listar_servicos_sessao_para_pacote",
    "obter_servico_para_formulario",
    "percentual_para_centesimos_ref",
    "repasse_medio_ponderado_pacote",
    "resolver_snapshot_venda",
]
