# 02 — Desenho funcional — E11 — Pré-venda / venda no atendimento / serviços adicionais

**Demanda:** `2026-04-06_E11_pre_venda_agenda`  
**Autor:** EQUIPE (Analista)  
**Data:** 2026-04-06  
**Estado:** **aprovado** pelo Diretor (2026-04-06 — «PROSSIGA» no Cursor); ver [`03_confirmacao_diretor.md`](03_confirmacao_diretor.md).

---

## 1. Contexto do sistema actual

### 1.1 Vendas (`venda.py`, `page_vendas.py`)

- Registo de `vendas` + `venda_itens` + pagamentos e recebimentos previstos.
- `estado_pagamento`: `integral` | `pendente` | `parcial` | `parcelado` — com regra de reconciliação **soma(meios) + soma(previstos) = total_final**.
- Já é possível **registar uma venda com pagamento totalmente previsto** (`pendente` ou parcelas futuras), ou seja, **há venda no sistema antes do dinheiro entrar**.

### 1.2 Agendamentos (`agendamento.py`, `page_agendamentos.py`)

- Cada `agendamento` **exige** `venda_id` e `venda_item_id` **NOT NULL** (FK na base).
- O agendamento **consome crédito** de uma linha de venda existente (`saldo_bucket`).
- **Conclusão:** hoje **não existe** agendamento “solto”; não há entidade de agenda equivalente a **expectativa de venda** sem pelo menos uma linha de `venda_itens`.

### 1.3 Lacuna

Os cenários A e B exigem:

- **Cenário A:** marcar **antes** de existir venda (ou antes de venda economicamente “fechada” ao critério do negócio).
- **Cenário B:** no mesmo **contexto de visita** (agendamento concreto), registar **venda adicional** de forma **rastreável** e **operacionalmente simples**.

---

## 2. Casos de uso

| ID | Nome | Actor | Resumo |
|:---|:---|:---|:---|
| **UC-A** | Marcar sem venda fechada | Recepção / EQUIPE | Criar **compromisso de agenda** com cliente, serviço, colaboradores e janela horária **sem** `venda`/`venda_item` obrigatórios no momento. |
| **UC-A2** | Fechar venda no atendimento | Recepção | No dia (ou no fecho do atendimento), **gerar venda** (linhas, descontos, pagamento) e **associar** ao compromisso; transição de estados coerente com o fluxo actual. |
| **UC-B** | Serviços adicionais no dia de pagamento | Recepção | Com agendamento já ligado a venda (ou recém-fechado por UC-A2), **registar nova venda** (ou extensão acordada) **ligada à mesma visita** para auditoria e relatórios. |

---

## 3. Decisão de desenho recomendada (Analista)

### 3.1 Dois modos de origem do agendamento

Introduzir conceptualmente (e depois no modelo) o campo **`modo_origem_agenda`** (nome funcional; o Arquiteto fixará o nome SQL):

| Modo | Significado | Crédito / buffer |
|:---|:---|:---|
| **`com_credito_venda`** | Comportamento **actual**: nasce de `venda_item_id` com saldo. | Usa `saldo_bucket` como hoje. |
| **`pre_venda`** | **Compromisso** sem linha de venda no momento da marcação. | **Não** consome bucket; ocupa slot de agenda; preço pode ser **provisório** ou **à fecho**. |

**Regra:** um registo de agenda está **sempre** em exactamente **um** destes modos.

### 3.2 Porquê não “apenas venda pendente antes da marcação”?

Registar primeiro uma `venda` com `estado_pagamento = pendente` e **depois** agendar **já resolve parcialmente** o fluxo financeiro, mas:

- O negócio pediu explicitamente **agendamento sem venda consumada por detrás** (expectativa / pré-venda).
- Uma `venda` pendente **é** um documento de venda no sistema (útil para pipeline), mas **não** cumpre o requisito literal de **agenda sem linha de venda** se o Diretor quiser separar **“marcado”** de **“vendido”** nos relatórios e na operação.

**Proposta:** suportar **`pre_venda`** como modo **principal** do Cenário A; opcionalmente, na Fase 2, oferecer **atalho** “criar venda pendente + agendar” para quem preferir esse hábito de trabalho.

### 3.3 Fecho no atendimento (UC-A2)

Fluxo de ecrã sugerido (alto nível):

1. Na lista/detalhe de **Agendamentos**, filtro ou badge **«Pré-venda»** para compromissos `pre_venda`.
2. Acção **«Fechar venda / receber»** (apenas para estados `AGENDADO` ou `CONFIRMADO`, conforme política):
   - Abre **assistente** reutilizando a lógica do **Painel de Vendas** (cliente pré-preenchido, linhas sugeridas a partir do `servico_id` do compromisso e quantidade 1 por omissão, preço do catálogo ou preço gravado no compromisso).
   - Após `registrar_venda` com sucesso, o sistema **associa** o agendamento à `venda`/`venda_item` criados e **altera** `modo_origem_agenda` para **`com_credito_venda`** (ou remove flag de pré-venda), mantendo o **mesmo** `id` de agendamento (continuidade operacional).

