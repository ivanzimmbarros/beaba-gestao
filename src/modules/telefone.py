"""Normalização E.164 com phonenumbers; compatibilidade com legado 11 dígitos (BR) e 9 (PT)."""

from __future__ import annotations

import re

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat

# Região por omissão quando o utilizador escolhe país no UI
_DEFAULT_REGION_FOR_ISO: dict[str, str] = {
    "PT": "PT",
    "BR": "BR",
    "ES": "ES",
    "US": "US",
    "CA": "CA",
}


def regiao_phonenumbers_para_iso2(iso2: str) -> str:
    return _DEFAULT_REGION_FOR_ISO.get(iso2.upper(), iso2.upper())


def normalizar_telefone_e164(
    numero_nacional: str,
    iso2_pais: str,
    tipo_linha: str,
) -> tuple[bool, str, str]:
    """
    `tipo_linha`: 'movel' | 'fixo'
    Devolve (ok, e164_ou_vazio, mensagem_erro).
    """
    iso = regiao_phonenumbers_para_iso2(iso2_pais)
    digits = re.sub(r"\D", "", numero_nacional or "")
    if not digits:
        return False, "", "❌ Indique o número após o indicativo do país."
    try:
        parsed = phonenumbers.parse(digits, iso)
    except NumberParseException:
        return False, "", "❌ Número inválido para o país seleccionado."
    if not phonenumbers.is_valid_number(parsed):
        return False, "", "❌ Número inválido para o país seleccionado."
    if tipo_linha == "movel":
        t = phonenumbers.number_type(parsed)
        if t not in (
            phonenumbers.PhoneNumberType.MOBILE,
            phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE,
        ):
            return False, "", "❌ O número não corresponde a um telemóvel. Escolha «Fixo» se for o caso."
    elif tipo_linha == "fixo":
        t = phonenumbers.number_type(parsed)
        if t == phonenumbers.PhoneNumberType.MOBILE:
            return False, "", "❌ O número parece ser telemóvel. Escolha «Telemóvel» se for o caso."
    e164 = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
    return True, e164, ""


def normalizar_telefone_legado_ou_e164(valor: str) -> str | None:
    """
    Aceita valor já E.164 (+…) ou legado 11 dígitos (BR) ou 9 dígitos (PT nacional).
    """
    v = (valor or "").strip()
    if not v:
        return None
    if v.startswith("+"):
        try:
            p = phonenumbers.parse(v, None)
            if phonenumbers.is_valid_number(p):
                return phonenumbers.format_number(p, PhoneNumberFormat.E164)
        except NumberParseException:
            return None
        return None
    digits = re.sub(r"\D", "", v)
    if len(digits) == 11:
        try:
            p = phonenumbers.parse(digits, "BR")
            if phonenumbers.is_valid_number(p) or phonenumbers.is_possible_number(p):
                return phonenumbers.format_number(p, PhoneNumberFormat.E164)
        except NumberParseException:
            pass
    if len(digits) == 9:
        try:
            p = phonenumbers.parse(digits, "PT")
            if phonenumbers.is_valid_number(p):
                return phonenumbers.format_number(p, PhoneNumberFormat.E164)
        except NumberParseException:
            pass
    return None
