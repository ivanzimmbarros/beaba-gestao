"""Cadastro de colaboradores, habilitações e percentuais de repasse."""

from __future__ import annotations

import re
import sqlite3
from collections import OrderedDict
from datetime import date, datetime

from src.database.connection import get_connection
from src.modules.constants import SEXOS
from src.modules.nif import normalizar_nif_armazenamento
from src.modules.telefone import normalizar_telefone_legado_ou_e164
from src.modules.validators import (
    email_valido,
    normalizar_codigo_postal_pt,
    parse_data_iso,
    validar_e_limpar_telefone,
)


def _candidatos_whatsapp_colaborador_busca(raw: str) -> list[str]:
    """Variantes para bater com `colaboradores.whatsapp` (E.164, só dígitos, legado 11)."""
    out: list[str] = []
    s = (raw or "").strip()
    if not s:
        return []
    t = normalizar_telefone_legado_ou_e164(s)
    if t:
        out.append(t)
        out.append(t.lstrip("+"))
    d = re.sub(r"\D", "", s)
    if d:
        out.append(d)
    v = validar_e_limpar_telefone(s)
    if v:
        out.append(v)
    seen: set[str] = set()
    uniq: list[str] = []
    for x in out:
        if x and x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def buscar_colaboradores_por_nif_email_telefone(
    *,
    nif: str = "",
    email: str = "",
    telefone: str = "",
    documento_internacional: bool = False,
) -> list[tuple[int, str]]:
    """Pesquisa OR (NIF normalizado, email, várias formas de telefone)."""
    merged: dict[int, str] = {}
    conn = get_connection()
    if not conn:
        return []

    def _add_rows(rows: list[tuple[int, str]]) -> None:
        for cid, nome in rows:
            merged[int(cid)] = str(nome)

    try:
        cur = conn.cursor()
        for cand in _candidatos_whatsapp_colaborador_busca((telefone or "").strip()):
            cur.execute(
                "SELECT id, nome FROM colaboradores WHERE whatsapp = ? ORDER BY nome COLLATE NOCASE",
                (cand,),
            )
            _add_rows([(int(a), str(b)) for a, b in cur.fetchall()])

        em = (email or "").strip().lower()
        if em and email_valido(em):
            cur.execute(
                """
                SELECT id, nome FROM colaboradores
                WHERE lower(trim(email)) = ?
                ORDER BY nome COLLATE NOCASE
                """,
                (em,),
            )
            _add_rows([(int(a), str(b)) for a, b in cur.fetchall()])

        nif_raw = (nif or "").strip()
        if nif_raw:
            ok_n, _, nif_v = normalizar_nif_armazenamento(
                nif_raw, documento_identificacao_internacional=bool(documento_internacional)
            )
            if ok_n:
                cur.execute(
                    """
                    SELECT id, nome FROM colaboradores
                    WHERE nif_ou_documento IS NOT NULL AND trim(nif_ou_documento) != ''
                      AND nif_ou_documento = ?
                    ORDER BY nome COLLATE NOCASE
                    """,
                    (nif_v,),
                )
                _add_rows([(int(a), str(b)) for a, b in cur.fetchall()])
    finally:
        conn.close()

    out = sorted(merged.items(), key=lambda x: (x[1].lower(), x[0]))
    return [(i, n) for i, n in out]


