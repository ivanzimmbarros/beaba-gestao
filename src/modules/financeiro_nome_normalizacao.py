"""Chave canónica para detectar nomes duplicados (centro, natureza, tipo de gasto).

Comparação ignora:
- maiúsculas / minúsculas (casefold);
- marcas diacríticas (acentos, cedilhas, etc.), via NFKD + remoção de caracteres combinantes.
"""

from __future__ import annotations

import unicodedata


def chave_duplicacao_nome(s: str) -> str:
    """Valor estável para testar se dois nomes visíveis são o «mesmo» registo lógico."""
    t = (s or "").strip()
    if not t:
        return ""
    nk = unicodedata.normalize("NFKD", t)
    sem_marcas = "".join(c for c in nk if unicodedata.category(c) != "Mn")
    return sem_marcas.casefold()
