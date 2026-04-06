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
        cur.execute("SELECT id, nome FROM servicos WHERE ativo = 1 ORDER BY nome")
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
    servicos_repasse: list[tuple[int, float]],
) -> tuple[bool, str]:
    """
    `servicos_repasse`: lista (servico_id, percentual %) com duas casas decimais (0,01 a 100,00).
    Número de contacto exclusivo por colaborador (UNIQUE).
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
    linhas: list[tuple[int, int]] = []
    for sid, pct in servicos_repasse:
        sid = int(sid)
        if sid in vistos:
            return False, "❌ Não repita o mesmo serviço na lista de habilitações."
        vistos.add(sid)
        cent = percentual_para_centesimos(pct)
        if cent is None:
            return False, "❌ Cada percentual deve estar entre 0,01% e 100,00% (duas casas decimais)."
        linhas.append((sid, cent))

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
        for ordem, (sid, cent) in enumerate(linhas, start=1):
            cur.execute(
                """
                INSERT INTO colaborador_servicos (colaborador_id, servico_id, percentual_centesimos, ordem)
                VALUES (?, ?, ?, ?)
                """,
                (cid, sid, cent, ordem),
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
