# 04 — Desenho lógico — E11 — Pré-venda na agenda

**Demanda:** `2026-04-06_E11_pre_venda_agenda`  
**Autor:** EQUIPE (Arquiteto)  
**Data:** 2026-04-06  
**Base normativa:** [`02_desenho_funcional.md`](02_desenho_funcional.md) (aprovado).

---

## 1. Objectivo técnico

Permitir **`agendamentos`** em modo **`pre_venda`** (`venda_id` / `venda_item_id` nulos até fecho), preservar o fluxo **`credito_venda`** existente, suportar **associação** a linha de venda após `registrar_venda`, e opcionalmente **`vendas.agendamento_contexto_id`** para vendas adicionais (UC-B).

---

## 2. Esquema relacional (SQLite)

### 2.1 Tabela `agendamentos`

| Coluna | Tipo | Regra |
|:---|:---|:---|
| `modo_origem` | `TEXT NOT NULL` | `CHECK (modo_origem IN ('credito_venda', 'pre_venda'))`. **Default** na migração: `'credito_venda'` para todas as linhas existentes. |
| `venda_id` | `INTEGER` | **NULL** permitido **sse** `modo_origem = 'pre_venda'`; **NOT NULL** obrigatório **sse** `modo_origem = 'credito_venda'`. |
| `venda_item_id` | `INTEGER` | Idem. |
| `preco_referencia_centavos` | `INTEGER NULL` | Opcional; `NULL` ou `>= 0`. Preço congelado na marcação (resposta a Q1 do funcional: quando preenchido = congelado; quando `NULL` = usar catálogo no fecho). |
| `tipo_origem` | `TEXT NOT NULL` | Mantém enum actual (`sessao_avulsa`, `pacote`, `coworking`, `evento`). Em **`pre_venda`**, derivar de `servicos.natureza` + `pacote_sessao_id` com a **mesma** lógica que `_tipo_origem_para_natureza` / `_servico_ocorrencia` — **sem** novo literal `pre_venda` no CHECK. |

**CHECK composto (recomendado na tabela nova):**

```sql
CHECK (
  (modo_origem = 'pre_venda' AND venda_id IS NULL AND venda_item_id IS NULL)
  OR
  (modo_origem = 'credito_venda' AND venda_id IS NOT NULL AND venda_item_id IS NOT NULL)
)
```

**`pacote_sessao_id`:** em **`pre_venda`**, **primeira entrega (MVP):** **proibir** pacotes — `pacote_sessao_id IS NULL` e validação de domínio: natureza do `servico_id` ∈ {`Sessão`, `Coworking`, `Evento`}. Pacote + pré-venda fica **E11.2** (alinhado a Q2 do funcional).

### 2.2 Tabela `vendas`

| Coluna | Tipo | Regra |
|:---|:---|:---|
| `agendamento_contexto_id` | `INTEGER NULL` | `FOREIGN KEY (agendamento_contexto_id) REFERENCES agendamentos(id) ON DELETE SET NULL`. Opcional; preenchido quando a venda é registada **no contexto** de uma visita (UC-B ou fluxo guiado a partir do detalhe do agendamento). |

**Nota:** não há FK de `agendamentos` → `vendas` no momento da criação do `pre_venda`; a FK `vendas.agendamento_contexto_id` → `agendamentos` é segura (agendamento já existe).

### 2.3 Migração SQLite

O `CREATE TABLE` actual fixa `venda_id` / `venda_item_id` **NOT NULL**. SQLite **não** remove NOT NULL com `ALTER COLUMN`.

**Procedimento** (função dedicada em `connection.py`, executada uma vez após detecção de esquema legado):

1. `BEGIN TRANSACTION`
2. `CREATE TABLE agendamentos_e11 (...)` com colunas e CHECK acima.
3. `INSERT INTO agendamentos_e11 SELECT ...` mapeando linhas existentes: `modo_origem = 'credito_venda'`, `preco_referencia_centavos = NULL`, resto copiado.
4. Desactivar FK temporariamente ou ordem: `DROP TABLE agendamentos` (SQLite exige recriar `agendamento_colaboradores` FK — preferível: renomear `agendamentos` → `agendamentos_old`, criar `agendamentos`, copiar, recriar índices, `INSERT` em `agendamento_colaboradores` já apontam IDs estáveis se IDs preservados na cópia).
5. Estratégia segura: copiar `agendamentos` para `agendamentos_e11` com mesmo `id` (`INSERT ... SELECT` com ids), apagar `agendamento_colaboradores`, apagar `agendamentos`, renomear `agendamentos_e11` → `agendamentos`, recriar `agendamento_colaboradores` a partir de backup temporário ou `SELECT` guardado.

**Arquiteto recomenda:** implementar `_migrate_agendamentos_e11(cursor)` com teste de `PRAGMA table_info` — se `venda_id` já nullable, skip.

`_ensure_column` para `vendas.agendamento_contexto_id` após migração de agendamentos.

---

## 3. Máquina de estados (`agendamentos.status`)

