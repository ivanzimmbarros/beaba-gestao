"""Constantes partilhadas do domínio (evita imports frágeis entre UI e regras)."""

SEXOS: tuple[str, ...] = (
    "Feminino",
    "Masculino",
    "Outro",
    "Prefiro não informar",
)

# Catálogo — Fase 1 (E06 incremental). Pacote e Evento nas fases seguintes.
NATUREZAS_CATALOGO_FASE1: tuple[str, ...] = ("Sessão", "Produto", "Coworking")

__all__ = ["SEXOS", "NATUREZAS_CATALOGO_FASE1"]
