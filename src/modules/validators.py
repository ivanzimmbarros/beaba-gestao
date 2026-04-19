"""Validações partilhadas (contacto, email, código postal, datas)."""

from __future__ import annotations

import re
from datetime import datetime


def validar_e_limpar_telefone(valor: str) -> str | None:
    num_limpo = re.sub(r"\D", "", valor or "")
    return num_limpo if len(num_limpo) == 11 else None


def normalizar_codigo_postal_pt(raw: str) -> str | None:
    """Aceita '1234-567' ou '1234567'; devolve sempre 'XXXX-XXX' ou None."""
    t = (raw or "").strip().replace(" ", "")
    if re.fullmatch(r"\d{7}", t):
        return f"{t[:4]}-{t[4:]}"
    if re.fullmatch(r"\d{4}-\d{3}", t):
        return t
    return None


def email_valido(email: str) -> bool:
    e = (email or "").strip()
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", e))


def parse_data_iso(s: str | None) -> bool:
    if not s or not str(s).strip():
        return False
    try:
        datetime.strptime(str(s).strip()[:10], "%Y-%m-%d")
        return True
    except ValueError:
        return False


def normalizar_iban_dados_bancarios(raw: str) -> tuple[bool, str, str]:
    """
    Validação leve de IBAN (formato internacional) para ficha de colaborador.
    Devolve (ok, mensagem_erro, iban_sem_espacos_maiúsculas).
    """
    t = re.sub(r"\s+", "", (raw or "").strip()).upper()
    if not t:
        return False, "❌ Dados Bancários — IBAN é obrigatório.", ""
    if len(t) < 15 or len(t) > 34:
        return False, "❌ IBAN inválido (comprimento).", ""
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]+", t):
        return False, "❌ IBAN inválido (use o formato internacional, ex.: PT50…).", ""
    return True, "", t
