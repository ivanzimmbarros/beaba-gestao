# 02 — Desenho funcional — E12 Refactoração Painel operacional (Torre de Controle + Diário de Bordo)

**Demanda:** `2026-04-07_E12_refatoracao_painel_operacional`  
**Data:** 2026-04-07  
**Autor:** EQUIPE (Analista)  
**Estado:** Proposta — **aguarda confirmação formal do Diretor** no Cursor (`CONFIRMO` / `PROSSIGA`).

---

## Objectivo

Transformar o [`docs/PAINEL_OPERACIONAL.md`](../../../PAINEL_OPERACIONAL.md) e o ecrã **Fluxo e governança** da app num par **coerente**: **comando executivo em cima**, **detalhe técnico em baixo** (apêndices), com **sincronismo** via [`status_demanda.json`](../../status_demanda.json).

---

## Secção 1 — Dashboard visual de fluxo («Torre de Controle»)

### 1.1 O que o Diretor deve ver «de relance»

- **Uma linha de fases A → F** do Fluxo oficial (alinhamento a [`FLUXO_SUCESSO_E_FALHA.md`](../../FLUXO_SUCESSO_E_FALHA.md)), cada fase com o **par de PCs** correspondente:

| Fase | Conteúdo (resumo executivo) | PCs (Git → Painel) |
|:---:|:---|:---:|
| **A** | Analista + Diretor — desenho funcional e confirmação | PC1 → PC2 |
| **B** | Arquiteto + Analista — desenho lógico | PC3 → PC4 |
| **C** | Dev + Arquiteto — 1.ª validação de código | PC5 → PC6 |
| **D** | Analista + Dev — código + plano de testes | PC7 → PC8 |
| **E** | QA — plano e execução massiva | PC9 → PC10 → PC11 → PC12 |
| **F** | Diretor — encerramento informado | PC13a → PC13b |

- **Indicador de posição:** qual fase está **activa** e, dentro dela, se estamos **antes do PC Git** (ímpar), **entre Git e Painel**, ou **após o par fechado**. Isso deve derivar de campos no JSON (ver §4) e ser mostrado com **estados visuais** consistentes:
  - **Concluído** — fase fechada (ambos os PCs do par, quando aplicável).
  - **Em curso** — fase actual (destaque).
  - **Pendente** — ainda não iniciada.
  - **Correção (FALHA)** — quando `falha` no JSON não for nulo ou existir flag explícita de percurso reverso (ver §4).

### 1.2 Forma visual no Markdown (Painel)

- **Opção preferida:** **grelha de 6 colunas** (A … F) com ícones Unicode leves (ex.: ○ pendente, ◐ em curso, ● feito) + **legenda** numa linha; alternativa ou complemento: **diagrama Mermaid** `flowchart LR` com nós A–F coloridos por estado (executivo, não código).
- **Linha adicional:** «**PC em foco:** PC*n*» (texto claro) para bater o olho sem abrir o apêndice.

### 1.3 Forma visual na app (Streamlit)

- **Mesma lógica** que o Painel: `st.columns(6)` com **rótulos curtos** (A–F + título de uma palavra: Desenho, Lógico, Código 1, Código 2, QA, Fecho) e **cor / emoji** por estado, alimentados pelo JSON.
- **Tooltip ou expander** «O que é cada fase?» com a tabela resumo (evitar poluir o topo).

---

## Secção 2 — Diário de Bordo (histórico)

### 2.1 Conteúdo

