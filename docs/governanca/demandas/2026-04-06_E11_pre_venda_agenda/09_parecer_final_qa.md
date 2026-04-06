# 09 — Parecer final QA — E11

**Demanda:** `2026-04-06_E11_pre_venda_agenda`  
**Data:** 2026-04-06

---

## Execução

| Verificação | Resultado |
|:---|:---|
| `python -m pytest tests/ -v` | **49 passed** (regressão completa) |
| Escopo | `test_agendamento.py` (E11 + legado), `test_venda.py`, restantes módulos |

## Observações

- Migração E11 coberta por `test_schema_agendamentos_tem_modo_origem` e fluxos pré-venda.
- Recomendação operacional: **smoke manual** Streamlit — criar pré-venda, ir a Vendas, fechar com linha do mesmo serviço, confirmar modo `credito_venda` na lista.

---

## Selo QA

**APROVADO POR: QA (EQUIPE)**  
**Data:** 2026-04-06  
**Evidência Git:** commit de governança que inclui este parecer + estado alinhado em `develop`.

**Mensagem Git sugerida:** `selo(qa): E11 pytest 49 PC11`
