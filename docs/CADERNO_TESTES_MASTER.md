# Caderno mestre de testes — BeaBa Gestão

**Normativo:** a **EQUIPE** (persona Dev no passo **18** do **Fluxo oficial de governança** em [`governanca/FLUXO_SUCESSO_E_FALHA.md`](governanca/FLUXO_SUCESSO_E_FALHA.md)) **actualiza** este documento com o **plano de testes** de cada demanda. O **QA** (EQUIPE) valida, incrementa se necessário, e executa testes massivos. O Diretor **não** edita este ficheiro manualmente.

## 1. Testes automatizados (regressão obrigatória)

| Âmbito | Comando | Notas |
|:---|:---|:---|
| Suite completa | `python -m pytest tests/ -v` | Deve passar antes de **selo QA** e push em `develop`. |

## 2. Mapa completo da suite (regressão global — não só último épico)

**Total actual (auditoria 2026-04-13):** **183** testes — `python -m pytest tests/ -v`.

| Ficheiro | Âmbito de negócio / técnico |
|:---|:---|
| `tests/conftest.py` | SQLite isolado por teste (`BEABA_SQLITE_PATH`); protege `data/beaba_gestao.db` local |
| `tests/e2e_stress_test.py` | E2E herói + boundary (jornada transversal: cliente, venda, agendamento, integridade); contratos visuais FIN incl. **2. Repasses** |
| `tests/fin_ui_contract.py` | Contrato UI Financeiro: slot Sereno + sector **2. Repasses** (`assert_fin_repasses_sector_na_pagina`) |
| `tests/test_fin_visual_sereno.py` | Financeiro: inject CSS Ilha Mãe + strings sector repasses |
| `tests/test_financeiro_categorias_gasto.py` | Centro/natureza/tipo gasto operacional |
| `tests/test_financeiro_lancamentos_gasto.py` | Lançamentos, parsing, listagem controle |
| `tests/test_financeiro_repasses_colaboradores.py` | Consulta repasse colaboradores (CONCLUIDO / REALIZADO_PENDENTE_PGTO), filtros |
| `tests/test_agendamento.py` | Agendamentos, buffer, máquina de estados, E11 pré-venda, `listar_agendamentos_elegiveis_associacao_linha_venda`, `pos_venda_associar_agendamentos_por_linha` |
| `tests/test_app_governance_syntax.py` | Compilação smoke `app_governance` |
| `tests/test_catalogo.py` | Catálogo: sessão, pacote, evento, validações |
| `tests/test_cliente.py` | Módulo `cliente`: busca, cadastro, NIF/datas |
| `tests/test_clientes_agendamentos_page.py` | UI consolidada CAG: import, estado, resumo setor 2, HTML naturezas |
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
