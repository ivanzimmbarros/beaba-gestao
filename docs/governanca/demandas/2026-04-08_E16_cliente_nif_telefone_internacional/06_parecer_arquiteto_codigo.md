# 06 — Parecer Arquiteto (código)

**Demanda:** `2026-04-08_E16_cliente_nif_telefone_internacional` · **2026-04-08**

## Leitura técnica (referência `develop`)

- **`nif.py` / `telefone.py`:** alinhados ao [`04_desenho_logico.md`](04_desenho_logico.md) — módulo 11, doc. internacional, E.164 + legado BR/PT.
- **`country_dial_codes.py` / `telefone_widgets.py`:** separação UI vs domínio; `preencher_session_telefone_de_e164` coerente com edição em Vendas.
- **`cliente.py`:** orquestração e transacções mantidas; `FilhoInput` com data opcional e recálculo de idade conforme desenho.
- **`connection.py`:** colunas novas + migração `cliente_contatos_emergencia` (remoção CHECK 11 dígitos) — necessária para E.164 nas emergências.
- **Risco residual:** `IntegrityError` em `cadastrar_cliente` continua com mensagem genérica «contacto duplicado» — aceitável; UNIQUE só em `whatsapp`.

## Decisão

**FAVORÁVEL** — sem veto técnico. Próximo: Analista (`07`) e QA.

**Referência de código:** commits `64f28e8` / `0de294c` (implementação E16 + ajuste PAINEL).
