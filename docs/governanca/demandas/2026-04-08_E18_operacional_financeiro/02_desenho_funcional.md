# E18 — Desenho funcional (resumo)

## Estados agendamento

`PRE_AGENDADO` → `AGENDADO` → `CONFIRMADO` → `REALIZADO_PENDENTE_PGTO` ⇄ `CONCLUIDO` | `CANCELADO`

- **Gate CONCLUIDO:** `SUM(venda_pagamento_linhas) + legacy venda_pagamentos` deve igualar `total_final_centavos - credito_abatido_centavos` na venda ligada; senão a transição define `REALIZADO_PENDENTE_PGTO` com mensagem explícita.

## Ledger

- `credito_movimentos`: append-only; `UNIQUE(referencia_tipo, referencia_id, tipo_movimento)` para idempotência.
- Crédito por cancelamento: `tipo_movimento = CREDITO_CANCELAMENTO`, referência `agendamento`.

## Repasse

- `repasse_linhas` geradas ao entrar `REALIZADO_PENDENTE_PGTO` ou `CONCLUIDO` (base: `preco_referencia_centavos` ou linha de venda).

## Pagamentos

- `venda_pagamento_linhas.tipo_meio`: `DINHEIRO_MBWAY`, `IBAN`, `CARTAO_CREDITO`, `CREDITO_LOJA` (uso futuro explícito em linha).
