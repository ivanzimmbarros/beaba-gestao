# 04 — Desenho lógico (Arquiteto / EQUIPE)

**Demanda:** `2026-04-07_E12_refatoracao_painel_operacional`  
**Data:** 2026-04-07

---

## 1. `status_demanda.json` — campos adicionais

| Chave | Tipo | Obrigatório | Uso |
|:---|:---|:---:|:---|
| `fase_governanca` | string (`A`–`F` ou `—`) | não | Fase activa do Fluxo oficial para a demanda corrente. |
| `pc_foco` | string \| null | não | PC em destaque (ex. `PC7`). |
| `percurso` | string | não | `normal` \| `correccao`. |
| `ultima_entrega_marco` | string | não | Último marco de produto encerrado (ex. `E11`). |
| `fases_resumo` | array de objetos | não | `{ "id", "label", "pcs", "estado" }` com `estado` ∈ `feito`, `curso`, `pendente`, `correccao`. |
| `diario_bordo_resumo` | array de strings | não | Linhas curtas para o ecrã Streamlit (espelho executivo do Diário do Painel). |

Leitores antigos ignoram chaves desconhecidas. A UI usa defaults se faltar `fases_resumo` (grelha genérica `pendente`).

---

## 2. `PAINEL_OPERACIONAL.md`

- Secções **1–4** executivas: Torre (Mermaid + tabela), Estado actual, Diário E01–E11, Como pedir evolução.  
- **Apêndices** numerados: retrabalhos, esclarecimento ficheiro normativo, PC1–PC13, CI, 15 etapas, concordância, histórico longo, anexos E09–E06, glossário, fluxo textual.

---

## 3. `page_fluxo_gestao.py`

- Funções puras para derivar ícone/cor por `estado`.  
- Layout: Torre (`st.columns(6)`), métricas, `diario_bordo_resumo`, expanders para pendente/PCs/falha/JSON.  
- Sem `pandas` / `numpy`.

---

## 4. Testes

- `test_governanca.py`: validar presença e forma mínima de `fases_resumo` quando existir; chaves base inalteradas.
