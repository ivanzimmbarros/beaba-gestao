# Painel operacional — BeaBa Gestão

**Última actualização:** 2026-04-08 — **E17** concluída (backup/DR SQLite); **E16** (NIF + E.164 + filhos); **E15** Monitor de Voo; **E14** telemetria; **E12** Torre + Diário.  
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

## Backup e recuperação (E17 — SQLite)

| Artefacto | Uso |
|:---|:---|
| **`scripts/backup_sqlite_hourly.py`** | Cópia online (`Backup` API) de `data/beaba_gestao.db` → `backups/hourly/beaba_gestao_UTC_*.db`, `PRAGMA quick_check`, rotação (defeito **168** ficheiros). |
| **`scripts/backup_hourly.cmd`** | Entrada para **Task Scheduler** (Windows), cada **1 hora** — ajustar caminho do `python` / venv. |
| **`scripts/verify_restore_weekly.py`** | Semanal: última cópia horária → staging em `backups/restore_verify/`, `integrity_check` + `foreign_key_check`, **sem** alterar produção. |
| **`scripts/verify_restore_weekly.cmd`** | Task Scheduler (ex.: domingo 03:00). |

**Ambiente (opcional):** `BEABA_REPO_ROOT` (raiz do clone); `BEABA_BACKUP_KEEP`; `BEABA_BACKUP_CLOUD_QUEUE=0` para desligar cópia espelho em `backups/cloud_queue/`.

**Nuvem:** **não** sincronizar `data/beaba_gestao.db` em uso (OneDrive/Dropbox/etc.). Sincronizar apenas **cópias fechadas** — recomendado: apontar o cliente de nuvem só a `backups/cloud_queue/` **ou** usar rclone/S3/Azure com encriptação. Detalhe: [`99_encerramento.md`](governanca/demandas/2026-04-08_E17_backup_dr/99_encerramento.md) (restauro manual).

**App:** conexão SQLite com **`PRAGMA journal_mode=WAL`** (`src/database/connection.py`).

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
| **F** | Encerramento | **PC13a** → **PC13b** | `99_encerramento.md` + Painel final |

**Legenda visual (também na app):** 🟢 feito · 🔵 em curso · ⚪ pendente · 🟠 correção (percurso FALHA).

**PC em foco** e estado por fase: espelhados em [`status_demanda.json`](governanca/status_demanda.json) (`pc_foco`, `fases_resumo`) e no **Monitor de Voo** (`monitor_governanca.py`).

**Ao vivo (E14 + E15):** durante o trabalho da EQUIPE, o mesmo JSON inclui **`live_status`**, **`etapas_pendentes`** e **`live_actualizado_iso`**; o **Monitor de Voo** mostra o bloco **STATUS LIVE** no topo com **`streamlit-autorefresh`** (10 s, sempre activo). O Painel `.md` permanece o registo **histórico** nos PCs.

---

## Estado actual — visão imediata

| Indicador | Situação |
|:---|:---|
| **Demanda activa** | ⚪ *Nenhuma* — última: **E17** entregue ([`99_encerramento.md`](governanca/demandas/2026-04-08_E17_backup_dr/99_encerramento.md)); antes **E16** ([`99`](governanca/demandas/2026-04-08_E16_cliente_nif_telefone_internacional/99_encerramento.md)). Próximo: **`@Files` → Analista**. |
| **Última entrega de produto** | ✅ **E11** — Pré-venda na agenda (marco de negócio de referência no Diário); evoluções posteriores: E12–E17 (processo, monitor, backup/DR). |
| **Última entrega de processo** | ✅ **E17** — Backup/DR SQLite ([`99`](governanca/demandas/2026-04-08_E17_backup_dr/99_encerramento.md)). Antes: **E16** NIF / E.164; **E15** Monitor; **E14** telemetria; **E12** Torre. |
| **Testes** | ✅ **62** `pytest` · CI: **FLUXO OFICIAL DE GOVERNANCA** + **Validador Maestro V2** em `develop`. |

---

## Diário de Bordo — marcos E01 a E17

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

---

## Apêndice H — Histórico de entregas (detalhe)

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

**Estado:** etapas 01–15 concluídas.

| # | Etapa | Estado | Nota |
|:---:|:---|:---:|:---|
| 01–03 | Config, Clientes, Colaboradores | ✅ | Filtros e equipa |
| 04 | Escopo | ✅ | Alinhado Diretor |
| 05 | Dados | ✅ | `agendamentos`, `agendamento_colaboradores` — [`MODELO`](MODELO_ARQUITETURA.md) |
| 06 | UI | ✅ | [`page_agendamentos.py`](../src/ui/page_agendamentos.py) |
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

✅ [`page_vendas.py`](../src/ui/page_vendas.py), [`venda.py`](../src/modules/venda.py). Testes: **33** no fecho E07.

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
