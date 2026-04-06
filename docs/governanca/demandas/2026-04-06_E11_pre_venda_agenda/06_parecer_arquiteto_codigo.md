# 06 — Parecer do Arquiteto (código) — E11

**Demanda:** `2026-04-06_E11_pre_venda_agenda`  
**Referência de código:** commit **`a6a9a8f`** em `develop` (implementação E11).

---

## Estado

**Concluído (PC5)** — parecer favorável com **selo Arquiteto**.

## Verificação técnica (resumo)

- **Migração SQLite:** recriação controlada de `agendamentos` com `PRAGMA foreign_keys=OFF`, cópia de `agendamento_colaboradores` e CHECK composto (`pre_venda` ↔ FKs nulas) — alinhado ao `04`.
- **Integridade:** `vendas.agendamento_contexto_id` com FK para `agendamentos`; validação de cliente na `registrar_venda`.
- **Domínio:** separação clara `credito_venda` / `pre_venda`; bloqueio de `CONCLUIDO` sem venda; cancelamento pré-venda sem buffer; `_count_consumindo` restrito a `credito_venda`.
- **UI:** fluxos «Fechar pré-venda» e «Nova venda nesta visita» via `session_state` + navegação para `page_vendas`; associação pós-venda por `servico_id`.
- **Testes automatizados:** regressão alargada (inclui migração, associação, rejeição pacote em pré-venda, contexto cliente).

---

## Selo Arquiteto

| Campo | Valor |
|:---|:---|
| **APROVADO POR** | **Arquiteto (EQUIPE)** |
| **Data** | **2026-04-06** |
| **Notas** | Código conforme [`04_desenho_logico.md`](04_desenho_logico.md); sem veto técnico. Próximo: validação de negócio (Analista, PC7) e QA (PC11). |

**Mensagem Git sugerida (rastreio):** `selo(arquiteto): E11 codigo aprovado PC5`
