"""Constantes partilhadas do domínio (evita imports frágeis entre UI e regras)."""

SEXOS: tuple[str, ...] = (
    "Feminino",
    "Masculino",
    "Outro",
    "Prefiro não informar",
)

# Catálogo — E06 incremental. Fase 1: Sessão, Produto, Coworking. Fase 2: Pacote. Fase 3: Evento.
NATUREZAS_CATALOGO_FASE1: tuple[str, ...] = ("Sessão", "Produto", "Coworking")
NATUREZAS_CATALOGO_FASE2: tuple[str, ...] = (*NATUREZAS_CATALOGO_FASE1, "Pacote")
NATUREZAS_CATALOGO_FASE3: tuple[str, ...] = (*NATUREZAS_CATALOGO_FASE2, "Evento")

__all__ = ["SEXOS", "NATUREZAS_CATALOGO_FASE1", "NATUREZAS_CATALOGO_FASE2", "NATUREZAS_CATALOGO_FASE3"]
