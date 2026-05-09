# Épico 24 — Colaboradores: Setor 5 «Relatórios de realização e repasse»

**ID:** `2026-05-09_E24_colaboradores_setor5_relatorios_repasse`  
**Nome curto:** E24 — Relatórios Colaboradores (realização + repasse)  
**Fase 0 (actual):** Plano faseado, inventário obrigatório de requisitos e conformidade institucional — **sem alteração a código de produção** até **aprovação formal explícita do Diretor** no chat (ex.: **CONFIRMO** / **PROSSIGA** por fase ou por tranche acordada).

---

## 0. Âmbito mandatório (checklist integral — nada fica de fora)

| # | Requisito mandatório | Onde será tratado nas fases |
|---|----------------------|------------------------------|
| M1 | Novo **Setor 5** na página **`Colaboradores`** (`render_page_colaboradores` / módulos associados), coerente com Constituição Visual Sereno (ilha, hierarquia, sem violar contratos existentes dos setores 1–4). | Fase 2–3 |
| M2 | **Relatórios específicos** orientados à **realização por colaborador** e ao **cálculo / evidência de repasse** no período. | Fase 1–4 |
| M3 | Selecção obrigatória de **período** (data início — data fim, sem ambiguidade; ver decisões §8). | Fase 2 |
| M4 | Três **modos de filtro mutuamente exclusivos** (uma dimensão activa por geração de relatório): **Especialidade** | **Serviço** | **Colaborador**. | Fase 2 |
| M5 | Após escolher o modo, lista de opções **dependente do modo** — UI tipo **combo** alinhada ao Streamlit disponível (**`st.selectbox`** para o modo OU padrão documentado equivalente Sereno-approved). | Fase 2 |
| M6 | A lista de valores do modo seleccionado deve permitir **`multiselect`** — **várias linhas opcionais seleccionadas em simultâneo**. | Fase 2 |
| M7 | Acção **«Gerar relatório»**: (a) construir dataset; (b) apresentar **tabela visual** na UI com todas as linhas do período e filtros; (c) disponibilizar **botão de download PDF** por baixo da tabela. | Fase 3–4 |
| M8 | **PDF obrigatório em orientação landscape (paisagem)** para maximizar colunas na grelha. | Fase 4 |
| M9 | Corpo do PDF: **primeiro bloco textual/diagramático** — descrição **clara de todos os filtros** aplicados + **resumo executivo** (ver §3.2 texto exacto esperado); **depois** tabela principal com os dados. | Fase 4 |
| M10 | Resumo inicial no PDF deve incluir, **no mínimo**: total de **atendimentos** no período; **quebra do total por especialidade**; **quebra por serviço habilitado** no contexto do relatório; **total de repasse** no período; quebra dos **valores de repasse por especialidade**; quebra dos **repasses por serviços habilitados**; distinção **já pago** vs **pendente de pagamento** (montantes e, se aplicável, contagens ou totais lado a lado). | Fase 4 |
| M11 | Tabela principal: **todas as linhas** de atendimentos no período cruzadas com filtros; colunas **nesta ordem** (rótulos afinados para UX — ver §4) com equivalência funcional garantida. | Fase 3–4 |
| M12 | O PDF deve refletir **as mesmas colunas** e **a mesma ordem** da tabela de ecrã (+ bloco resumo anterior). **Nenhuma coluna obrigatória omitida.** | Fase 4 |
| M13 | **Modelo visual** do PDF **e** da zona de relatório na página: **elegante, moderno, profissional** — não é aceitável apenas «despejar uma tabela crua». Deve comunicar instituição credible (tipografia consistente, cabeçalho de documento, secções claras). | Fase 4–5 |
| M14 | Conformidade **`.cursorrules` / Constituição Sereno**, testes (**unit + contrato UI + smoke + E2E slice** onde aplicável), **backup/E17** se houver migrações ou dados críticos novos expostos, **pytest 100%** pré-push desenvolvimento. | Fase 6–7 |

**Declaração de completude:** A secção §3 replica em prosa todos os pontos da tabela anterior; as fases seguintes fazem closure explícito de M1–M14 em critérios de aceite verificáveis.

---

## 1. Contexto técnico de linha de base

