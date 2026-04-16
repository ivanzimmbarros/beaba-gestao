# Caderno mestre de testes — BeaBa Gestão

**Normativo:** a **EQUIPE** (persona Dev no passo **18** do **Fluxo oficial de governança** em [`governanca/FLUXO_SUCESSO_E_FALHA.md`](governanca/FLUXO_SUCESSO_E_FALHA.md)) **actualiza** este documento com o **plano de testes** de cada demanda. O **QA** (EQUIPE) valida, incrementa se necessário, e executa testes massivos. O Diretor **não** edita este ficheiro manualmente.

## 1. Testes automatizados (regressão obrigatória)

| Âmbito | Comando | Notas |
|:---|:---|:---|
| Suite completa | `python -m pytest tests/ -v` | Deve passar antes de **selo QA** e push em `develop`. |

## 1.1 ETAPA 0 — Relatório de side-effects e plano de cobertura (2026-04-16)

**Âmbito:** alterações recentes até 2026-04-16 (épico **Especialidades** — `especialidades` + `servicos.especialidade_id`; commits anteriores Sereno / CAG / governança). **ETAPA 1** (2026-04-16) alargou testes unitários (edge em `tests/test_catalogo.py`) e a fatia E2E de domínio `run_catalogo_especialidades_domain_slice` em `_run_boundary_tests` (`tests/e2e_stress_test.py`); **ETAPA 2** mantém-se como registo formal pós-suite em CI / selo QA.

### A) Dados e migração SQLite

| Risco / side-effect | Impacto | Cobertura actual | Acção ETAPA 1 (testes) |
|:---|:---|:---|:---|
| `servicos.especialidade_id` NULL em bases legadas antes da migração | Listagens JOIN podem expor especialidade vazia; INSERT manual sem coluna falha se NOT NULL no futuro | `test_migrate_repreenche_especialidade_id_nulo` | — |
| `INSERT OR IGNORE` em especialidades «Geral» duplicado | Baixo — idempotência | `test_create_tables_idempotente_nao_duplica_geral_por_natureza` | — |
| Wipe `seed_validacao_massiva` inclui `especialidades` | Ordem de DELETE vs FK (hoje sem FK física em `especialidade_id`) | Não testado isoladamente | Smoke: script ou teste de integração mínimo que simula wipe + `create_tables` + seed parcial |

### B) Domínio catálogo e regras de negócio

| Risco | Impacto | Cobertura actual | Acção ETAPA 1 |
|:---|:---|:---|:---|
| Especialidade inativa (`ativo=0`) associada a serviço | `_resolver` rejeita inativas em novos cadastros; serviços antigos podem manter referência | `test_cadastrar_servico_rejeita_especialidade_inativa` | Opcional: desactivar especialidade com serviços dependentes (política documentada) |
| `especialidade_id` de natureza errada | Rejeitado no resolver | `test_cadastrar_servico_rejeita_especialidade_natureza_errada`; fatia E2E `run_catalogo_especialidades_domain_slice` | — |
| Nome duplicado `(natureza, nome)` | IntegrityError tratado | `test_cadastrar_especialidade_nome_duplicado_rejeita`; fatia E2E | — |
| Pacote/Evento sem linha «Geral» | Resolver faz INSERT OR IGNORE | Implícito nos fluxos existentes | Teste unitário explícito: base vazia só com tabelas — primeiro `cadastrar_pacote` cria cadeia |

### C) UI Streamlit (Catálogo e fluxos dependentes)

| Risco | Impacto | Cobertura actual | Acção ETAPA 1 |
|:---|:---|:---|:---|
| `st.selectbox` especialidade + mudança de natureza (chave `fk_esp_{natureza}`) | Estado residual entre naturezas | Contrato estático `assert_cat_especialidade_form_contract` | Edge: ficheiro-fonte ou teste de widgets keys únicas por natureza; documentar limite (sem browser real) |
| CAG/Vendas filtram só por `natureza` em `listar_servicos_para_venda` | `especialidade` no dict não usada na UI — confusão futura | `test_listar_servicos_para_venda_inclui_campos_especialidade`; fatia E2E | — |
| Tabela catálogo nova coluna «Especialidade» | Export/relatórios se copiarem colunas | Visual Sereno tests | Assert coluna no `page_catalogo` DataFrame keys (já parcial via listagem) |