- **Lista ordenada** dos marcos **E01 … E11** (e linha «próximo» quando aplicável), cada entrada com:
  - **ID / nome curto** (ex.: E11 — Pré-venda na agenda).
  - **Uma linha** de valor entregue para o negócio (sem jargão de módulos).
  - **Data de referência** (encerramento ou último marco documentado), quando existir no repositório.
  - **Retrabalhos de processo:** sub-linha ou badge **«Retrabalho: N×»** com link para [`registo_retrabalhos`](../../../PAINEL_OPERACIONAL.md#5-registo-de-retrabalhos-reabertura-de-etapas) / ficheiro dedicado (ver §2.3), ou **«—»** se zero.

### 2.2 Falhas de processo (retrabalhos)

- **Fonte única recomendada:** manter a **tabela de retrabalhos** do Painel (já prevista na secção 5) e/ou criar **`docs/governanca/registo_retrabalhos.md`** se a tabela do Painel ficar grande — o Diário no topo **resume** (contagem ou «sim/não»); o detalhe fica na fonte única.
- Entradas do diário **não duplicam** pareceres técnicos completos — apenas **facto executivo** («reaberta fase B por veto Arquiteto», etc.).

### 2.3 Sincronismo Painel ↔ app

- O **Diário de Bordo** no **Markdown** é a versão «oficial» para Git/auditoria.
- A app pode mostrar o **mesmo conteúdo** de duas formas (a decidir na Fase B técnica, após aprovação):
  - **Mínimo:** texto **síntese** vindo de `status_demanda.json` → chave `diario_bordo_resumo` (lista curta de strings), mantido pela EQUIPE em cada PC de Painel; ou
  - **Alargado:** ficheiro `docs/governanca/diario_bordo_marcos.md` lido em runtime (mais complexo em deploy); **recomendação inicial:** **JSON para estado + Painel para narrativa longa**, app com **resumo** + link «ver Painel no repo».

---

## Secção 3 — `status_demanda.json` (extensão proposta)

Campos **novos ou refinados** (retrocompatíveis — chaves opcionais com defaults na UI):

| Chave | Tipo | Uso |
|:---|:---|:---|
| `fase_governanca` | string | `"A"` … `"F"` ou `"—"` |
| `pc_foco` | string \| null | Ex.: `"PC1"`, `"PC7"`, exibido na Torre |
| `fases_resumo` | array de objetos | Opcional: `{ "id": "A", "estado": "pendente\|curso\|feito", "label": "..." }` para pintar a grelha sem lógica duplicada na app |
| `percurso` | string | `"normal"` \| `"correccao"` (espelho legível de `falha`) |
| `diario_bordo_resumo` | array de strings | 3–8 linhas para o ecrã Streamlit |
| `ultima_entrega_marco` | string | Ex.: `E11` — linha de destaque no topo |

A EQUIPE **actualiza** estes campos nos **PCs de Painel** (paridade com o texto do `PAINEL_OPERACIONAL.md`). Documentar o schema no `README` de `demandas/` ou num bloco no próprio Painel (apêndice técnico).

---

## Secção 4 — `PAINEL_OPERACIONAL.md` — estrutura alvo (após aprovação)

1. **Cabeçalho** — data, última entrega (uma linha).
2. **Torre de Controle** — §1 visual (grelha + PC em foco + ligação ao JSON).
3. **Estado actual** — tabela mínima (demanda activa, responsável, próximo passo) — **sem** parágrafos longos.
4. **Diário de Bordo** — §2 (E01–E11 + retrabalhos resumidos).
5. **Como pedir evolução** — 4 bullets (mantém simplicidade).
6. **Apêndice A** — PC1–PC13 (tabela actual, ligeiramente compactada se necessário).
7. **Apêndices B+** — 15 etapas técnicas, marcos E06–E09 detalhados, glossário, histórico de commits longos (o que hoje está no meio do ficheiro **desce**).

**Nada de definições normativas removidas** — apenas **reordenadas** para o fim.

---

## Secção 5 — Streamlit `page_fluxo_gestao.py` (âmbito pós-PC2)

- **Bloco 1:** Torre A–F (dados JSON).
- **Bloco 2:** Métricas actuais (demanda, fase, responsável) — mantidas.
- **Bloco 3:** Diário (resumo JSON ou expander com texto).
- **Bloco 4:** Pendente / PCs concluídos / falha — mantidos, possivelmente em **expander** «Detalhe operacional» para não competir com a Torre.
- **Sem pandas/plotly** nesta página (evitar dependência pesada na governança).

**Restrição do Diretor:** implementação **só depois** de `03_confirmacao_diretor.md` e fecho **PC1 + PC2**.

---

## Critérios de aceite (E12)

- [ ] Topo do Painel é **lido em menos de 30 segundos** por um leitor não técnico e responde: «onde estamos no fluxo?» e «o que já demos?».
- [ ] PC1–PC13 permanecem **integralmente** acessíveis no mesmo ficheiro (apêndice).
- [ ] `status_demanda.json` suporta a **Torre** e um **resumo** de Diário na app.
- [ ] Streamlit **Fluxo e governança** reflecte Torre + Diário (mínimo resumo) sem regressão de leitura do JSON existente.
- [ ] `pytest` completo verde após implementação.

---

## Riscos e mitigação

| Risco | Mitigação |
|:---|:---|
| JSON demasiado complexo | Começar com `fase_governanca` + `pc_foco` + `diario_bordo_resumo`; adicionar `fases_resumo` só se necessário. |
| Duplicação Painel vs JSON | Regra: **Painel narra**; JSON **estado**; app **espelha estado** + resumo. |
| Carga de manutenção do Diário | EQUIPE actualiza Diário em **PC13b** e em encerramentos de demanda. |

---

## Pedido ao Diretor

Validar este desenho funcional com **CONFIRMO** ou **PROSSIGA** no chat. Após registo em **`03_confirmacao_diretor.md`** e **PC1→PC2**, a EQUIPE inicia a **Fase B** (desenho lógico / estrutura de ficheiros e JSON) e, em seguida, implementação conforme norma.
