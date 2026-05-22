"""Constantes partilhadas do domínio (evita imports frágeis entre UI e regras)."""

SEXOS: tuple[str, ...] = (
    "Feminino",
    "Masculino",
    "Outro",
    "Prefiro não informar",
)

# Catálogo — E06 incremental. Fase 1: Sessão, Produto, Coworking. Fase 2: Pack. Fase 3: Evento.
NATUREZA_PACK: str = "Pack"
NATUREZAS_CATALOGO_FASE1: tuple[str, ...] = ("Sessão", "Produto", "Coworking")
NATUREZAS_CATALOGO_FASE2: tuple[str, ...] = (*NATUREZAS_CATALOGO_FASE1, NATUREZA_PACK)
NATUREZAS_CATALOGO_FASE3: tuple[str, ...] = (*NATUREZAS_CATALOGO_FASE2, "Evento")


def canon_natureza_catalogo(nat: str) -> str:
    """Normaliza rótulo de natureza (legado «Pacote» → «Pack»)."""
    n = " ".join(str(nat or "").strip().split())
    if n.casefold() == "pacote":
        return NATUREZA_PACK
    return n


def natureza_requer_especialidade_servico(nat: str) -> bool:
    """Sessão, Produto, Coworking (ou rótulo renomeado) exigem especialidade; Pack e Evento não."""
    return canon_natureza_catalogo(nat) not in (NATUREZA_PACK, "Evento")


def tipo_servico_catalogo_por_natureza(nat: str) -> str:
    """
    Tipo de formulário / validação: sessao, produto, coworking, pack, evento ou vazio.
    Usa rótulo canónico quando o nome na BD foi personalizado (ex.: Coworking → Coworkin).
    """
    c = canon_natureza_catalogo(nat)
    if c == "Sessão":
        return "sessao"
    if c == "Produto":
        return "produto"
    if c == "Coworking":
        return "coworking"
    if c == NATUREZA_PACK:
        return "pack"
    if c == "Evento":
        return "evento"
    return ""

# Catálogo — camada Natureza → Especialidade → Serviço (épico Especialidades).
ESPECIALIDADE_PADRAO_NOME: str = "Geral"

# --- Venda: `vendas.estado_pagamento` (chaves BD em minúsculas) ---
ESTADOS_PAGAMENTO_VENDA_BD: tuple[str, ...] = ("integral", "pendente", "parcial", "parcelado")

ESTADO_PAGAMENTO_VENDA_LABEL_PT: dict[str, str] = {
    "integral": "Pagamento integral",
    "pendente": "Pagamento pendente",
    "parcial": "Pagamento parcial",
    "parcelado": "Pagamento parcelado",
}

# Painel de Vendas (sem UI de recebimentos previstos): `pendente` não é seleccionável aqui.
VENDAS_UI_MODALIDADES_PAGAMENTO_LINHA: tuple[str, ...] = ("integral", "parcial", "parcelado")

# --- Agendamento: rótulo PT único para `REALIZADO_PENDENTE_PGTO` (UI e mensagens) ---
ESTADO_AGENDAMENTO_REALIZADO_PENDENTE_LABEL_PT: str = "Realizado (pendente pagamento)"

# Estados incluídos em «repasse efectivo»: linhas já materializadas em `repasse_linhas` apenas com estes valores de `agendamentos.status`.
STATUS_AGENDAMENTO_REPASSE_CONTABILIZADO: tuple[str, ...] = (
    "CONCLUIDO",
    "REALIZADO_PENDENTE_PGTO",
)

__all__ = [
    "SEXOS",
    "ESPECIALIDADE_PADRAO_NOME",
    "NATUREZA_PACK",
    "canon_natureza_catalogo",
    "natureza_requer_especialidade_servico",
    "tipo_servico_catalogo_por_natureza",
    "NATUREZAS_CATALOGO_FASE1",
    "NATUREZAS_CATALOGO_FASE2",
    "NATUREZAS_CATALOGO_FASE3",
    "ESTADOS_PAGAMENTO_VENDA_BD",
    "ESTADO_PAGAMENTO_VENDA_LABEL_PT",
    "VENDAS_UI_MODALIDADES_PAGAMENTO_LINHA",
    "ESTADO_AGENDAMENTO_REALIZADO_PENDENTE_LABEL_PT",
    "STATUS_AGENDAMENTO_REPASSE_CONTABILIZADO",
]