def buscar_colaboradores_por_prefixo_nome(prefixo: str, *, limit: int = 40) -> list[tuple[int, str]]:
    """
    Colaboradores cujo nome começa por `prefixo` (trim, LIKE case-insensitive).
    SQL parametrizado; `%` e `_` no prefixo são escapados. `limit` capa custo.
    """
    raw = (prefixo or "").strip()
    if not raw:
        return []
    lim = max(1, min(int(limit), 200))

    esc = raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    like_arg = f"{esc}%"

    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, nome FROM colaboradores
            WHERE nome LIKE ? ESCAPE '\\'
            ORDER BY nome COLLATE NOCASE
            LIMIT ?
            """,
            (like_arg, lim),
        )
        return [(int(a), str(b)) for a, b in cur.fetchall()]
    finally:
        conn.close()


def percentual_para_centesimos(pct: float) -> int | None:
    """Converte 0,01–100,00 % para inteiro 1–10000 (duas casas decimais implícitas)."""
    c = int(round(float(pct) * 100))
    if c < 1 or c > 10000:
        return None
    return c


def idade_anos_completos(data_nasc_iso: str) -> int | None:
    if not parse_data_iso(data_nasc_iso):
        return None
    d = datetime.strptime(data_nasc_iso[:10], "%Y-%m-%d").date()
    hoje = date.today()
    anos = hoje.year - d.year - ((hoje.month, hoje.day) < (d.month, d.day))
    return anos


def listar_servicos() -> list[tuple[int, str]]:
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, nome FROM servicos
            WHERE ativo = 1
              AND IFNULL(natureza, '') NOT IN ('Pacote', 'Evento')
            ORDER BY nome
            """
        )
        return list(cur.fetchall())
    finally:
        conn.close()


