# Painel operacional — BeaBa Gestão

**Última actualização:** 2026-04-12 — **E17 trilho backup/restore (GHA + prova local):** correcção de infraestrutura — os workflows agendados correm na branch **por defeito (`main`)**; `restore_weekly` e `test_restore_weekly` passam a descarregar artefactos dessa branch (`artifact_source_branch` em dispatch, defeito `main`). [`backup_encrypt_callable.yml`](../.github/workflows/backup_encrypt_callable.yml): **gate** obrigatório (pipeline + header BEA1 + upload); `if-no-files-found: error` no upload. **Secret:** `BEABA_BACKUP_KEY` (AES-256-GCM, **não** GPG) em *Settings → Secrets → Actions*. **Certificado de restore:** [`tests/E17_RESTORE_CERTIFICATE.txt`](../tests/E17_RESTORE_CERTIFICATE.txt) (gerado por [`scripts/generate_e17_restore_certificate.py`](../scripts/generate_e17_restore_certificate.py)); CI: [`.github/workflows/e17_restore_certify.yml`](../.github/workflows/e17_restore_certify.yml). `status_demanda.json` → `e17_backup_dr_operacional.status` **CONCLUÍDO**; campo `falha` limpo. **`python -m pytest tests/ -v` → 90 passed.**  
**Registo anterior (2026-04-12) — Decomissionamento UI (E20/E21):** remoção de `page_clientes.py` / `page_agendamentos.py`; superfície única [`page_clientes_agendamentos.py`](../src/ui/page_clientes_agendamentos.py).  
**Registo anterior (2026-04-12 manhã) — Auditoria 360º:** sincronização `develop`→`origin/develop` (código, workflows backup, testes, governança); **`python -m pytest tests/ -v` → 89 passed**; `docs/CADERNO_TESTES_MASTER.md` com mapa completo da suite; certificação **backup/restore:** testes `test_e17_backup_dr`, `test_restore_sqlite`, `test_sqlite_backup_verify` + simulação `verify_restore_weekly` em `BEABA_REPO_ROOT` temporário (sem tocar em `data/beaba_gestao.db`); `status_demanda.json` → bloco `auditoria_360`. **Nota D1:** `*.db` permanece fora do Git por norma — nuvem de dados = `backups/` + GHA, não commit de bases vivas.  
**Registo anterior (2026-04-08):** **App:** correcção de avisos Streamlit em `src/app.py` (campos País e Repasse % em Colaboradores/Clientes: defaults via `session_state` sem `value=` em conflito com `_col_prime`). **Carga operacional** (2026-04-09) em `data/beaba_gestao.db` via [`scripts/seed_validacao_massiva.py`](../scripts/seed_validacao_massiva.py) (100 clientes, 20 colaboradores, 20 serviços, ~300 vendas, 300 agendamentos); `PRAGMA integrity_check` ok após carga. **`pytest`** usa [`tests/conftest.py`](../tests/conftest.py) (`BEABA_SQLITE_PATH` isolado) para **não** apagar a base local ao correr a suite. **Protocolo Fortaleza (E20 + E17.1)** integrado no [Fluxo oficial](governanca/FLUXO_SUCESSO_E_FALHA.md): **portão de stress E2E** (`tests/e2e_stress_test.py`, ≥1000 iterações, relatório `tests/last_stress_report.txt`) **obrigatório antes de PC13**; validação **backup D1–D4** e **bolinha zero + GHA verde** no fecho. **E19.1** **activa** (Cloud Total — **Fase B**): blindagem de backup/integridade e **restauro operacional** a partir de cópias espelhadas (`backups/hourly`, `cloud_queue`, GHA). **E19** DW concluído; **E18** concluído; **E17.2** concluída; **E17** backup/DR base; **E16**–**E12** estáveis. **Painel v2** mantido.  
**Norma:** [`FLUXO_SUCESSO_E_FALHA.md`](governanca/FLUXO_SUCESSO_E_FALHA.md) (**Fluxo oficial de governança**).  
**Quem actualiza:** a **EQUIPE**; o Diretor **não** edita este ficheiro.

---

## Dois pontos de acesso (gestão vs monitor)

| Ponto de acesso | Comando (na **raiz** do repositório) | Função |
|:---|:---|:---|
| **App de Gestão** | `streamlit run app.py` | Operação: clientes, colaboradores, catálogo, vendas, agendamentos, dashboards. |
| **Monitor de Voo** | `streamlit run monitor_governanca.py` | Telemetria E14 (**STATUS LIVE**), Torre A–F, Diário, pendente, JSON — **stand-alone** para segundo ecrã. |