### D) Integrações transversais (Colaboradores, Agendamentos, Vendas, Relatórios, ETL)

| Risco | Impacto | Cobertura actual | Acção ETAPA 1 |
|:---|:---|:---|:---|
| `colaborador_servicos` continua por `servico_id` | Nenhum FK para especialidade — mudança de especialidade do serviço não rebalanceia habilitações | Sem alteração | Teste documental + opcional: ao mudar especialidade de serviço, habilitações permanecem válidas |
| `home_cockpit_metrics` / dashboards se agregarem por natureza | Podem ignorar especialidade | Não analisado em profundidade | Varredura grep + teste de fumo se existir SQL em `servicos` sem JOIN `especialidades` |
| `test_etl_analytics.py` usa `:memory:` DDL mínimo sem `especialidades` | ETL não referencia especialidade — OK | Isolado | Manter; se ETL passar a ler `especialidades`, alinhar DDL de teste |

### E) E2E — **não existe Playwright nem Cypress** no repositório

| Constatação | Norma actual | Ajuste proposto (ETAPA 1 / governança) |
|:---|:---|:---|
| E2E = `tests/e2e_stress_test.py` (pytest + jornada herói + contratos UI por leitura de ficheiros) + relatório `tests/last_stress_report.txt` | E20 em `.cursorrules` / `status_demanda.json` | **Opção A (activa):** fatia `tests/catalogo_especialidades_e2e_slice.py` chamada em `_run_boundary_tests`. **Opção B (futura):** Playwright em `e2e/browser/` — aprovação explícita. |
| Pedido explícito «Playwright/Cypress» | Incompatível com árvore actual | CADERNO + (recomendação) parágrafo futuro em `.cursorrules` após OK do Diretor |

### F) Ficheiros normativos a alinhar após OK

| Ficheiro | Necessidade |
|:---|:---|
| `docs/CADERNO_TESTES_MASTER.md` | §2 totais, mapa de ficheiros, secção demanda Especialidades, histórico — **actualizado nesta ETAPA 0** em parte; ETAPA 1 completa com IDs de testes novos. |
| `.cursorrules` | Acrescentar nota E20/E2E: «E2E pytest `e2e_stress_test.py` + contratos estáticos; browser automation apenas se adoptada» — **pendente aprovação**. |
| `docs/governanca/status_demanda.json` | Reflecte **224** testes e `live_status` 2026-04-16 (ETAPA 1); após ETAPA 2 manter sincronizado com CI. |
| `docs/MODELO_ARQUITETURA.md` | Já inclui `especialidades`; manter sincronizado se schema evoluir. |

---

## 2. Mapa completo da suite (regressão global — não só último épico)

**Total actual (auditoria 2026-04-16, pós-ETAPA 1 Especialidades):** **224** testes — `python -m pytest tests/ -v`.

