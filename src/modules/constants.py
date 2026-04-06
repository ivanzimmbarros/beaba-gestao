"""Constantes partilhadas do domínio (evita imports frágeis entre UI e regras)."""

SEXOS: tuple[str, ...] = (
    "Feminino",
    "Masculino",
    "Outro",
    "Prefiro não informar",
)

__all__ = ["SEXOS"]
