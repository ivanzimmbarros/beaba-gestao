# 07 — Parecer Analista (código)

**Demanda:** `2026-04-08_E16_cliente_nif_telefone_internacional` · **2026-04-08**

## Alinhamento ao funcional / lógico

- NIF PT e documento internacional com flag explícita; mensagens de erro em PT.
- Contacto principal e emergências em E.164; pesquisa de cliente aceita legado e `+…`.
- Filhos: data de nascimento opcional com prioridade da data sobre idade, como em [`04_desenho_logico.md`](04_desenho_logico.md).
- UI **Clientes** (menu) e **Vendas** (cadastro / edição) cobrem os mesmos contratos.

## Plano de testes

Actualizado em [`docs/CADERNO_TESTES_MASTER.md`](../../../CADERNO_TESTES_MASTER.md) (secção E16, suite **56** testes).

## Decisão

**APROVADO** — seguir para fase **QA** (execução massiva `pytest` + selo `09`).

**Ordem no Git:** `develop` com implementação + `06` (Arquiteto); este `07` encerra critério Analista para **PC7**.
