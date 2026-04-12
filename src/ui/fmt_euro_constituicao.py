"""Formato monetário canónico Constituição Visual: € 1.250,00 (milhar por ponto, decimal vírgula)."""

from __future__ import annotations


def fmt_euro_centavos(centavos: int) -> str:
    neg = "−" if centavos < 0 else ""
    x = abs(int(centavos))
    euros, cent = divmod(x, 100)
    s = str(euros)
    parts: list[str] = []
    while s:
        parts.append(s[-3:])
        s = s[:-3]
    body = ".".join(reversed(parts))
    return f"{neg}€ {body},{cent:02d}"