| Ficheiro | Âmbito de negócio / técnico |
|:---|:---|
| `tests/conftest.py` | SQLite isolado por teste (`BEABA_SQLITE_PATH`); protege `data/beaba_gestao.db` local |
| `tests/e2e_stress_test.py` | E2E herói + boundary (jornada transversal: cliente, venda, agendamento, integridade); contratos visuais FIN incl. **2. Repasses**; fatia domínio **Especialidades** (`run_catalogo_especialidades_domain_slice`) |
| `tests/catalogo_especialidades_e2e_slice.py` | Fatia E2E pytest (sem browser): «Geral», duplicado especialidade, natureza errada, chaves `listar_servicos_para_venda` |
| `tests/fin_ui_contract.py` | Contrato UI Financeiro: slot Sereno + sector **2. Repasses** (`assert_fin_repasses_sector_na_pagina`) |
| `tests/test_fin_visual_sereno.py` | Financeiro: inject CSS Ilha Mãe + strings sector repasses |
| `tests/test_financeiro_categorias_gasto.py` | Centro/natureza/tipo gasto operacional |
| `tests/test_financeiro_lancamentos_gasto.py` | Lançamentos, parsing, listagem controle |
| `tests/test_financeiro_repasses_colaboradores.py` | Consulta repasse colaboradores (CONCLUIDO / REALIZADO_PENDENTE_PGTO), filtros |
| `tests/test_agendamento.py` | Agendamentos, buffer, máquina de estados, E11 pré-venda, `listar_agendamentos_elegiveis_associacao_linha_venda`, `pos_venda_associar_agendamentos_por_linha`, conversão avulsa→consumo pacote (`converter_agendamento_avulso_para_consumo_pacote`, repasse) |
| `tests/test_app_governance_syntax.py` | Compilação smoke `app_governance` |
| `tests/test_catalogo.py` | Catálogo: sessão, pacote, evento, validações; **Especialidades** (edge: inativa, natureza errada, dup nome, migração NULL, idempotência `create_tables`, `listar_servicos_para_venda`, `atualizar_servico_fase1_existente`) |
| `tests/cat_ui_contract.py` | Contrato UI Catálogo: Ilha Sereno + **form Especialidade** (`assert_cat_especialidade_form_contract`) |
| `tests/test_cat_visual_sereno.py` | Catálogo Sereno + **teste contrato especialidade** |
| `tests/test_cliente.py` | Módulo `cliente`: busca, cadastro, NIF/datas |
| `tests/cag_setor4_ui_contract.py` | Contratos CAG Setor 4: lista no expander «Agendamentos»; conversão avulsa→pacote (hoje) |
| `tests/test_clientes_agendamentos_page.py` | UI consolidada CAG: import, estado, resumo setor 2, HTML naturezas, contratos Setor 4 |
| `tests/test_colaborador.py` | Colaboradores, serviços, repasse, idade |
| `tests/test_e17_backup_dr.py` | E17 backup horário, verify, rotação, corrupção |
| `tests/test_e17_1_cloud.py` | E17.1 crypto GCM, evidências SQLite, append telemetria |
| `tests/test_e18_credito.py` | Ledger crédito, gate pagamento, meios legado |
| `tests/test_etl_analytics.py` | ETL / DW, regras LTV e carga horária |
| `tests/test_governanca.py` | JSON painel, fluxo doc, caderno, monitor, telemetry schema |
| `tests/test_monitor_demanda.py` | Script monitor demanda (exit zero) |
| `tests/test_nif_e164.py` | E16 NIF PT, doc. internacional, E.164 |
| `tests/test_qa_auto.py` | Cliente: CP, duplicidade, emergência, filhos, grávida |
| `tests/test_relatorios.py` | Relatórios, KPIs, filtros, colaborador em linha |
| `tests/test_restore_sqlite.py` | E17.2 `restore_sqlite.py`: trava de branch + restore BEA1 com flag de teste |
| `tests/test_sqlite_backup_verify.py` | Header SQLite + verify destino mínimo |
| `tests/test_venda.py` | Vendas: totais, split, pendente, contexto agendamento, `listar_venda_item_ids_em_ordem` |
| `tests/test_view_governance.py` | `view_governance` CLI smoke |

## 3. Plano por demanda (template)

Para cada **ID de demanda**, acrescentar secção:

```markdown
### Demanda <ID> — <título>

- **Objectivo:** …
- **Novos casos:** …
- **Regressão:** pytest completo + smoke Streamlit: …
- **Critérios de aceite:** …
```

### Demanda `2026-04-06_E11_pre_venda_agenda` — pré-venda na agenda

