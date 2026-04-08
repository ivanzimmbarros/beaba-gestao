"""Validação NIF Portugal (módulo 11) e documento de identificação internacional."""

from __future__ import annotations

import re


def _apenas_digitos(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def validar_nif_portugal(nif: str) -> bool:
    """NIF PT: 9 dígitos, primeiro 1/2/3/5/6/8/9, dígito de controlo módulo 11."""
    d = _apenas_digitos(nif)
    if len(d) != 9:
        return False
    if d[0] not in "1235689":
        return False
    soma = sum(int(d[i]) * (9 - i) for i in range(8))
    resto = soma % 11
    dig = 0 if resto < 2 else 11 - resto
    return int(d[8]) == dig


def formatar_nif_visual_pt(nif: str) -> str:
    d = _apenas_digitos(nif)
    if len(d) != 9:
        return (nif or "").strip()
    return f"{d[:3]} {d[3:6]} {d[6:]}"


def validar_documento_identificacao_internacional(valor: str) -> bool:
    v = (valor or "").strip()
    if len(v) < 3 or len(v) > 40:
        return False
    return bool(re.fullmatch(r"[\w\s\-./]+", v, re.UNICODE))


def normalizar_nif_armazenamento(
    valor: str,
    *,
    documento_identificacao_internacional: bool,
) -> tuple[bool, str, str]:
    """Devolve (ok, mensagem_erro ou \"\", valor_normalizado)."""
    if documento_identificacao_internacional:
        v = (valor or "").strip()
        if not validar_documento_identificacao_internacional(v):
            return False, "❌ Indique o documento de identificação (3–40 caracteres válidos).", ""
        return True, "", v
    d = _apenas_digitos(valor)
    if len(d) != 9:
        return False, "❌ O NIF deve ter 9 dígitos.", ""
    if not validar_nif_portugal(d):
        return False, "❌ NIF português inválido (verifique o dígito de controlo).", ""
    return True, "", d
