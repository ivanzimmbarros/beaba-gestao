# E18 — Modelo híbrido operacional-financeiro

**Data:** 2026-04-08  
**Fonte:** `@Files` / EQUIPE — execução após plano aprovado.

## Objectivo

Evoluir agendamentos, pagamentos multi-meio, ledger de créditos de cliente, repasse por atendimento, auditoria de estados e UI (calendário dual, vendas, filtros de clientes).

## Escopo desta entrega (MVP técnico)

- Schema: `agendamento_historico`, `credito_movimentos`, `vw_cliente_saldo_credito`, `venda_pagamento_linhas`, `repasse_linhas`, novos `agendamentos.status`.
- Gate: `CONCLUIDO` só se soma de linhas de pagamento = total líquido (`total_final - credito_abatido`); caso contrário `REALIZADO_PENDENTE_PGTO`.
- Cancelamento: opção de converter valor em crédito (ledger com idempotência).
- Vendas: linhas E18 + abatimento de crédito + card «Falta Lançar».
- Calendário: cor estado + indicador pagamento; clientes com filtro saldo.

## Próximos documentos

- `02_desenho_funcional.md` — máquina de estados e ER.