- **Objectivo:** `modo_origem` / `pre_venda`, `associar_agendamento_pre_venda_a_item`, `registrar_venda` + `agendamento_contexto_id`, UI Agendamentos + Vendas.
- **Novos casos:** `test_schema_agendamentos_tem_modo_origem`, `test_pre_venda_sessao_concluir_bloqueado`, `test_pre_venda_associar_apos_venda`, `test_pre_venda_pacote_natureza_rejeita`, `test_cancelar_pre_venda`, `test_registrar_venda_contexto_agendamento_cliente_diferente_falha`, `test_listar_agendamentos_elegiveis_associacao_inclui_pre_venda`, `test_pos_venda_associar_integra_pre_venda_e_conclui`, `test_pos_venda_associacao_parcial_venda_vai_para_rpp`, `test_listar_venda_item_ids_em_ordem`, contrato `assert_vnd_associacao_agendamento_por_linha`.
- **Regressão:** `python -m pytest tests/ -v` (suite **49** testes após E11).
- **Critérios de aceite:** alinhados ao [`04_desenho_logico.md`](governanca/demandas/2026-04-06_E11_pre_venda_agenda/04_desenho_logico.md) §8.

### Demanda épico **Especialidades** (2026-04-16) — Natureza → Especialidade → Serviço

- **Objectivo:** tabela `especialidades`, `servicos.especialidade_id`, migração «Geral», APIs `listar_especialidades_por_natureza` / `cadastrar_especialidade` / resolver interno; UI `page_catalogo.py` (select + expander); `listar_itens_catalogo` / `listar_servicos_para_venda` com JOIN; seed wipe inclui `especialidades`.
- **Casos cobertos (224):** os anteriores + `test_cadastrar_servico_rejeita_especialidade_natureza_errada`, `test_cadastrar_servico_rejeita_especialidade_inativa`, `test_cadastrar_especialidade_nome_duplicado_rejeita`, `test_listar_servicos_para_venda_inclui_campos_especialidade`, `test_create_tables_idempotente_nao_duplica_geral_por_natureza`, `test_migrate_repreenche_especialidade_id_nulo`, `test_atualizar_servico_altera_especialidade`; fatia E2E domínio via `_run_boundary_tests` + `test_e2e_cat_visual_shell_contract`.
- **Edge cases remanescentes (opcional):** Pacote/Evento em BD só com tabelas mínimas (primeiro `cadastrar_pacote` sem migração prévia); política ao desactivar especialidade com serviços dependentes.
- **E2E — ETAPA 1:** `run_catalogo_especialidades_domain_slice` integrado em `e2e_stress_test` (boundary + `run_stress_pipeline` em `__main__`).
- **Regressão:** `python -m pytest tests/ -v` (**224** testes).
- **Critérios de aceite:** coerência `natureza` serviço ↔ especialidade; UI sem regressão Sereno; nenhum teste removido salvo obsolescência demonstrada.

### Demanda `2026-04-14_CAG_conversao_sessao_avulsa_pacote_hoje` — conversão para consumo de pacote (data de hoje)

- **Objectivo:** `converter_agendamento_avulso_para_consumo_pacote`, `listar_buckets_pacote_com_saldo_disponivel`, `agendamento_elegivel_conversao_para_pacote_hoje`; UI `_cag_render_conversao_pacote_hoje_block` após «Salvar Agendamento» no form Setor 4; regras de repasse (`PENDENTE_REPASSE` removido; bloqueio se existir linha ≠ pendente).
- **Novos casos:** `tests/test_agendamento.py` (elegibilidade, filtro de buckets, conversão OK, serviço ≠ componente, repasse `REPASSE_PAGO`, remoção de `PENDENTE_REPASSE`); `tests/cag_setor4_ui_contract.py` (`assert_cag_conversao_pacote_hoje_no_form_dados_agendamento`); `tests/test_clientes_agendamentos_page.py`; fatia CAG em `tests/e2e_stress_test.py`.
- **Regressão:** `python -m pytest tests/ -v` (**200** testes em 2026-04-14).
- **Schema / backup:** sem novas tabelas ou migrações nesta entrega (tabelas `agendamentos`, `repasse_linhas`, `agendamento_historico` já existentes).

### Demanda `2026-04-07_E12_refatoracao_painel_operacional` — Painel Torre + Diário + app