Ambos leem o mesmo [`status_demanda.json`](governanca/status_demanda.json) no disco; o Painel `.md` permanece o registo **histórico** nos PCs.

---

## Painel de demandas (layout v2 — espelho canónico)

A **fonte estruturada** é [`status_demanda.json`](governanca/status_demanda.json) (`painel_layout_version` **2**). Abaixo replica-se o esqueleto para leitura humana e PCs; o **Monitor de Voo** e `python scripts/view_governance.py` mostram o mesmo conteúdo a partir do JSON.

### [SEÇÃO: ÉPICOS EM EXECUÇÃO]

Reservado a demandas com status **Em Aberto** ou **Pendente**.

| ID | Título | Status | Fase | PC foco |
|:---|:---|:---:|:---:|:---|
| **E19.1** (trilho [`E17.1`](governanca/demandas/2026-04-09_E17_1_autonomia_resiliencia_cloud/01_demanda_diretor.md)) | **Escudo Cloud Total** — auditoria de backup (integridade no destino), espelho `cloud_queue`, restauro operacional a partir de cópia verificada; alinhado à Fase B do desenho lógico Cloud | **Em curso** | B | PC3–PC4 |
| `2026-04-09_E17_1_autonomia_resiliencia_cloud` | **E17.1** — dossier técnico (GHA, AES-GCM, restore semanal, telemetria) | **Pendente** (selo Diretor) | B | PC3–PC4 |

**Próximo foco (prioridade):** **E19.1 / E17.1** — fechar **Fase B** com **CONFIRMO** / **PROSSIGA** sobre o [`04_desenho_logico.md`](governanca/demandas/2026-04-09_E17_1_autonomia_resiliencia_cloud/04_desenho_logico.md); depois **Fases C/D** (workflows, bucket/OIDC, Monitor). A **E19.1** garante que o que já está em produção (ledger, `dw_*`, vendas) não fica sem cópia verificada nem sem percurso de restauro local.

### [SEÇÃO: HISTÓRICO DE ÉPICOS CONCLUÍDOS]

Lista **cronológica inversa** (entrega mais recente primeiro). Cada linha liga ao dossier em `docs/governanca/demandas/` para **auditoria**.

| Data | ID | Título | Validação (resumo) | Documentos |
|:---|:---|:---|:---|:---|
| 2026-04-09 | *E19 (registo técnico)* | **E19** — Analytics de alta performance (DW `dw_*`, ETL, UI só leitura) | `pytest` + ETL + `dw_fact_*` / `dw_cliente_kpi`; LTV Real alinhado ao ledger E18 | `scripts/etl_analytics.py` · `src/ui/page_dashboards.py` (bloco E19) |
| 2026-04-08 | `2026-04-08_E18_operacional_financeiro` | **E18** — Reestruturação operacional-financeira | 69 testes passados; **integrity_check:** ok | [`01_demanda_diretor.md`](governanca/demandas/2026-04-08_E18_operacional_financeiro/01_demanda_diretor.md) · [`02_desenho_funcional.md`](governanca/demandas/2026-04-08_E18_operacional_financeiro/02_desenho_funcional.md) |
| 2026-04-08 | `2026-04-08_E17_2_retencao_restore_ativo` | **E17.2** — Retenção / restore / e-mails | Integração trilho E17.1/E18; telemetria [`backup_dr_history.json`](governanca/telemetry/backup_dr_history.json) | [`01_demanda_diretor.md`](governanca/demandas/2026-04-08_E17_backup_dr/01_demanda_diretor.md) · [`99_encerramento.md`](governanca/demandas/2026-04-08_E17_backup_dr/99_encerramento.md) |

**Entregas E18 (negócio):** máquina de estados dual (agendamento), ledger de créditos, gate de integridade financeira (CONCLUIDO vs REALIZADO_PENDENTE_PGTO), repasses, multi-meio em `venda_pagamento_linhas`.

**Encerramento E17.2:** requisitos operacionais do perímetro E17.2 foram **integrados e superados** pela arquitectura operacional-financeira do **E18** (ledger, gate de pagamento, estados de agendamento).

---

## Backup e recuperação (E17 — SQLite) + **E19.1** (integridade)

