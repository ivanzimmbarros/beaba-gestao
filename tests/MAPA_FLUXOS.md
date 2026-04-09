# Épico 20 — Fortaleza Operacional: mapa de fluxos E2E (checklist de desenho)

Documento de **mapeamento** antes da codificação de testes de stress. Cada fluxo lista **critérios de aceitação** verificáveis na base (`tabela` / `valor`).

---

## Fluxo 1 — Cadastro de cliente

| # | Critério de aceitação |
|---|------------------------|
| 1.1 | O **nome** e **whatsapp** (E.164) enviados pelo formulário devem chegar a `clientes` nas colunas `nome` e `whatsapp` com os **mesmos valores normalizados** (contacto via `normalizar_telefone_legado_ou_e164`). |
| 1.2 | O **NIF** ou documento internacional normalizado deve estar em `clientes.nif_ou_documento`; com `identificacao_internacional = 1` quando aplicável. |
| 1.3 | Morada estruturada: `endereco_rua`, `codigo_postal` (formato PT `NNNN-NNN` quando PT), `concelho`, `freguesia` **NOT NULL** coerentes com o cadastro. |
| 1.4 | Tentativa de segundo cliente com o **mesmo `whatsapp`** deve **não** criar linha duplicada (rejeição de domínio ou UNIQUE). |

---

## Fluxo 2 — Jornada herói: Pré-venda → Agendamento → Venda → Associação

| # | Critério de aceitação |
|---|------------------------|
| 2.1 | Após `criar_agendamento_pre_venda`, deve existir linha em `agendamentos` com `cliente_id` = cliente da jornada, `servico_id` = serviço da sessão, `modo_origem = 'pre_venda'`, `venda_id` **NULL**, `status` coerente (ex.: `AGENDADO`). |
| 2.2 | Colaboradores: pelo menos uma linha em `agendamento_colaboradores` com `agendamento_id` ligado ao agendamento e `colaborador_id` válido. |
| 2.3 | Após `registrar_venda` com `agendamento_contexto_id` = id do agendamento, `vendas.cliente_id` = mesmo cliente e deve existir `venda_itens` com `servico_id` alinhado ao agendamento. |
| 2.4 | Pagamento integral E18: `venda_pagamento_linhas` deve somar (com legado se vazio) o **líquido** `total_final_centavos - credito_abatido_centavos` quando `estado_pagamento = 'integral'`. |
| 2.5 | Após `associar_agendamento_pre_venda_a_item`, `agendamentos.venda_id` e `venda_item_id` **preenchidos**, `modo_origem = 'credito_venda'`. |

---

## Fluxo 3 — Venda directa (sem agendamento prévio)

| # | Critério de aceitação |
|---|------------------------|
| 3.1 | `vendas.agendamento_contexto_id` deve ser **NULL** quando não há contexto de visita. |
| 3.2 | `venda_itens` deve refletir quantidade × preço snapshot; `total_final_centavos` na venda alinhado à soma após descontos conforme `calcular_totais_venda`. |
| 3.3 | Meios em `venda_pagamento_linhas.tipo_meio` ∈ `DINHEIRO_MBWAY`, `IBAN`, `CARTAO_CREDITO`, `CREDITO_LOJA` após migração E18. |

---

## Fluxo 4 — Cancelamento / ledger de crédito (E18)

| # | Critério de aceitação |
|---|------------------------|
| 4.1 | Crédito por cancelamento: inserção idempotente em `credito_movimentos` com `UNIQUE(referencia_tipo, referencia_id, tipo_movimento)` para o par (`agendamento`, `id`). |
| 4.2 | `vw_cliente_saldo_credito` (ou soma de movimentos) deve refletir o **saldo** esperado após crédito positivo e débitos `USO_VENDA`. |
| 4.3 | Agendamento em `CANCELADO` com política de buffer coerente com `devolver_ao_buffer` e regras de domínio. |

---

## Fluxo 5 — Analytics (E19) pós-operação

| # | Critério de aceitação |
|---|------------------------|
| 5.1 | Após `run_etl`, deve existir linha em `dw_fact_agendamento` por agendamento processado, com `carga_horaria_h` derivada de `hora_inicio`/`hora_fim` quando válidos HH:MM. |
| 5.2 | `dw_fact_venda`: para vendas com `estado_pagamento = 'pendente'`, `receita_ltv_real_centavos = 0`; para outras, valor coerente com min(liquidado, esperado) e ledger. |
| 5.3 | `dw_cliente_kpi.cliente_id` como chave; `receita_ltv_real_total_centavos` agregada consistente com soma das contribuições LTV por cliente em `dw_fact_venda`. |

---

## Referência rápida — ordem da «Jornada do Herói» (stress E2E)

1. `cadastrar_cliente`  
2. `criar_agendamento_pre_venda` (sessão + colaborador)  
3. `registrar_venda` (integral, contexto = agendamento, linha = mesmo serviço)  
4. `associar_agendamento_pre_venda_a_item`  
5. `run_etl` (batch) + verificação opcional `dw_cliente_kpi` / `PRAGMA integrity_check` no ficheiro de teste  

---

## Execução — suíte stress (`tests/e2e_stress_test.py`)

- Relatório: `tests/last_stress_report.txt` (gerado após cada corrida; ficheiro no `.gitignore`).
- `python tests/e2e_stress_test.py` — defeito **1000** iterações da jornada (definir `E2E_STRESS_HERO_ITERATIONS` para ajustar).
- `pytest tests/e2e_stress_test.py` — defeito **35** iterações (`E2E_STRESS_HERO_ITERATIONS` também aplica).

---

*E20 — Fortaleza Operacional (resiliência total). Documento vivo: actualizar quando novos fluxos forem introduzidos.*