**Política de estado:** após associação, o consumo de crédito para **essa** ocorrência deve refletir a regra actual (a ocorrência passa a contar como consumo da nova linha). Detalhe técnico em **Fase B** (`04_desenho_logico.md`).

### 3.4 Serviços adicionais (UC-B)

- No **detalhe do agendamento** (já com venda), acção **«Nova venda no contexto desta visita»**:
  - Abre `page_vendas` com **cliente** e, se existir, **referência ao `agendamento_id`** (novo campo opcional no cabeçalho da venda — ver §4).
- **Relatórios:** filtro ou dimensão **«Vendas ligadas a agendamento #N»** para auditoria (Fase B / E11 implementação).

### 3.5 Cancelamento e calendário

- **`pre_venda` cancelado:** não há devolução a “buffer de crédito” (não existia linha); apenas liberta slot; opcional motivo/nota.
- **Conflitos de horário:** reutilizar validações actuais de intervalo; eventual regra extra “colaborador indisponível” mantém-se.

### 3.6 Indicadores

- Novo indicador na área **Agendamentos** ou **Dashboards** (acordar prioridade na implementação): **«Compromissos pré-venda futuros»** (contagem / valor estimado se houver preço provisório).

---

## 4. Alterações de dados (alto nível — para desenho lógico)

**Proposta para o Arquiteto detalhar:**

1. **`agendamentos`:** tornar **`venda_id`** e **`venda_item_id`** **NULL** quando `modo = pre_venda`; acrescentar colunas de negócio, por exemplo:
   - `modo_origem_agenda` (`credito_venda` | `pre_venda`),
   - `preco_referencia_centavos` NULL (opcional — congelar preço na marcação),
   - eventual `moeda` / notas de proposta.
2. **`vendas`:** campo opcional **`agendamento_contexto_id`** NULL → FK para `agendamentos.id` (visitas que originam ou acompanham a venda adicional). **CHECK:** não obrigatório para todas as vendas.
3. **Tipo de origem em `tipo_origem`:** para `pre_venda` antes do fecho, pode ser necessário valor adicional (ex.: `pre_venda`) ou mapear para o `tipo_origem` “final” à data do fecho — **decisão na Fase B** (impacta listagens e ícones na UI).

**Migração:** registos existentes = `credito_venda` com FK preenchida; novos `pre_venda` com FK nula até fecho.

---

## 5. Impacto em relatórios

- **Receita:** continuar a basear-se em **`vendas` / `venda_itens`** (não contar `pre_venda` como receita).
- **Pipeline:** novo bloco ou filtro **«Pré-vendas / compromissos sem venda»** (opcional E11 ou E11.1).

---

## 6. Critérios de aceitação (rascunho para QA)

1. É possível criar um agendamento **`pre_venda`** sem `venda_item` no momento.
2. É possível **fechar venda** a partir desse agendamento e ficar **ligado** ao mesmo registo de agenda.
3. É possível registar **segunda venda** com **referência** ao agendamento da visita (UC-B).
4. Regressão: fluxo **actual** (venda → crédito → agendar) **mantém-se** sem alteração de comportamento para dados existentes.
5. Cancelamento de `pre_venda` não corrompe integridade nem inventa créditos inexistentes.

---

## 7. Fora de âmbito (sugestão)

- Assinatura digital / contratos.
- Pagamentos online automáticos.
- Multi-unidade.

---

## 8. Riscos e perguntas em aberto para o Diretor

| # | Pergunta |
|:---|:---|
| Q1 | Em **pré-venda**, o preço mostrado ao cliente deve ser **congelado** na marcação ou **sempre** o do catálogo no dia do fecho? |
| Q2 | Pode haver **pré-venda** para **Pacote** (múltiplas sessões) ou, na primeira entrega, limitar a **Sessão / Coworking / Evento** em linha única? |
| Q3 | **CONCLUIDO** sem venda associada deve ser **impedido** por regra? (Recomendação Analista: **sim**, bloquear conclusão até fecho ou marcar excepção administrativa.) |

---

## 9. Próximo passo

- **Diretor:** confirmação formal no chat (**CONFIRMO** / **PROSSIGA**) ou pedido de ajuste ao `02`.  
- Após aprovação: **Fase B** — Arquiteto elabora **`04_desenho_logico.md`** (esquema SQL, máquina de estados, funções e testes alvo).