| Artefacto | Uso |
|:---|:---|
| **`scripts/backup_sqlite_hourly.py`** | Cópia **integral** (`Backup` API) de `data/beaba_gestao.db` → `backups/hourly/beaba_gestao_*.db` — inclui **todas** as tabelas (E18 ledger/repasse, E19 `dw_*`, etc.). **Sucesso** só após **`scripts/sqlite_backup_verify.py`** (header mágico SQLite + `PRAGMA quick_check`; opcional `integrity_check` com `BEABA_BACKUP_INTEGRITY_FULL=1`). Rotação defeito **168** ficheiros. |
| **`scripts/sqlite_backup_verify.py`** | Funções partilhadas: validação de header (16 bytes) + pragma; usada pelo backup horário e pela cópia em `cloud_queue`. |
| **`scripts/restore_operacional_de_copia.py`** | **Fase B (restauro local):** repõe `data/beaba_gestao.db` a partir da **última** cópia em `backups/hourly` ou `backups/cloud_queue` (ou ficheiro explícito), **após** as mesmas verificações. Requer `--confirmar` ou `BEABA_RESTORE_OPERACIONAL=1`. **Pare a app** antes (Windows). Complementa `restore_sqlite.py` (artefacto encriptado GHA). |
| **`scripts/backup_hourly.cmd`** | Entrada para **Task Scheduler** (Windows), cada **1 hora** — ajustar caminho do `python` / venv. |
| **`scripts/verify_restore_weekly.py`** | Semanal: última cópia horária → staging em `backups/restore_verify/`, `integrity_check` + `foreign_key_check`, **sem** alterar produção. |
| **`scripts/verify_restore_weekly.cmd`** | Task Scheduler (ex.: domingo 03:00). |

**Ambiente (opcional):** `BEABA_REPO_ROOT` (raiz do clone); `BEABA_BACKUP_KEEP`; `BEABA_BACKUP_CLOUD_QUEUE=0` para desligar cópia espelho em `backups/cloud_queue/`; `BEABA_BACKUP_INTEGRITY_FULL=1` para verificação completa pós-backup.

**`.gitignore`:** `*.db` mantém **fora do Git** tanto `data/beaba_gestao.db` (vivo) como réplicas em `backups/` — **intencional**; a «nuvem» não é `git push` de `.db`, mas **OneDrive/rclone/S3** sobre `backups/cloud_queue/` e/ou **artefactos GHA**.

**Nuvem:** **não** sincronizar `data/beaba_gestao.db` em uso (OneDrive/Dropbox/etc.). Sincronizar apenas **cópias fechadas** — recomendado: apontar o cliente de nuvem só a `backups/cloud_queue/` **ou** usar rclone/S3/Azure com encriptação. Detalhe: [`99_encerramento.md`](governanca/demandas/2026-04-08_E17_backup_dr/99_encerramento.md) (restauro manual).

**App:** conexão SQLite com **`PRAGMA journal_mode=WAL`** (`src/database/connection.py`).

### E17.1 — GitHub Actions (nuvem)

| Workflow | Gatilho | Função |
|:---|:---|:---|
| [`.github/workflows/backup_hourly.yml`](../.github/workflows/backup_hourly.yml) | `cron: 5 * * * *` UTC + `workflow_dispatch` | Checkout código em **`develop`** (telemetria); *run* do cron listado em **`main`**; `e17_1_gha_backup_job.py` + **`BEABA_BACKUP_KEY`**; artefacto **`beaba-sqlite-backup-encrypted`**; gate valida upload. |
| [`.github/workflows/restore_weekly.yml`](../.github/workflows/restore_weekly.yml) | `cron: 0 3 * * 0` UTC + `workflow_dispatch` | Download artefacto do **`backup_hourly` na branch `main`** (defeito); decrypt; `e17_1_gha_restore_job.py` + telemetria. |
| [`.github/workflows/e17_restore_certify.yml`](../.github/workflows/e17_restore_certify.yml) | `push` (paths E17) + `workflow_dispatch` | `pytest` restore/verify + regenera certificado + upload artefacto **`E17_RESTORE_CERTIFICATE`**. |

**Secret obrigatório:** `BEABA_BACKUP_KEY` — base64 de **32 bytes** (ou hex com 64 caracteres). **Não** é GPG/passphrase. **Monitor de Voo** → separador **Backup e Restore** lê `docs/governanca/telemetry/backup_dr_history.json`. **Prova local versionada:** [`tests/E17_RESTORE_CERTIFICATE.txt`](../tests/E17_RESTORE_CERTIFICATE.txt).