- **Objectivo:** `PAINEL_OPERACIONAL.md` executivo; `status_demanda.json` com `fases_resumo`, `diario_bordo_resumo`, `pc_foco`, etc.; UI de governança (hoje **Monitor de Voo**).
- **Novos casos:** `test_governanca` valida forma de `fases_resumo` / `diario_bordo_resumo` quando presentes.
- **Regressão:** `python -m pytest tests/ -v` (**50** testes); smoke **Monitor de Voo** (Torre, Diário, expanders).
- **Critérios de aceite:** [`02_desenho_funcional.md`](governanca/demandas/2026-04-07_E12_refatoracao_painel_operacional/02_desenho_funcional.md) e [`99_encerramento.md`](governanca/demandas/2026-04-07_E12_refatoracao_painel_operacional/99_encerramento.md).

### Demanda `2026-04-07_E13_ajustes_copy_formularios` — copy formulários

- **Objectivo:** apenas alteração de strings na UI (`app.py`) + coerência em `catalogo.py`.
- **Regressão:** `python -m pytest tests/ -v` (**50**).
- **Critérios de aceite:** [`02_desenho_funcional.md`](governanca/demandas/2026-04-07_E13_ajustes_copy_formularios/02_desenho_funcional.md).

### Demanda `2026-04-07_E14_telemetria_live` — STATUS LIVE

- **Objectivo:** telemetria no JSON; UI com bloco ao vivo + `streamlit-autorefresh`.
- **Novos casos:** `test_governanca` valida `live_status`, `etapas_pendentes`, `live_actualizado_iso`.
- **Regressão:** `python -m pytest tests/ -v` (**50**); smoke **Monitor de Voo** (autorefresh contínuo, fila).
- **Critérios de aceite:** [`02_desenho_funcional.md`](governanca/demandas/2026-04-07_E14_telemetria_live/02_desenho_funcional.md).

### Demanda `2026-04-07_E15_monitor_governanca_externo` — Monitor stand-alone

- **Objectivo:** `monitor_governanca.py` na raiz; remoção da página Fluxo em `src/app.py`; PAINEL com dois pontos de acesso.
- **Novos casos:** `test_monitor_governanca_script_existe_e_compila`.
- **Regressão:** `python -m pytest tests/ -v` (**50**); smoke **Monitor de Voo** (`streamlit run monitor_governanca.py`).
- **Critérios de aceite:** [`02_desenho_funcional.md`](governanca/demandas/2026-04-07_E15_monitor_governanca_externo/02_desenho_funcional.md) e [`99_encerramento.md`](governanca/demandas/2026-04-07_E15_monitor_governanca_externo/99_encerramento.md).

### Demanda `2026-04-08_E16_cliente_nif_telefone_internacional` — NIF, doc. internacional, E.164

- **Objectivo:** `nif.py`, `telefone.py`, `country_dial_codes.py`, `telefone_widgets.py`; colunas `nif_ou_documento`, `identificacao_internacional`, `cliente_filhos.data_nascimento`; migração `cliente_contatos_emergencia` (remove CHECK 11 dígitos); UI Clientes + Vendas.
- **Novos casos:** `tests/test_nif_e164.py`; regressão em `test_qa_auto`, `test_venda`, `test_agendamento`, `test_relatorios` (parâmetros `nif` / `documento_identificacao_internacional`).
- **Regressão:** `python -m pytest tests/ -v` (**56** testes).
- **Critérios de aceite:** [`04_desenho_logico.md`](governanca/demandas/2026-04-08_E16_cliente_nif_telefone_internacional/04_desenho_logico.md).

## 4. Histórico