- **Página-alvo:** `src/ui/page_colaboradores.py` — hoje inclui pesquisa, mapa da equipa, disponibilidade (`render_colaboradores_disponibilidade_setor`), ficha em expander e dados de parceria. O **Setor 5** será um bloco novo (expander/island master alinhado a `inject_constituicao_col_page`), **mantendo ordenação UX** já acordada com mapa/ficha.
- **Dados centrais (operacional-financ.E18/E19):**
  - `agendamentos` — data/hora de atendimento, `servico_id`, `cliente_id`, estados vários (`concluído`, `pendente_repasse`, etc. — confirmar lista exacta nas fases 1–2).
  - `agendamento_colaboradores` — ligação N:N colaboradores ao agendamento, `ordem`.
  - `colaboradores`, `servicos`, `especialidades` (via catalogo/colaborador serviços habilitados).
  - **`colaborador_servicos`** — `percentual_centesimos` (repasse pactuado por serviço/colaborador; base do «percentual padrão de repasse acordado»).
  - **`repasse_linhas`** — `valor_repasse_centavos`, `status_repasse` (`PENDENTE_REPASSE` \| `REPASSE_PAGO`), `base_calculo_centavos`, `percentual_bp`, `agendamento_id`, `colaborador_id`.

**Contrato técnico a fechar na Fase 1 (sem fugas):**

- Critérios de inclusão de linha na tabela: só agendamentos **concluídos / com repasse gerado**, ou outros estados definidos pelo produto documentado antes de código.
- Regra quando um agendamento tem **vários colaboradores**: cada linha de `repasse_linhas` já materializa contribuições por par (agenda↔colab); relatório trabalha sobre **esta granularidade**.
- Harmonização **`percentual_bp`** entre `repasse_linhas` vs `colaborador_servicos` em caso divergência — critério de verdade registado antes de relatório.

Referências obrigatórias de código existente durante desenho: `src/modules/agendamento.py` (`_gerar_repasse_linhas`, `_base_repasse_centavos`), `src/ui/page_financeiro.py` (repasses já exibidos), funções tipo `listar_repasses` em módulos financeiros.

---

## 2. Objectivos de negócio (síntese)

| # | Objectivo |
|---|-----------|
| A | Permitir auditoria rápida e **relacionamento colaborativo** («medir evolução das relações com os colaboradores») através de dados **objectivos**. |
| B | Documento legal-institucional (PDF) utilizável externamente (**landscape**) com **filtros explícitos** e ** números coerentes** com ERP interno repasse_linhas/agendamentos. |
| C | Evitar segunda fonte manual: totais PDF = soma ou agregações explícitos das mesmas queries que sustentam Streamlit DataFrame—**zero deriva não justificada**. |

---

## 3. Funcionalidade esperada — derivação obrigatória dos M1–M14

### 3.1 Filtros (UI antes de gerar)

1. **Período**: intervalo inclusivo definido pelo utilizador `[data_ini, data_fim]` (+ horários se decidido §8 — default provável 00:00–23:59 fuso local documentado).
2. **Dimensão do filtro**: exactamente uma opção dentre:
   - **Por especialidade** — multiselect de especialidades (apenas registos onde o serviço do atendimento mapeia para uma das especialidades escolhidas).
   - **Por serviço** — multiselect de serviços (lista completa contextualizada pela natureza/catalogo atual).
   - **Por colaborador** — multiselect de colaboradores (apenas linhas onde o par agendamento–colaborador pertence aos seleccionados).
3. Estados de interface:
   - Se multiselect vazio antes de gerar → **bloqueio** com mensagem clara (fail-safe); não há dataset ambíguo «todos sem aviso».

### 3.2 Resumo executivo inicial no PDF — conteúdo mínimo (M9–M10)

Ordenação sugerida no documento (ajustável no design final, mas todos os **blocos obrigatórios** devem estar presentes e legíveis):

1. Cabeçalho institucional (nome app, tipo de relatório, data de emissão, período solicitado textual).
2. **Filtros activos réplica**: modo (Especialidade | Serviço | Colaborador) + valores escolhidos (lista nominativa ou ids + nomes quando relevante LGPD-safe).
3. **Métricas globais período:**
   - Count total de linhas relatório ou total de «atendimentos» segundo definição de negócio (unicidade por `(ag_id,colab_id,line_id)` registado).
   - Soma valores **totais linha/atendimento** (coerência com definido na Fase 1).
   - Soma valores **repasse devido**.
   - Soma valores **pagos vs pendentes** (duas metas lado a lado + percentagem opcional não obrigatória).
4. **Quebra por especialidade** (counts e valores totais-atendimento; repasses totais nesta especialidade pagos vs pendentes).
5. **Quebra por serviço habilitado** neste contexto (mesma estrutura de somas).
6. Nota técnica one-liner: «Base de dados beaba SQLite / referência período TZ» se necessário auditoria ISO.

### 3.3 Tabela principal PDF + ecrã (M11–M12, ordem canónica)

Colunas obrigatórias **nesta sequência**:

| Ord | Conceito obrigatório | Rótulo sugerido (PT, curto) |
|-----|----------------------|-------------------------------|
| 1 | Nome completo colaborador | **Colaborador** |
| 2 | Data e hora atendimento | **Quando** |
| 3 | Especialidade ligada ao serviço | **Área / Especialidade** |
| 4 | Serviço prestado | **Serviço** |
| 5 | Nome completo cliente | **Cliente** |
| 6 | % repasse pactuado (serviço/colaborador) | **Repasse pactuado (%)** |
| 7 | Valor monetário global da linha de atendimento usada na base de repasse | **Valor atend.** |
| 8 | Montante direito ao colaborador segundo repasse_linhas derivado | **Repasse (.€)** ou **Repasse (€)** documentado formato |
| 9 | Estado pago pendente ligado ao repasse_linhas/status | **Estado pgto.** |

*Não é obrigatório repetir verbatim estes labels se houver nomenclatura interna institucional, mas deve existir glossário §9 no documento QA final com mapeamento 1-a-1 entre label visível ↔ campo fonte.*

### 3.4 Estética institucional (M13 — não apenas tabela cru)

Critérios mínimos de aceite aceitabilidade Diretor:

- PDF: **landscape**, margens definidas (≥14mm segurança impressão), zebra rows ou bandas sutis cores Sereno institucional (ver cores existentes tema), tipo legível (~9–10pt dados, 13–14 títulos), quebras de página com repetição de cabeçalho de tabela onde necessário (`repeat header row` se biblioteca PDF suportar).
- Secções com **divider** textual ou rule line clara («Resumo executivo», «Quebras analíticas», «Detalhe linha-a-linha»).

---

## 4. Tratamento obrigatório de qualidade / governança

- **`tests/` novo coverage:** módulo agregações + função puras de relatório (>80% cenários filtros período + multimodo + multiselect vazio erro).
- **Contrato:** `tests/col_visual_sereno.py` OU extensão `col_ui_contract` garantindo texto Setor 5 + botão PDF existe em render admin path (adaptar permissões esperadas quando definidas).
- **Smoke UI:** entrada que page colaboradores contém marcadores («Setor 5» texto estabilizado).
- **E2E stress slice fino:** relatório modo colaborador 1 período sintético (usar BD isolada monkeypatch)—adicionado em `tests/e2e_stress_test.py` na fenda do épico.
- **LGPD minimização:** relatório cliente inclui apenas nome já exposto pela operação habitual; política dados sensíveis reforço em cabeçalho PDF («Uso interno»).
- **Backup / migrations:** se novas vistas Materializadas / colunas apenas consulta — opcional SQLite VIEW; migrações `connection.py` + inventário `.cursorrules` se alterar schema físico real.

---

## 5. Fases de execução (só iniciar após cada portão APPROVED)

### Fase 0 — Este plano (**actual**)

- Entrega ficheiro atual + entrada `status_demanda.json`.
- **Gate:** texto **CONFIRMO** Diretor aceitando faseamento §5 e decisões baseline §8 placeholders.

### Fase 1 — Modelo dados & especificação de query

Atividades obrigatórias:

| Actividade | Artefactos |
|-----------|-------------|
| ERD lógico de junção relatório (`SQL` texto / diagrama texto) | apêndice opcional dentro deste dossier `02_queries_relatorio_repasse.sql` stub |
| Definições fechamento: estados inclusão exclusão agenda | atualização dossier §8 resolvido definitivamente antes de código |
| Funções puras `src/modules/colaboradores_relatorio.py` (**novo fich recommended**) | stubs + tipo hints + docstrings comportamento filtros |

Critérios aceite: **pytest apenas lógicas puras** sem Streamlit primeiro.

### Fase 2 — UI Setor 5 filtros Streamlit Sereno

- Expander novo **ordenado fisicamente** após último setor operacional atual (determinar ordenação factual no PR descrevendo onde insere relativamente disponibilidade + mapa + ficha).
- Componentes período + select modo + multiselect opções gerados por funções `listar_*` reutilizado catálogo existente sempre que possível.
- Botão gerar só activo se período válido + multiselect não vazio.
- Spinner & feedback erros utilizador.

Gate aprovação UI estática antes de dados massivos pode ser modo mock.

### Fase 3 — Tabela resultado e validações de negócio

- `pandas` DataFrame ordenado deterministicamente (datas asc + colaborador + cliente + id linha)—document order key.
- `st.data_editor` apenas leitura (padronizado com rest project) ou dataframe normal + garantia sem edição inadvertida.
- Resumo rápido on-screen opcional (**não obrigatório** se já duplicará PDF textual; mas UX recomenda micro métricas 3 KPI acima da tabela—decisão Diretor Fase a Fase).

### Fase 4 — Geração PDF landscape + paridade dados

Seleccionar tecnologia antes de primeira linha código **e gravar**:

| Opción | Pros | Contras |
|--------|------|---------|
| **ReportLab / platypus** | controle máximo layout programa | código verboso |
| **WeasyPrint + HTML modelo** | design modern rápido | dependência Cairo Windows potencial dor |
| **fpdf2** | leve | layout complexo trabalhoso |
| **pandas Styler → PNG** ❌ não PDF landscape adequado institucional | — | ❌ rechaz formal |

Critérios aceite: byte-for-byte regressão opcional hashing template + snapshot primeiro PDF golden file em `tests/fixtures/report_sample.pdf.hash` apenas se Diretor quer.

Botão PDF: mime `application/pdf`; filename `bea_rel_colaboradores_YYYYMMDD_HHmm.pdf`.

### Fase 5 — Polimento Sereno institucional

- Harmonizar paleta Verde Sereno (RGB extraídas `styles_theme`).
- Íconologia secções («Resumo», «Detalhes») — apenas vector PDF built-in texto + linhas geométricas (sem raster externa não versionada obrigatória).

### Fase 6 — Testes expansão conforme protocolo fortaleza

- Pytest novo + atualização coberturas fin_ui não necessário diretamente; focus col*.
- Smoke + E2E slice e docstrings backups scripts referenciados segundo norma projeto.

### Fase 7 — QA fecho & governança

- Demonstração lado Diretor: três relatórios reais exemplo ( modo esp / serv / col ).
- Stress ≥1000 iterações se activar alteração navegação crítica segundo `protocolo_fortaleza` do JSON atual.
- Atualização `ultima_actualizacao_iso` + marca épico estado **CONCLUÍDO** ou **REVISÃO** conforme resultado.

---

## 6. Critérios de aceite formais consolidados

1. ✅ Setor 5 operacional apenas após todas as permissões esperadas decididas §8-perfis RBAC (**default provável todos roles actua Colaboradores** — confirm).
2. ✅ Paridade valores: soma(DataFrame campo repasse)==soma(repasse_linhas filtradas) ±0 cêntimos.
3. ✅ Multiselect vazio ⇒ bloqueado.
4. ✅ PDF sempre landscape + contém resumo + tabela todas colunas obrig M11.
5. ✅ Nenhum regressão pytest existente falhando ao fechar épico branch.

---

## 7. Riscos pré-identificados (mitigação inicial)

| Risco | Mitigação Fase inicial |
|-------|-----------------------|
| Períodos longíssimos → timeouts Streamlit/PDF grande | paging virtual UI + chunked PDF gerado stream / limitador aviso período (>12 meses configurável Diretor guard-rail §8 |
| Divergências repasse regenerate vs histórico | Fonte oficial = `repasse_linhas`; nunca recomputação silenciosa paralela inconsistente linha relatório vs ledger |
| Timezone inconsistência relatório | Fixar TZ documentado («Europe/Lisbon por defeito») antes de primeira query |
| Multiselect opções grandes (100+ services) performance | ordenação alfabética + campo busca texto secundário (st multiselect com default search limit—avaliado Fase2) |

---

## 8. Decisões a fechar obrigatoriamente ANTES primeira linha de código (Fase1 kickoff checklist)

Liste fechável com Diretor quando ele der **CONFIRMO** Fase ≥1:

- [ ] **RBAC**: quais perfis vê Setor 5 (admin apenas? também `colaborador` limitado próprios dados?).
- [ ] **Timezone** relatório oficial.
- [ ] **Inclusão estado agendamentos** (lista enumerada permissiva/blocante).
- [ ] Formato valores monetários (€ com duas casas; locale `pt_PT`).
- [ ] Biblioteca PDF escolhida e dependência registada (`requirements.txt` rev bump).
- [ ] Glossário público institucional título relatório («Relatório de realização profissional e repasses» exemplo).
- [ ] Threshold alerta período volumétrico.
- [ ] Ordem física inserção Setor vs Disponibilidade (proposta: disponibilidade permanece topo operacional dia-a-dia; relatórios ficam antes ou depois Diretor prefere?). **Marcar na aprovação.**

---

## 9. Estado

**Estado épico:** Fase 0 — **plano apenas**. Nenhuma implementação iniciada até **aprovação formal explícita** do Diretor (por texto no chat autorizando fase seguinte conforme política projeto).

---

## 10. Pedido oficial ao Diretor (fecho Fase 0)

Confirme por texto:

1. **Faseamento** §5 (Ajustar ou aceitar textualmente).  
2. **Lista §8 decisões obrigatórias** antes Fase 1 — preencher ou autorizar placeholders propostos.  
3. **Autorização** para escrever Fase 1 após comando **CONFIRMO** ou **PROSSIGA FASE 1**.