def cadastrar_colaborador(
    nome: str,
    sexo: str,
    data_nascimento: str,
    endereco_rua: str,
    endereco_numero: str,
    endereco_complemento: str,
    codigo_postal: str,
    concelho: str,
    freguesia: str,
    distrito: str,
    pais: str,
    email: str,
    numero_contato: str,
    observacoes: str,
    servicos_repasse: list[tuple[int, float, str]],
    *,
    nif_ou_documento: str = "",
    identificacao_internacional: bool = False,
) -> tuple[bool, str]:
    """
    `servicos_repasse`: lista (servico_id, percentual %, data_insercao_linha ISO YYYY-MM-DD)
    por linha de habilitação (data da inserção da linha, não do cadastro do colaborador).
    """
    nome = (nome or "").strip()
    if not nome:
        return False, "❌ O nome é obrigatório."

    if sexo not in SEXOS:
        return False, "❌ Selecione uma opção de sexo."

    dn = (data_nascimento or "").strip()[:10]
    if not parse_data_iso(dn):
        return False, "❌ A data de nascimento é obrigatória e deve ser válida."
    idade = idade_anos_completos(dn)
    if idade is None or idade < 18:
        return False, "❌ O colaborador deve ter pelo menos 18 anos de idade."

    rua = (endereco_rua or "").strip()
    num = (endereco_numero or "").strip()
    comp = (endereco_complemento or "").strip()
    cp = normalizar_codigo_postal_pt(codigo_postal)
    conc = (concelho or "").strip()
    freg = (freguesia or "").strip()
    dist = (distrito or "").strip()
    pais_v = (pais or "").strip() or "Portugal"

    if not rua:
        return False, "❌ A rua (logradouro) é obrigatória."
    if not num:
        return False, "❌ O número de porta é obrigatório."
    if not cp:
        return False, "❌ O código postal é obrigatório (formato XXXX-XXX)."
    if not conc:
        return False, "❌ O concelho é obrigatório."
    if not freg:
        return False, "❌ A freguesia é obrigatória."

    email = (email or "").strip()
    if not email:
        return False, "❌ O email é obrigatório."
    if not email_valido(email):
        return False, "❌ Indique um email válido."

    nif_raw = (nif_ou_documento or "").strip()
    nif_store: str | None = None
    intl_i = 0
    if nif_raw:
        ok_n, msg_n, nif_v = normalizar_nif_armazenamento(
            nif_raw, documento_identificacao_internacional=bool(identificacao_internacional)
        )
        if not ok_n:
            return False, msg_n
        nif_store = nif_v
        intl_i = 1 if identificacao_internacional else 0

    tel = validar_e_limpar_telefone(numero_contato)
    if not tel:
        return False, "❌ O número de contacto deve ter 11 dígitos numéricos."

    if not servicos_repasse:
        return False, "❌ Indique pelo menos um serviço habilitado com o respetivo percentual."

    vistos: set[int] = set()
    linhas: list[tuple[int, int, str]] = []
    for sid, pct, dlinha in servicos_repasse:
        sid = int(sid)
        if sid in vistos:
            return False, "❌ Não repita o mesmo serviço na lista de habilitações."
        vistos.add(sid)
        cent = percentual_para_centesimos(pct)
        if cent is None:
            return False, "❌ Cada percentual deve estar entre 0,01% e 100,00% (duas casas decimais)."
        dl = (dlinha or "").strip()[:10]
        if not parse_data_iso(dl):
            return False, "❌ Em cada linha, a data de inserção da habilitação é obrigatória (formato AAAA-MM-DD)."
        linhas.append((sid, cent, dl))

    obs = (observacoes or "").strip()

    conn = get_connection()
    if not conn:
        return False, "❌ Não foi possível ligar à base de dados."

    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM servicos WHERE id IN ({})".format(",".join("?" * len(vistos))), tuple(vistos))
        if len(cur.fetchall()) != len(vistos):
            return False, "❌ Um ou mais serviços selecionados são inválidos."

        cur.execute(
            """
            INSERT INTO colaboradores (
                nome, sexo, data_nascimento, email, nif_ou_documento, identificacao_internacional,
                whatsapp, observacoes,
                endereco_rua, endereco_numero, endereco_complemento,
                codigo_postal, concelho, freguesia, distrito, pais
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nome,
                sexo,
                dn,
                email,
                nif_store,
                intl_i,
                tel,
                obs,
                rua,
                num,
                comp,
                cp,
                conc,
                freg,
                dist,
                pais_v,
            ),
        )
        cid = cur.lastrowid
        for ordem, (sid, cent, dl) in enumerate(linhas, start=1):
            cur.execute(
                """
                INSERT INTO colaborador_servicos (
                    colaborador_id, servico_id, percentual_centesimos, ordem, data_insercao_linha
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (cid, sid, cent, ordem, dl),
            )
        conn.commit()
        return True, "✅ Colaborador cadastrado com sucesso."
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, "⚠️ Este número de contacto já está atribuído a outro colaborador."
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao guardar: {e}"
    finally:
        conn.close()


def listar_colaboradores_resumo() -> list[tuple[int, str]]:
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, nome FROM colaboradores ORDER BY nome COLLATE NOCASE")
        return list(cur.fetchall())
    finally:
        conn.close()


def listar_colaboradores_vitrine() -> list[tuple[int, str, str]]:
    """
    Lista para cards na UI: (id, nome, primeiro serviço habilitado ou etiqueta neutra).
    """
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT c.id, c.nome,
              COALESCE(
                (SELECT s.nome FROM colaborador_servicos cs
                 JOIN servicos s ON s.id = cs.servico_id
                 WHERE cs.colaborador_id = c.id
                 ORDER BY cs.ordem LIMIT 1),
                ''
              ) AS primeiro_serv
            FROM colaboradores c
            ORDER BY c.nome COLLATE NOCASE
            """
        )
        out: list[tuple[int, str, str]] = []
        for rid, nome, ps in cur.fetchall():
            lbl = str(ps).strip() if ps else "Sem serviço"
            out.append((int(rid), str(nome), lbl))
        return out
    finally:
        conn.close()


def listar_naturezas_servicos_mapa_equipa() -> list[str]:
    """Naturezas distintas de serviços activos elegíveis na UI Col (excl. Pacote/Evento)."""
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT TRIM(IFNULL(natureza, '')) AS n
            FROM servicos
            WHERE ativo = 1
              AND TRIM(IFNULL(natureza, '')) NOT IN ('', 'Pacote', 'Evento')
            ORDER BY n COLLATE NOCASE
            """
        )
        return [str(r[0]) for r in cur.fetchall() if r[0]]
    finally:
        conn.close()


