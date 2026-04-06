"""Cadastro de colaboradores, habilitações e percentuais de repasse."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime

from src.database.connection import get_connection
from src.modules.constants import SEXOS
from src.modules.validators import (
    email_valido,
    normalizar_codigo_postal_pt,
    parse_data_iso,
    validar_e_limpar_telefone,
)


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
                nome, sexo, data_nascimento, email, whatsapp, observacoes,
                endereco_rua, endereco_numero, endereco_complemento,
                codigo_postal, concelho, freguesia, distrito, pais
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nome,
                sexo,
                dn,
                email,
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


def obter_colaborador(colaborador_id: int) -> dict | None:
    cid = int(colaborador_id)
    conn = get_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT nome, sexo, data_nascimento, email, whatsapp, observacoes,
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
        "whatsapp": row[4],
        "observacoes": row[5] or "",
        "endereco_rua": row[6],
        "endereco_numero": row[7],
        "endereco_complemento": row[8] or "",
        "codigo_postal": row[9],
        "concelho": row[10],
        "freguesia": row[11],
        "distrito": row[12] or "",
        "pais": row[13] or "Portugal",
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
                nome = ?, sexo = ?, data_nascimento = ?, email = ?, whatsapp = ?, observacoes = ?,
                endereco_rua = ?, endereco_numero = ?, endereco_complemento = ?,
                codigo_postal = ?, concelho = ?, freguesia = ?, distrito = ?, pais = ?
            WHERE id = ?
            """,
            (
                nome,
                sexo,
                dn,
                email,
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