- **2026-04-16:** Épico Especialidades (schema + domínio + UI Catálogo); suite **217** testes; CADERNO §1.1 ETAPA 0 (side-effects + plano ETAPA 1/2); E2E actual = pytest `e2e_stress_test` (sem Playwright/Cypress no repo).
- **2026-04-16 (ETAPA 1):** +7 testes em `test_catalogo.py`; `catalogo_especialidades_e2e_slice.py` + chamada em `e2e_stress_test._run_boundary_tests`; suite **224** testes.
- **2026-04-14:** Conversão CAG avulsa→consumo de pacote (hoje) + contrato UI + E2E; suite **200** testes (`test_agendamento`, `cag_setor4_ui_contract`, `e2e_stress_test`).
- **2026-04-06:** Documento criado para cumprir passo 18 do percurso normal — SUCESSO (plano de testes mestre).
- **2026-04-06:** Plano E11 (pré-venda) acrescentado; suite pytest **49** testes.
- **2026-04-07:** Plano E12 (Painel + governança UI); suite mantém **49** testes.
- **2026-04-07:** E13 (copy UI) — regressão **49** testes; sem novos casos automatizados.
- **2026-04-07:** E14 (telemetria) — `test_governanca` alargado; suite **49** testes (pré-E15).
- **2026-04-07:** E15 (monitor externo) — `test_monitor_governanca_script_existe_e_compila`; suite **50** testes.
- **2026-04-08:** E16 (NIF + telefone E.164 + nasc. filho) — `test_nif_e164.py`; suite **56** testes.
- **2026-04-08:** E17 (backup/DR SQLite) — `test_e17_backup_dr.py`; suite **62** testes.
- **2026-04-09:** E17.1 — `test_backup_dr_history_json_existe_e_schema_vazio`; suite **63** testes.
- **2026-04-09:** E17.1 Fase C — `test_e17_1_cloud.py`; suite **66** testes.
- **2026-04-12:** Auditoria 360º — mapa completo §2 (21 ficheiros + `conftest`); suite **89** testes (`test_cliente.py`, `test_clientes_agendamentos_page.py`, `test_e18_credito.py`, `test_etl_analytics.py`, `test_restore_sqlite.py`, `test_sqlite_backup_verify.py`, `test_app_governance_syntax.py`, `test_monitor_demanda.py`, `test_view_governance.py`, `e2e_stress_test` na suite pytest).

### Demanda `2026-04-09_E17_1_autonomia_resiliencia_cloud` — telemetria backup/DR (Monitor)

- **Objectivo:** `backup_dr_history.json` + workflows GHA + AES-GCM + aba Monitor (matriz).
- **Novos casos:** `test_backup_dr_history_json_existe_e_schema_vazio`; `test_e17_1_cloud.py` (GCM, evidências SQLite, append telemetria).
- **Regressão:** `python -m pytest tests/ -v` (**89** testes em 2026-04-12).
- **Critérios de aceite:** [`04_desenho_logico.md`](governanca/demandas/2026-04-09_E17_1_autonomia_resiliencia_cloud/04_desenho_logico.md) §6 e workflows.

### Demanda `2026-04-08_E17_backup_dr` — backup e DR SQLite

- **Objectivo:** `scripts/backup_sqlite_hourly.py`, `scripts/verify_restore_weekly.py`; WAL em `connection.py`; pasta `backups/`; política nuvem documentada no PAINEL.
- **Novos casos:** compilação dos scripts; backup sem fonte (exit 1); backup + verify OK; verify sem backups (exit 1); rotação com `BEABA_BACKUP_KEEP=2`; corrupção binária na cópia horária → verify falha.
- **Regressão:** `python -m pytest tests/ -v` (suite actual **89** testes; E17 em `test_e17_backup_dr.py` + `test_sqlite_backup_verify.py` + `test_restore_sqlite.py`).
- **Critérios de aceite:** [`04_desenho_logico.md`](governanca/demandas/2026-04-08_E17_backup_dr/04_desenho_logico.md) e [`99_encerramento.md`](governanca/demandas/2026-04-08_E17_backup_dr/99_encerramento.md).

### Pós-E18 / E19 / UI (mapa transversal)

- **E18 crédito e gate:** `tests/test_e18_credito.py`.
- **E19 DW / ETL:** `tests/test_etl_analytics.py` + regressão em `test_relatorios.py` / dashboards.
- **Página Clientes+Agendamentos (CAG):** `tests/test_clientes_agendamentos_page.py`.
- **Módulo cliente (API):** `tests/test_cliente.py` (além de `test_qa_auto` / E16).
- **Stress E2E (portão E20):** além da suite, correr `python tests/e2e_stress_test.py` com iterações ≥1000 antes de PC13 de épico; relatório opcional `tests/last_stress_report.txt`.
