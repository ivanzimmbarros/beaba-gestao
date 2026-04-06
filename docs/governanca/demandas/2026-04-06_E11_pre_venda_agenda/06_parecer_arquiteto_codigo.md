# 06 — Parecer do Arquiteto (código) — E11

**Demanda:** `2026-04-06_E11_pre_venda_agenda`  
**Data (rascunho Dev):** 2026-04-06

---

## Estado

**Pendente selo formal (PC5)** — a persona **Arquiteto** deve rever o diff em `develop` e emitir **APROVADO** ou pedido de correcção (FALHA).

## Evidência entregue pela Dev (EQUIPE)

- Migração SQLite `_migrate_agendamentos_e11_if_needed` + `CREATE` alinhado em [`connection.py`](../../../../src/database/connection.py).
- Domínio: [`agendamento.py`](../../../../src/modules/agendamento.py) (`criar_agendamento_pre_venda`, `associar_agendamento_pre_venda_a_item`, regras `CONCLUIDO` / cancelamento pré-venda); [`venda.py`](../../../../src/modules/venda.py) (`registrar_venda` → 3-tuple, `agendamento_contexto_id`).
- UI: [`page_agendamentos.py`](../../../../src/ui/page_agendamentos.py), [`page_vendas.py`](../../../../src/ui/page_vendas.py).
- Testes: **49** `pytest` em `tests/test_agendamento.py`, `tests/test_venda.py` (regressão completa).

---

## Parecer Arquiteto *(a preencher)*

| Campo | Valor |
|:---|:---|
| **APROVADO POR** | *(pendente — Arquiteto)* |
| **Data** | |
| **Notas** | |
