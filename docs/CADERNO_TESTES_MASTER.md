# Caderno mestre de testes — BeaBa Gestão

**Normativo:** a **EQUIPE** (persona Dev no passo **18** do **Fluxo oficial de governança** em [`governanca/FLUXO_SUCESSO_E_FALHA.md`](governanca/FLUXO_SUCESSO_E_FALHA.md)) **actualiza** este documento com o **plano de testes** de cada demanda. O **QA** (EQUIPE) valida, incrementa se necessário, e executa testes massivos. O Diretor **não** edita este ficheiro manualmente.

## 1. Testes automatizados (regressão obrigatória)

| Âmbito | Comando | Notas |
|:---|:---|:---|
| Suite completa | `python -m pytest tests/ -v` | Deve passar antes de **selo QA** e push em `develop`. |

## 2. Por módulo (referência rápida)

- `tests/test_qa_auto.py` — clientes, validações
- `tests/test_colaborador.py` — colaboradores
- `tests/test_catalogo.py` — catálogo, pacotes, eventos
- `tests/test_venda.py` — vendas (incl. `agendamento_contexto_id` / cliente ≠ agendamento)
- `tests/test_relatorios.py` — relatórios / dashboards
- `tests/test_agendamento.py` — agendamentos (incl. E11 pré-venda, migração `modo_origem`, associação a `venda_item`)
- `tests/test_nif_e164.py` — E16 NIF (módulo 11) e normalização E.164 / legado
- `tests/test_e17_backup_dr.py` — E17 backup horário + verificação semanal (subprocess, repo isolado)

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
- **Novos casos:** `test_schema_agendamentos_tem_modo_origem`, `test_pre_venda_sessao_concluir_bloqueado`, `test_pre_venda_associar_apos_venda`, `test_pre_venda_pacote_natureza_rejeita`, `test_cancelar_pre_venda`, `test_registrar_venda_contexto_agendamento_cliente_diferente_falha`.
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

### Demanda `2026-04-08_E17_backup_dr` — backup e DR SQLite

- **Objectivo:** `scripts/backup_sqlite_hourly.py`, `scripts/verify_restore_weekly.py`; WAL em `connection.py`; pasta `backups/`; política nuvem documentada no PAINEL.
- **Novos casos:** compilação dos scripts; backup sem fonte (exit 1); backup + verify OK; verify sem backups (exit 1); rotação com `BEABA_BACKUP_KEEP=2`; corrupção binária na cópia horária → verify falha.
- **Regressão:** `python -m pytest tests/ -v` (**62** testes).
- **Critérios de aceite:** [`04_desenho_logico.md`](governanca/demandas/2026-04-08_E17_backup_dr/04_desenho_logico.md) e [`99_encerramento.md`](governanca/demandas/2026-04-08_E17_backup_dr/99_encerramento.md).
