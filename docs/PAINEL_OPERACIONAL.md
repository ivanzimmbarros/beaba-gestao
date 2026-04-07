# Painel operacional — BeaBa Gestão

**Última actualização:** 2026-04-07 — **Torre de Controle** + **Diário de Bordo** (demanda **E12**).  
**Norma:** [`FLUXO_SUCESSO_E_FALHA.md`](governanca/FLUXO_SUCESSO_E_FALHA.md) (**Fluxo oficial de governança**).  
**Quem actualiza:** a **EQUIPE**; o Diretor **não** edita este ficheiro.

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

**PC em foco** e estado por fase: espelhados em [`status_demanda.json`](governanca/status_demanda.json) (`pc_foco`, `fases_resumo`) e no menu **Fluxo e governança** da aplicação.

---

## Estado actual — visão imediata

| Indicador | Situação |
|:---|:---|
| **Demanda activa** | ⚪ *Nenhuma* — próximo pedido: **`@Files` → Analista** no Cursor. |
| **Última entrega de produto** | ✅ **E11** — Pré-venda na agenda (ver Diário abaixo). |
| **Última entrega de processo** | ✅ **E12** — Refactoração deste Painel + Torre na app ([`99_encerramento.md`](governanca/demandas/2026-04-07_E12_refatoracao_painel_operacional/99_encerramento.md)). |
| **Testes** | ✅ **49** `pytest` · CI: **FLUXO OFICIAL DE GOVERNANCA** + **Validador Maestro V2** em `develop`. |

---

## Diário de Bordo — marcos E01 a E11

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
| 14 | Validação visual | Vendas, Dashboards, Agendamentos, **Fluxo e governança** | ✅ |
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
| E12 | Painel executivo + Torre na app |

---

## Apêndice H — Histórico de entregas (detalhe)

- **2026-04-07 — E12:** Painel tipo Torre + Diário; `status_demanda.json` alargado; `page_fluxo_gestao` sem pandas.
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