def listar_servicos_para_mapa_equipa(naturezas: list[str] | None = None) -> list[tuple[int, str, str]]:
    """
    (servico_id, nome, natureza) para multiselect «Serviços Registados».
    Sem naturezas: todos os serviços elegíveis; com naturezas: só essas naturezas (trim).
    """
    nats = [str(x).strip() for x in (naturezas or []) if str(x).strip()]
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        base = """
            SELECT id, nome, TRIM(IFNULL(natureza, ''))
            FROM servicos
            WHERE ativo = 1
              AND IFNULL(natureza, '') NOT IN ('Pacote', 'Evento')
        """
        if nats:
            ph = ",".join("?" * len(nats))
            cur.execute(
                base + f" AND TRIM(IFNULL(natureza, '')) IN ({ph}) ORDER BY nome COLLATE NOCASE",
                nats,
            )
        else:
            cur.execute(base + " ORDER BY nome COLLATE NOCASE")
        return [(int(a), str(b), str(c)) for a, b, c in cur.fetchall()]
    finally:
        conn.close()


def resolver_conjunto_servicos_mapa_equipa(
    *,
    naturezas_seleccionadas: list[str],
    servico_ids_seleccionados: list[int],
) -> list[int]:
    """
    Conjunto de serviço_ids para filtrar habilitações.
    - Só naturezas: todos os serviços activos com essas naturezas.
    - Só serviços: os ids seleccionados (se ainda elegíveis).
    - Ambos: intersecção (serviço ∈ seleção e natureza ∈ seleção).
    Listas ambas vazias: [].
    """
    nats = [str(x).strip() for x in naturezas_seleccionadas if str(x).strip()]
    sids = [int(x) for x in servico_ids_seleccionados]

    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, TRIM(IFNULL(natureza, ''))
            FROM servicos
            WHERE ativo = 1
              AND IFNULL(natureza, '') NOT IN ('Pacote', 'Evento')
            """
        )
        id_to_nat: dict[int, str] = {int(r[0]): str(r[1]) for r in cur.fetchall()}
    finally:
        conn.close()

    if not nats and not sids:
        return []

    if nats and sids:
        out = {sid for sid in sids if sid in id_to_nat and id_to_nat[sid] in nats}
        return sorted(out)
    if sids:
        out = {sid for sid in sids if sid in id_to_nat}
        return sorted(out)
    return sorted(i for i, nat in id_to_nat.items() if nat in nats)


def listar_colaboradores_mapa_equipa(servico_ids: list[int], *, limit: int = 400) -> list[dict[str, object]]:
    """
    Colaboradores com pelo menos uma habilitação em `servico_ids`.
    Cada entrada: ``{"id": int, "nome": str, "servicos": [(nome_servico, natureza), ...]}``
    (apenas habilitações cujo serviço está no conjunto), ordenado por nome.
    """
    if not servico_ids:
        return []
    lim = max(1, min(int(limit), 2000))
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        ph = ",".join("?" * len(servico_ids))
        cur.execute(
            f"""
            SELECT c.id, c.nome, s.nome, TRIM(IFNULL(s.natureza, ''))
            FROM colaboradores c
            INNER JOIN colaborador_servicos cs ON cs.colaborador_id = c.id
            INNER JOIN servicos s ON s.id = cs.servico_id AND s.ativo = 1
            WHERE cs.servico_id IN ({ph})
            ORDER BY c.nome COLLATE NOCASE, s.nome COLLATE NOCASE
            """,
            servico_ids,
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    by_c: "OrderedDict[int, tuple[str, list[tuple[str, str]]]]" = OrderedDict()
    for cid, nome, snome, nat in rows:
        cid_i = int(cid)
        if cid_i not in by_c:
            by_c[cid_i] = (str(nome), [])
        by_c[cid_i][1].append((str(snome), str(nat)))

    out: list[dict[str, object]] = []
    for cid_i, (nome, sv) in by_c.items():
        out.append({"id": cid_i, "nome": nome, "servicos": sv})
        if len(out) >= lim:
            break
    return out


def obter_colaborador(colaborador_id: int) -> dict | None:
    cid = int(colaborador_id)
    conn = get_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT nome, sexo, data_nascimento, email, nif_ou_documento, identificacao_internacional,
                   whatsapp, observacoes,
                   endereco_rua, endereco_numero, endereco_complemento,
                   codigo_postal, concelho, freguesia, distrito, pais
            FROM colaboradores WHERE id = ?
            """,
            (cid,),
        )
        row = cur.fetchone()
        if not row:
            return None
        cur.execute(
            """
            SELECT cs.servico_id, s.nome, cs.percentual_centesimos, cs.data_insercao_linha
            FROM colaborador_servicos cs
            JOIN servicos s ON s.id = cs.servico_id
            WHERE cs.colaborador_id = ?
            ORDER BY cs.ordem
            """,
            (cid,),
        )
        slinhas = cur.fetchall()
    finally:
        conn.close()

    linhas: list[dict[str, int | float | str]] = []
    for sid, snome, cent, dlinha in slinhas:
        linhas.append(
            {
                "servico_id": int(sid),
                "nome_servico": str(snome),
                "percentual": int(cent) / 100.0,
                "data_insercao_linha": (dlinha or "")[:10],
            }
        )

    return {
        "id": cid,
        "nome": row[0],
        "sexo": row[1],
        "data_nascimento": row[2],
        "email": row[3],
        "nif_ou_documento": row[4] or "",
        "identificacao_internacional": bool(row[5]),
        "whatsapp": row[6],
        "observacoes": row[7] or "",
        "endereco_rua": row[8],
        "endereco_numero": row[9],
        "endereco_complemento": row[10] or "",
        "codigo_postal": row[11],
        "concelho": row[12],
        "freguesia": row[13],
        "distrito": row[14] or "",
        "pais": row[15] or "Portugal",
        "linhas": linhas,
    }


