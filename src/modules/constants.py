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

__all__ = [
    "SEXOS",
    "ESPECIALIDADE_PADRAO_NOME",
    "NATUREZAS_CATALOGO_FASE1",
    "NATUREZAS_CATALOGO_FASE2",
    "NATUREZAS_CATALOGO_FASE3",
    "ESTADOS_PAGAMENTO_VENDA_BD",
    "ESTADO_PAGAMENTO_VENDA_LABEL_PT",
    "VENDAS_UI_MODALIDADES_PAGAMENTO_LINHA",
    "ESTADO_AGENDAMENTO_REALIZADO_PENDENTE_LABEL_PT",
]