| Transição | `pre_venda` | `credito_venda` |
|:---|:---|:---|
| `AGENDADO` → `CONFIRMADO` | Permitido | Igual ao actual |
| `AGENDADO`/`CONFIRMADO` → `CONCLUIDO` | **Bloqueado** se ainda `venda_id IS NULL` (recomendação funcional Q3) | Igual ao actual |
| `CONCLUIDO` | Só com `venda_id` / `venda_item_id` preenchidos e `modo_origem` actualizado para `credito_venda` | — |
| Cancelar | Igual; `devolver_ao_buffer` **ignorado** ou forçado a `0` quando `pre_venda` (não há crédito a devolver) | Igual ao actual |

---

## 4. Módulo `agendamento.py` — funções

| Função | Responsabilidade |
|:---|:---|
| `criar_agendamento_pre_venda` | Valida serviço (natureza MVP), intervalo horário, colaboradores; `INSERT` com `modo_origem='pre_venda'`, `venda_id`/`venda_item_id` NULL, `tipo_origem` derivado do serviço, `pacote_sessao_id` NULL. |
| `associar_agendamento_pre_venda_a_item` | Parâmetros: `ag_id`, `venda_item_id`. Valida agendamento `pre_venda` + estado editável; resolve `venda_id` a partir do item; valida `cliente_id` coerente com venda; `UPDATE` preenche FKs e `modo_origem='credito_venda'`. Não cria venda (fica a cargo de `registrar_venda` + esta chamada ou fluxo UI atómico). |
| `fechar_pre_venda_com_nova_venda` *(opcional wrapper)* | Orquestra: chamar `registrar_venda` (módulo venda) com dados do formulário + `agendamento_contexto_id` opcional; obter `venda_item_id` da linha criada; chamar `associar_agendamento_pre_venda_a_item`. Transaccão única na camada de aplicação (conn partilhada ou sequência com rollback). |

**Ajustes em funções existentes:**

- `criar_agendamento` (actual): manter só para `credito_venda`; ou ramo interno se `venda_item_id` presente.
- `listar_agendamentos` / `obter_agendamento`: incluir `modo_origem`, `preco_referencia_centavos`; `pagamento` = rotulo especial **«Pré-venda (sem venda)»** quando `pre_venda`.
- `saldo_bucket` / `_count_consumindo`: considerar apenas linhas com `venda_item_id NOT NULL` (já implícito se queries filtram por item).
- `_consome_credito`: agendamentos `pre_venda` **não** entram em contagem de bucket (query join ou `WHERE venda_item_id IS NOT NULL`).

---

## 5. Módulo `venda.py`

- `registrar_venda`: aceitar parâmetro opcional `agendamento_contexto_id: int | None`; `INSERT` em `vendas` com a nova coluna.
- Validação: se `agendamento_contexto_id` preenchido, `SELECT` agendamento — `cliente_id` da venda deve igualar `agendamentos.cliente_id`.

---

## 6. UI (`page_agendamentos.py`, `page_vendas.py`)

- **Novo fluxo** «Marcar pré-venda»: sem selector de bucket; escolhe cliente, serviço (filtrado MVP), data/hora, colaboradores; checkbox ou campo opcional preço referência.
- **Badge** `pre_venda` na listagem.
- **Acção** «Fechar venda»: expander que reutiliza campos do painel de vendas (ou `st.session_state` + `switch_page` se o projecto adoptar navegação) com `agendamento_contexto_id` e pós-processamento `associar_*`.
- **Acção** «Nova venda nesta visita»: pré-preenche cliente + `agendamento_contexto_id` na página de vendas.

*(Detalhe de widgets — Fase C / Dev.)*

---

## 7. Relatórios (`relatorios.py`)

- Nenhuma alteração obrigatória na **receita** (base `vendas`).
- Opcional E11: métrica **«Compromissos pré-venda futuros»** — `COUNT(*)` onde `modo_origem='pre_venda'` e `data_agendamento >= hoje` e `status IN ('AGENDADO','CONFIRMADO')`.

---

## 8. Testes (alvo para `tests/test_agendamento.py` e `test_venda.py`)

1. Migração: DB legado com 1 agendamento → após `create_tables` colunas e CHECK satisfeitos.
2. `criar_agendamento_pre_venda` sucesso (Sessão).
3. Pacote ou natureza inválida → falha.
4. `associar_agendamento_pre_venda_a_item` após `registrar_venda` — modo passa a `credito_venda`.
5. `alterar_status` → `CONCLUIDO` com `pre_venda` sem venda → falha.
6. Cancelar `pre_venda` — sem erro; buffer inalterado para buckets do cliente.
7. `registrar_venda` com `agendamento_contexto_id` inconsistente com cliente → falha.

---

## 9. Rastreabilidade UC ↔ técnico

| UC | Realização |
|:---|:---|
| UC-A | `criar_agendamento_pre_venda` |
| UC-A2 | `registrar_venda` + `associar_agendamento_pre_venda_a_item` (transaccional) |
| UC-B | `registrar_venda(..., agendamento_contexto_id=ag_id)` |

---

## 10. Parecer Arquiteto (encerramento Fase B — passo 9)

Desenho lógico **consistente** com o funcional aprovado; MVP **exclui pacote** em `pre_venda`; migração documentada para SQLite legado. **Pronto para validação Analista** (`05`) e **Fase C** (Dev).