def atualizar_colaborador(
    colaborador_id: int,
    nome: str,
    sexo: str,
    data_nascimento: str,
    endereco_rua: str,
    endereco_numero: str,
    endereco_complemento: str,
    codigo_postal: str,
    concelho: str,
    freguesia: str,
    distrito: str,
    pais: str,
    email: str,
    numero_contato: str,
    observacoes: str,
    servicos_repasse: list[tuple[int, float, str]],
    *,
    nif_ou_documento: str = "",
    identificacao_internacional: bool = False,
) -> tuple[bool, str]:
    """Atualiza ficha e substitui todas as linhas de habilitação."""
    nome = (nome or "").strip()
    if not nome:
        return False, "❌ O nome é obrigatório."

    if sexo not in SEXOS:
        return False, "❌ Selecione uma opção de sexo."

    dn = (data_nascimento or "").strip()[:10]
    if not parse_data_iso(dn):
        return False, "❌ A data de nascimento é obrigatória e deve ser válida."
    idade = idade_anos_completos(dn)
    if idade is None or idade < 18:
        return False, "❌ O colaborador deve ter pelo menos 18 anos de idade."

    rua = (endereco_rua or "").strip()
    num = (endereco_numero or "").strip()
    comp = (endereco_complemento or "").strip()
    cp = normalizar_codigo_postal_pt(codigo_postal)
    conc = (concelho or "").strip()
    freg = (freguesia or "").strip()
    dist = (distrito or "").strip()
    pais_v = (pais or "").strip() or "Portugal"

    if not rua:
        return False, "❌ A rua (logradouro) é obrigatória."
    if not num:
        return False, "❌ O número de porta é obrigatório."
    if not cp:
        return False, "❌ O código postal é obrigatório (formato XXXX-XXX)."
    if not conc:
        return False, "❌ O concelho é obrigatório."
    if not freg:
        return False, "❌ A freguesia é obrigatória."

    email = (email or "").strip()
    if not email:
        return False, "❌ O email é obrigatório."
    if not email_valido(email):
        return False, "❌ Indique um email válido."

    nif_raw = (nif_ou_documento or "").strip()
    nif_store: str | None = None
    intl_i = 0
    if nif_raw:
        ok_n, msg_n, nif_v = normalizar_nif_armazenamento(
            nif_raw, documento_identificacao_internacional=bool(identificacao_internacional)
        )
        if not ok_n:
            return False, msg_n
        nif_store = nif_v
        intl_i = 1 if identificacao_internacional else 0

    tel = validar_e_limpar_telefone(numero_contato)
    if not tel:
        return False, "❌ O número de contacto deve ter 11 dígitos numéricos."

    if not servicos_repasse:
        return False, "❌ Indique pelo menos um serviço habilitado com o respetivo percentual."

    vistos: set[int] = set()
    linhas: list[tuple[int, int, str]] = []
    for sid, pct, dlinha in servicos_repasse:
        sid = int(sid)
        if sid in vistos:
            return False, "❌ Não repita o mesmo serviço na lista de habilitações."
        vistos.add(sid)
        cent = percentual_para_centesimos(pct)
        if cent is None:
            return False, "❌ Cada percentual deve estar entre 0,01% e 100,00% (duas casas decimais)."
        dl = (dlinha or "").strip()[:10]
        if not parse_data_iso(dl):
            return False, "❌ Em cada linha, a data de inserção da habilitação é obrigatória (formato AAAA-MM-DD)."
        linhas.append((sid, cent, dl))

    obs = (observacoes or "").strip()
    cid = int(colaborador_id)

    conn = get_connection()
    if not conn:
        return False, "❌ Não foi possível ligar à base de dados."

    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM colaboradores WHERE id = ?", (cid,))
        if not cur.fetchone():
            return False, "❌ Colaborador não encontrado."

        cur.execute("SELECT id FROM servicos WHERE id IN ({})".format(",".join("?" * len(vistos))), tuple(vistos))
        if len(cur.fetchall()) != len(vistos):
            return False, "❌ Um ou mais serviços selecionados são inválidos."

        cur.execute(
            """
            UPDATE colaboradores SET
                nome = ?, sexo = ?, data_nascimento = ?, email = ?,
                nif_ou_documento = ?, identificacao_internacional = ?,
                whatsapp = ?, observacoes = ?,
                endereco_rua = ?, endereco_numero = ?, endereco_complemento = ?,
                codigo_postal = ?, concelho = ?, freguesia = ?, distrito = ?, pais = ?
            WHERE id = ?
            """,
            (
                nome,
                sexo,
                dn,
                email,
                nif_store,
                intl_i,
                tel,
                obs,
                rua,
                num,
                comp,
                cp,
                conc,
                freg,
                dist,
                pais_v,
                cid,
            ),
        )
        cur.execute("DELETE FROM colaborador_servicos WHERE colaborador_id = ?", (cid,))
        for ordem, (sid, cent, dl) in enumerate(linhas, start=1):
            cur.execute(
                """
                INSERT INTO colaborador_servicos (
                    colaborador_id, servico_id, percentual_centesimos, ordem, data_insercao_linha
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (cid, sid, cent, ordem, dl),
            )
        conn.commit()
        return True, "✅ Colaborador atualizado com sucesso."
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, "⚠️ Este número de contacto já está atribuído a outro colaborador."
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao guardar: {e}"
    finally:
        conn.close()


def media_repasse_percentual_servico(servico_id: int) -> float | None:
    """Média dos percentuais de repasse (0–100 com decimais) dos colaboradores habilitados."""
    conn = get_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT AVG(percentual_centesimos)
            FROM colaborador_servicos
            WHERE servico_id = ?
            """,
            (int(servico_id),),
        )
        row = cur.fetchone()
        if not row or row[0] is None:
            return None
        return float(row[0]) / 100.0
    finally:
        conn.close()
