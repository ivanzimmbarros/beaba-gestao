"""Lista de países com indicativo telefónico (UI de contacto)."""

from __future__ import annotations

# (ISO3166-1 alpha-2, indicativo E.164 sem +, nome em PT)
_PAIS_DIAL: list[tuple[str, str, str]] = [
    ("PT", "351", "Portugal"),
    ("BR", "55", "Brasil"),
    ("ES", "34", "Espanha"),
    ("FR", "33", "França"),
    ("DE", "49", "Alemanha"),
    ("GB", "44", "Reino Unido"),
    ("US", "1", "Estados Unidos"),
    ("CA", "1", "Canadá"),
    ("IT", "39", "Itália"),
    ("NL", "31", "Países Baixos"),
    ("BE", "32", "Bélgica"),
    ("CH", "41", "Suíça"),
    ("LU", "352", "Luxemburgo"),
    ("AO", "244", "Angola"),
    ("MZ", "258", "Moçambique"),
    ("CV", "238", "Cabo Verde"),
    ("TL", "670", "Timor-Leste"),
    ("IE", "353", "Irlanda"),
    ("PL", "48", "Polónia"),
    ("SE", "46", "Suécia"),
    ("NO", "47", "Noruega"),
    ("DK", "45", "Dinamarca"),
    ("FI", "358", "Finlândia"),
    ("AT", "43", "Áustria"),
    ("GR", "30", "Grécia"),
    ("RO", "40", "Roménia"),
    ("CZ", "420", "Rep. Checa"),
    ("HU", "36", "Hungria"),
    ("AR", "54", "Argentina"),
    ("CL", "56", "Chile"),
    ("CO", "57", "Colômbia"),
    ("MX", "52", "México"),
    ("UY", "598", "Uruguai"),
    ("VE", "58", "Venezuela"),
    ("IN", "91", "Índia"),
    ("CN", "86", "China"),
    ("JP", "81", "Japão"),
    ("KR", "82", "Coreia do Sul"),
    ("ZA", "27", "África do Sul"),
]


def listar_paises_indicativo() -> list[tuple[str, str, str]]:
    return list(_PAIS_DIAL)


def rotulo_pais_telefone(iso2: str, dial: str, nome: str) -> str:
    return f"{nome} ({iso2}) +{dial}"


def encontrar_por_texto_busca(busca: str) -> list[tuple[str, str, str]]:
    t = (busca or "").strip().lower()
    if not t:
        return listar_paises_indicativo()
    out: list[tuple[str, str, str]] = []
    for iso, dial, nome in _PAIS_DIAL:
        if (
            t in nome.lower()
            or t in iso.lower()
            or t in dial
            or t in f"+{dial}"
            or (t.startswith("+") and dial.startswith(t[1:]))
        ):
            out.append((iso, dial, nome))
    return out if out else listar_paises_indicativo()