---

## Torre de Controle — onde estamos no fluxo

Visão **executiva** das **fases A–F** e dos **pares de pontos de controlo (PC)**. O detalhe normativo está no [Apêndice C](#apêndice-c--pontos-de-controlo-pc1pc13-e-ci).

```mermaid
flowchart LR
  A[A · Desenho] --> B[B · Lógico]
  B --> C[C · Código 1]
  C --> D[D · Código 2]
  D --> E[E · QA]
  E --> F[F · Fecho]
```

| Fase | Nome operacional | PCs (Git → Painel) | Olhar para… |
|:---:|:---|:---:|:---|
| **A** | Analista + Diretor | **PC1** → **PC2** | `01`–`03` + Painel / JSON |
| **B** | Arquiteto + Analista | **PC3** → **PC4** | Desenho lógico + selos |
| **C** | Dev + Arquiteto | **PC5** → **PC6** | Código + parecer Arquiteto |
| **D** | Analista + Dev | **PC7** → **PC8** | Código + plano de testes |
| **E** | QA | **PC9** → **PC10** → **PC11** → **PC12** | Plano, execução, selo QA |
| **E′** | Portão Fortaleza (E20) | **PC12.5** | **Após** PC12, **antes** de PC13: `pytest` → stress E2E (≥1000 iter) → `last_stress_report.txt`; checklist backup D1–D4; working tree limpa + push + GHA verde (ver [Fluxo oficial](governanca/FLUXO_SUCESSO_E_FALHA.md)) |
| **F** | Encerramento | **PC13a** → **PC13b** | `99_encerramento.md` + Painel final |

**Legenda visual (também na app):** 🟢 feito · 🔵 em curso · ⚪ pendente · 🟠 correção (percurso FALHA).

**PC em foco** e estado por fase: espelhados em [`status_demanda.json`](governanca/status_demanda.json) (`pc_foco`, `fases_resumo`) e no **Monitor de Voo** (`monitor_governanca.py`).

**Ao vivo (E14 + E15):** durante o trabalho da EQUIPE, o mesmo JSON inclui **`live_status`**, **`etapas_pendentes`** e **`live_actualizado_iso`**; o **Monitor de Voo** mostra o bloco **STATUS LIVE** no topo com **`streamlit-autorefresh`** (10 s, sempre activo). O Painel `.md` permanece o registo **histórico** nos PCs.

---

## Estado actual — visão imediata

| Indicador | Situação |
|:---|:---|
| **Demanda activa** | 🔵 **E19.1** — **Escudo** Cloud Total (Fase **B**): backup com verificação de integridade, espelho para nuvem, restauro operacional a partir de cópia; trilho técnico **E17.1** ([dossier](governanca/demandas/2026-04-09_E17_1_autonomia_resiliencia_cloud/01_demanda_diretor.md)). **Próximo passo:** selo **CONFIRMO** no `04_desenho_logico` + Fase C (GHA/OIDC). |
| **Última entrega de produto** | ✅ **E19** — Data Warehouse `dw_*`, ETL, UI Analytics (protecção operacional sob **E19.1**). |
| **Última entrega de processo** | ✅ **E19** (2026-04-09); **E19.1** em curso (backup/restore reforçados); **E18** (2026-04-08); **E17.2** concluída; **E17** base ([`99` E17](governanca/demandas/2026-04-08_E17_backup_dr/99_encerramento.md)). |
| **Testes** | ✅ Suite **`pytest tests/`** (CI: **FLUXO OFICIAL DE GOVERNANCA** + **Validador Maestro V2** em `develop`). **Portão E20:** stress E2E [`tests/e2e_stress_test.py`](../tests/e2e_stress_test.py) (mín. **1000** iterações no fecho de épico) + [`tests/last_stress_report.txt`](../tests/last_stress_report.txt) (gerado; pode estar no `.gitignore`). Registo histórico E18: **69** testes + **integrity_check** ok. |

---

## Diário de Bordo — marcos E01 a E19

Resumo **executivo** (detalhe técnico nos [anexos](#apêndice-h--e09-agendamentos-detalhe) e no [`CONTROLE_DE_VOO.md`](../CONTROLE_DE_VOO.md)). **Retrabalhos de processo:** ver [Apêndice A](#apêndice-a--registo-de-retrabalhos); abaixo indica-se apenas se houve evento registado.

| Marco | Data ref. | O que foi entregue (negócio) | Retrabalho |
|:---|:---|:---|:---:|
| **E01** | — | **V11.0** — identidade na app, navegação, Caderno Mestre. | — |
| **E02** | — | **Clientes** — contacto + ficha alargada. | — |
| **E03** | — | **Morada + filhos** — endereço pesquisável; filhos com nome. | — |
| **E04** | — | **Colaboradores** — habilitações, repasses, validações. | — |
| **E05** | — | **CI** — auditorias Arquiteto/Analista estáveis no GitHub. | — |
| **E06** | — | **Catálogo** — sessão, produto, coworking, **pacote**, **evento**. | — |
| **E07** | — | **Vendas** — registo, descontos, meios de pagamento, parcelas. | — |
| **E08** | — | **Relatórios** — KPIs, gráficos, exportação CSV. | — |
| **E09** | — | **Agendamentos** — calendário, estados, buffer, ligação à venda. | — |
| **E10** | — | *Reservado* — sem marco de produto dedicado nesta linha. | — |
| **E11** | 2026-04-06 | **Pré-venda × agenda** — marcação sem venda imediata; fecho na visita. | — |
| **E12** | 2026-04-07 | **Painel** — Torre de Controle + Diário de Bordo; UI de governança (posteriormente **E15** em monitor externo). | — |
| **E13** | 2026-04-07 | **Copy UI** — legendas e rótulos em Clientes, Colaboradores e Catálogo (`app.py`). | — |
| **E14** | 2026-04-07 | **Telemetria ao vivo** — `live_status` / `etapas_pendentes` / `live_actualizado_iso`; UI integrada na app (até **E15**). | — |
| **E15** | 2026-04-07 | **Monitor de Voo** — `monitor_governanca.py` na raiz; app principal sem entrada Fluxo; autorefresh obrigatório. | — |
| **E16** | 2026-04-08 | **Cliente** — NIF PT + doc. internacional; telefone E.164; `cliente_filhos.data_nascimento`; migração emergência. **Entregue** ([`99`](governanca/demandas/2026-04-08_E16_cliente_nif_telefone_internacional/99_encerramento.md)). | — |
| **E17** | 2026-04-08 | **Backup/DR** — hot-backup horário SQLite, verificação semanal `integrity_check`, `cloud_queue`, WAL; scripts + PAINEL. **Entregue** ([`99`](governanca/demandas/2026-04-08_E17_backup_dr/99_encerramento.md)). | — |
| **E17.1** | 2026-04-09 | **Cloud Total** — GHA, AES-GCM, restore semanal, telemetria; **em curso** Fase B ([`01`](governanca/demandas/2026-04-09_E17_1_autonomia_resiliencia_cloud/01_demanda_diretor.md)). | — |
| **E17.2** | 2026-04-08 | **Retenção multi-tier + restore activo + e-mails** — concluído; requisitos operacionais integrados / superados pelo **E18**. | — |
| **E18** | 2026-04-08 | **Operacional-financeiro** — ledger de créditos, linhas de pagamento multi-meio, gate CONCLUIDO, `repasse_linhas`, máquina de estados de agendamento. **Entregue** ([`01`](governanca/demandas/2026-04-08_E18_operacional_financeiro/01_demanda_diretor.md) · [`02`](governanca/demandas/2026-04-08_E18_operacional_financeiro/02_desenho_funcional.md)). | — |
| **E19** | 2026-04-09 | **Analytics DW** — `scripts/etl_analytics.py` (tabelas `dw_*`), carga horária decimal, recorrência/LTV Real no ETL (ledger E18); UI apenas `SELECT` sobre `dw_*` + botão ETL. | — |
| **E19.1** | 2026-04-09 | **Cloud Total (Fase B) + escudo** — integridade pós-backup (`sqlite_backup_verify`), restauro operacional (`restore_operacional_de_copia.py`); alinhado a E17.1 / nuvem. | — |
| **E20** | 2026-04-09 | **Fortaleza operacional** — stress E2E como **portão de saída** antes de PC13; [`tests/e2e_stress_test.py`](../tests/e2e_stress_test.py), [`tests/MAPA_FLUXOS.md`](../tests/MAPA_FLUXOS.md); norma em [Fluxo oficial](governanca/FLUXO_SUCESSO_E_FALHA.md) + `status_demanda.json`. | — |

---

## Como pedir uma evolução nova

1. No **Cursor**: **`@Files`** → **Analista** ou **EQUIPE**.  
2. Descreva o pedido; a EQUIPE abre a pasta em `docs/governanca/demandas/<ID>/`.  
3. Aprove o desenho funcional com **CONFIRMO** ou **PROSSIGA** no chat.  
4. Não precisa criar ficheiros no repositório manualmente.

📄 **Documento normativo completo:** [`docs/governanca/FLUXO_SUCESSO_E_FALHA.md`](governanca/FLUXO_SUCESSO_E_FALHA.md)

---

# Apêndices (referência técnica)

## Apêndice A — Registo de retrabalhos (reabertura de etapas)

| Data | Demanda | Etapa afectada | Origem | Resumo do problema | O que se fez | N.º |
|:---|:---|:---|:---|:---|:---|:---:|
| *—* | *—* | *—* | *—* | *Nenhum registo ainda.* | *—* | *—* |

**Origem possível:** Diretor, Analista, Arquiteto, Dev, QA, CI.

---

## Apêndice B — Nome do ficheiro `FLUXO_SUCESSO_E_FALHA.md`

O nome no disco é **histórico** (links estáveis). **SUCESSO** = percurso normal até à entrega; **FALHA** = percurso de correção. Opção A (só linguagem «Fluxo oficial» no Painel) está **em uso**.

---

## Apêndice C — Pontos de controlo PC1–PC13 e CI

Cada **push** credível em **`origin/develop`** fecha o lado **Git** do par; em seguida **Painel** + `status_demanda.json`.

| Ponto | Depois de… | Repositório | Painel / JSON |
|:---:|:---|:---|:---|
| **PC1** | Aprovação do desenho funcional no chat | `01`–`03` no dossier | **PC2** |
| **PC3** | Desenho lógico validado | Desenho + selo Analista | **PC4** |
| **PC5** | Código validado pelo Arquiteto | Parecer Arquiteto | **PC6** |
| **PC7** | Código + plano de testes (Analista) | Parecer + `CADERNO_TESTES_MASTER` | **PC8** |
| **PC9** | Plano de testes alterado (se houver) | Plano actualizado | **PC10** |
| **PC11** | Testes finais QA | Parecer QA | **PC12** |
| **PC12.5** | Portão Fortaleza (E20 + E17.1) | Evidência no parecer QA: pytest + `e2e_stress_test.py` (≥1000) + `last_stress_report.txt`; backup/telemetria D1–D4; sem bolinhas; push + CI verde | *(transição para Fase F)* |
| **PC13a** | Encerramento | `99_encerramento.md` | **PC13b** |

*Definição completa de PC GitHub (local + commit + push):* [`FLUXO_SUCESSO_E_FALHA.md`](governanca/FLUXO_SUCESSO_E_FALHA.md).

### CI no ramo `develop`

| Workflow | Ficheiro | Função |
|:---|:---|:---|
| **FLUXO OFICIAL DE GOVERNANCA** | [`.github/workflows/fluxo_oficial_governanca.yml`](../.github/workflows/fluxo_oficial_governanca.yml) | Artefactos normativos + `pytest tests/test_governanca.py` |
| **Validador Maestro V2** | [`.github/workflows/qa_automatico.yml`](../.github/workflows/qa_automatico.yml) | Suite completa `pytest tests/` |

Se uma regra de ramo exigir o nome antigo *Fabrica Zimmermann…*, actualize no GitHub para **FLUXO OFICIAL DE GOVERNANCA**.

---

## Apêndice D — Fluxo oficial (tabela expandida)

| Ordem | Fase | Significado | Precisa do Diretor? |
|:---:|:---|:---|:---:|
| 1 | Pedido | Registo via `@Files` | — |
| 2 | Desenho funcional | O quê, em negócio | ✅ **CONFIRMO** / **PROSSIGA** |
| 3 | Desenho técnico | Modelo e impactos | — |
| 4–6 | Construção e revisões | Dev / Arquiteto / Analista | — |
| 7 | Testes | QA | — |
| 8 | Encerramento | Informação ao Diretor | — |

**Correção:** regressão à primeira etapa afectada; registo em Apêndice A.

---

## Apêndice E — Aprovações («selos»)

| No Cursor | Significado |
|:---|:---|
| **CONFIRMO** / **PROSSIGA** | Selo do Diretor naquela fase — a EQUIPE regista em `03_confirmacao_diretor.md` (ou equivalente). |

---

## Apêndice F — Plano das 15 etapas técnicas (por marco)

| # | Etapa | Onde validar | Estado |
|:---:|:---|:---|:---:|
| 01 | Configuração | [`.cursorrules`](../.cursorrules) · [Fluxo oficial](governanca/FLUXO_SUCESSO_E_FALHA.md) · [`CADERNO_MESTRE.md`](CADERNO_MESTRE.md) · [`app.py`](../src/app.py) | ✅ |
| 02 | Clientes | [`cliente.py`](../src/modules/cliente.py) · [`test_qa_auto.py`](../tests/test_qa_auto.py) | ✅ |
| 03 | Colaboradores | [`colaborador.py`](../src/modules/colaborador.py) · [`test_colaborador.py`](../tests/test_colaborador.py) | ✅ |
| 04 | Proposta / escopo | [`CONTROLE_DE_VOO.md`](../CONTROLE_DE_VOO.md) | ✅ |
| 05 | Estrutura de dados | [`MODELO_ARQUITETURA.md`](MODELO_ARQUITETURA.md) | ✅ |
| 06 | Tema / UI | [`theme.py`](../src/ui/theme.py) · [`ui/`](../src/ui/) | ✅ |
| 07 | Base de dados | [`connection.py`](../src/database/connection.py) | ✅ |
| 08 | Regras de domínio | `modules/` | ✅ |
| 09 | Testes automáticos | [`tests/`](../tests/) | ✅ |
| 10 | CI | **FLUXO OFICIAL DE GOVERNANCA** + **Validador Maestro V2** | ✅ |
| 11 | pytest local | `pytest tests/` | ✅ |
| 12 | Documentação | `docs/` · `CONTROLE` · este painel | ✅ |
| 13 | Revisão de links | Esta tabela | ✅ |
| 14 | Validação visual | Vendas, Dashboards, Agendamentos, **Monitor de Voo** | ✅ |
| 15 | Push `develop` | Git | ✅ |

**Legenda:** ✅ Feito · 🚧 Em curso · ⚪ Pendente

---

## Apêndice G — Concordância marcos ↔ 15 etapas

| Marco | Cobertura (resumo) |
|:---|:---|
| E01 V11 | Configuração, tema, base, docs |
| E02/E03 | Clientes, morada, filhos |
| Governança | `FLUXO_SUCESSO_E_FALHA.md`, PC1–PC13, JSON, app |
| E04 | Colaboradores |
| E06 | Catálogo híbrido |
| E07 | Vendas |
| E08 | Relatórios / dashboards |
| E09 | Agendamentos |
| E11 | Pré-venda na agenda |
| E12 | Painel executivo + Torre (UI governança → E15 monitor) |
| E13 | Copy formulários (`app.py` + mensagem `catalogo.py`) |
| E14 | Telemetria ao vivo + `.cursorrules` microtarefas |
| E15 | `monitor_governanca.py` stand-alone; remoção Fluxo da app |
| E17.1 | Backup/DR na nuvem (GHA + cifra + telemetria + matriz Monitor) |
| E17.2 | Retenção 3/7/30d, restore activo, e-mails, dashboards Web/CLI — concluído; legado operacional alinhado ao E18 |
| E18 | Vendas/agendamentos: ledger `credito_movimentos`, `venda_pagamento_linhas`, gate financeiro, repasses, estados |
| E19 | ETL `dw_*` + dashboards só leitura; LTV Real e ocupação fora da UI (batch) |
| E19.1 | Backup integral verificado + restauro a partir de cópia espelhada; trilho Cloud E17.1 |

---

## Apêndice H — Histórico de entregas (detalhe)

- **2026-04-12 — Decomissionamento UI Clientes/Agendamentos:** removidos `page_clientes.py` e `page_agendamentos.py`; única superfície [`page_clientes_agendamentos.py`](../src/ui/page_clientes_agendamentos.py); hub, sidebar e governança alinhados; pytest 89/89 pós-corte.
- **2026-04-09 — E19.1 (em curso):** `sqlite_backup_verify.py`; reforço `backup_sqlite_hourly.py`; `restore_operacional_de_copia.py`; `.gitignore` documentado para `.db`.
- **2026-04-09 — E19:** `scripts/etl_analytics.py`; tabelas `dw_fact_agendamento`, `dw_fact_venda`, `dw_cliente_kpi`, `dw_etl_run`; secção Analytics em `page_dashboards.py`.
- **2026-04-08 — E18:** modelo híbrido operacional-financeiro; dossier [`2026-04-08_E18_operacional_financeiro`](governanca/demandas/2026-04-08_E18_operacional_financeiro/01_demanda_diretor.md); painel v2 no JSON + Monitor.
- **2026-04-08 — E17.2:** fecho operacional; integração narrativa com E18 (ver secção histórico no JSON / PAINEL).
- **2026-04-07 — E15:** `monitor_governanca.py` na raiz; `page_fluxo_gestao` removido; PAINEL com dois acessos; **50** testes.
- **2026-04-07 — E14:** STATUS LIVE, `streamlit-autorefresh`, campos `live_*` no JSON; regra EQUIPE em `.cursorrules`; **49** testes (pré-E15).
- **2026-04-07 — E13:** Copy Clientes, Colaboradores, Catálogo; rótulo duração pacote; Âmbito evento; **49** testes.
- **2026-04-07 — E12:** Painel tipo Torre + Diário; `status_demanda.json` alargado; UI Fluxo (evoluída em E15 para monitor externo).
- **2026-04-06 — CI:** **FLUXO OFICIAL DE GOVERNANCA** (substitui *Fabrica Zimmermann*).
- **2026-04-06 — E11:** Pré-venda na agenda; **49** testes.
- **`6671f3d`:** `@Files`, documentação automática, fluxo na app.
- **`f92c4f2`:** Norma governança completa.
- **`7dfc53d`:** E07–E09 no `develop`.

---

## Apêndice I — E09 Agendamentos (detalhe)

**Estado:** etapas 01–15 concluídas na linha E09; **E18** evoluiu estados, histórico, crédito e gate financeiro (ver [`02_desenho_funcional.md` E18](governanca/demandas/2026-04-08_E18_operacional_financeiro/02_desenho_funcional.md)).

| # | Etapa | Estado | Nota |
|:---:|:---|:---:|:---|
| 01–03 | Config, Clientes, Colaboradores | ✅ | Filtros e equipa |
| 04 | Escopo | ✅ | Alinhado Diretor |
| 05 | Dados | ✅ | `agendamentos`, `agendamento_colaboradores` — [`MODELO`](MODELO_ARQUITETURA.md) |
| 06 | UI | ✅ | [`page_clientes_agendamentos.py`](../src/ui/page_clientes_agendamentos.py) (consolidação 2026-04-12; legado `page_agendamentos` removido) |
| 07 | BD | ✅ | [`connection.py`](../src/database/connection.py) |
| 08 | Regras | ✅ | [`agendamento.py`](../src/modules/agendamento.py) |
| 09 | Testes | ✅ | [`test_agendamento.py`](../tests/test_agendamento.py) incl. E11 |
| 10–15 | CI, docs, QA, Git | ✅ | — |

**Escopo (resumo):** data + horas + colaboradores; calendário unificado; estados; pagamento; buffer; cancelamento com/sem devolução ao buffer.

---

## Apêndice J — E08 Dashboards

✅ [`page_dashboards.py`](../src/ui/page_dashboards.py), [`relatorios.py`](../src/modules/relatorios.py). Testes: **36** no fecho E08.

---

## Apêndice K — E07 Vendas

✅ [`page_vendas.py`](../src/ui/page_vendas.py), [`venda.py`](../src/modules/venda.py). Testes: **33** no fecho E07. **E18:** linhas `venda_pagamento_linhas`, abatimento de crédito, coerência com gate de agendamento CONCLUIDO.

---

## Apêndice L — E06 Catálogo

✅ [`catalogo.py`](../src/modules/catalogo.py), `app.py`. **28** testes no fecho E06.

---

## Apêndice M — Glossário

| Termo | Significado |
|:---|:---|
| **EQUIPE** | Agente Cursor: Analista, Arquiteto, Dev, QA. |
| **`develop`** | Ramo de entregas. |
| **PC** | Ponto de controlo Git → Painel. |
| **pytest** | Testes automáticos. |
| **CI** | **FLUXO OFICIAL DE GOVERNANCA** + **Validador Maestro V2** em `develop`. |
