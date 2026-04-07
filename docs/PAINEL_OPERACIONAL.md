# Painel operacional — BeaBa Gestão

**Para que serve:** este é o **quadro de bordo** do projecto — o sítio onde vê, em linguagem simples, **em que fase estamos**, **o que já foi entregue** e **o que falta** para uma evolução.  
**Quem actualiza:** a **EQUIPE** (agente no Cursor), após cada marco. O Diretor **não** precisa editar este ficheiro.

**Última actualização do painel:** 2026-04-06 — workflow **FLUXO OFICIAL DE GOVERNANCA** no GitHub Actions (substitui *Fabrica Zimmermann…*).

---

## 1. Estado actual — visão imediata

| Indicador | Situação |
|:---|:---|
| **Demanda activa** | ⚪ *Nenhuma* — à espera de novo pedido com **`@Files` → Analista** no Cursor. |
| **Última entrega concluída** | ✅ **Pré-venda na agenda (E11)** — reserva sem venda imediata, fecho nas Vendas, vendas ligadas à visita. |
| **Testes automáticos** | ✅ **49** testes a passar (`python -m pytest tests/ -v`). |
| **Resumo na aplicação** | Menu **Fluxo e governança** → lê o ficheiro [`status_demanda.json`](governanca/status_demanda.json). |

**Última demanda fechada (referência rápida)**

| | |
|:---|:---|
| **Nome** | Pré-venda × Agenda (`2026-04-06_E11_pre_venda_agenda`) |
| **Pasta com todos os documentos** | [`demandas/2026-04-06_E11_pre_venda_agenda/`](governanca/demandas/2026-04-06_E11_pre_venda_agenda/) |
| **Encerramento** | [`99_encerramento.md`](governanca/demandas/2026-04-06_E11_pre_venda_agenda/99_encerramento.md) |
| **Código principal** | commit `a6a9a8f` no ramo `develop` |

---

## 2. Como pedir uma evolução nova

1. No **Cursor**, use **`@Files`** e dirija-se ao **Analista** (ou diga explicitamente **EQUIPE**).  
2. Descreva o que quer. A EQUIPE cria a documentação e propõe o desenho.  
3. Quando estiver de acordo, responda no chat com **CONFIRMO** ou **PROSSIGA** — isso é a **sua aprovação** para a equipa avançar para a fase seguinte.  
4. Não é obrigatório criar ficheiros à mão no repositório.

---

## 3. Fluxo oficial de governança — uma linha do tempo

Toda a evolução do produto segue o **Fluxo oficial de governança** (regras completas no documento técnico, link abaixo). Em linguagem simples:

| Ordem | Fase | O que significa | Quem trabalha | Precisa da sua palavra? |
|:---:|:---|:---|:---|:---|
| 1 | **Pedido** | Registo do que pediu | EQUIPE | — |
| 2 | **Desenho funcional** | O que o sistema deve fazer, em termos de negócio | Analista (+ EQUIPE) | ✅ Sim — **CONFIRMO** / **PROSSIGA** |
| 3 | **Desenho técnico** | Como isso encaixa na base de dados e no código | Arquiteto | — (validação interna) |
| 4 | **Construção** | Programação e ecrãs | Dev | — |
| 5 | **Revisão técnica** | O código está bem construído? | Arquiteto | — |
| 6 | **Revisão de negócio** | O código faz o que o desenho funcional pedia? | Analista | — |
| 7 | **Testes** | Baterias automáticas e verificações | QA | — |
| 8 | **Encerramento** | Informação de que a entrega está pronta | EQUIPE | Informação (pode testar na app) |

**Quando algo corre mal** (veto, erro grave, desenho a refazer): volta-se à **primeira etapa afectada** e regista-se no **Registo de retrabalhos** (secção 5). O documento técnico chama isso de «percurso de correção»; no dia-a-dia é: **parar, corrigir, voltar a validar**.

📄 **Documento completo da regra:** [`docs/governanca/FLUXO_SUCESSO_E_FALHA.md`](governanca/FLUXO_SUCESSO_E_FALHA.md)  
*(O nome do ficheiro no disco mantém-se por compatibilidade; no Painel chamamos-lhe **Fluxo oficial de governança**.)*

---

## 4. A sua aprovação — «selo» para a etapa seguinte

O que importa para avançar **não é o nome do ficheiro no GitHub**, e sim **a sua confirmação no chat** nos momentos certos (por exemplo após ler o desenho funcional).

| O que faz no Cursor | O que isso significa para a equipa |
|:---|:---|
| **CONFIRMO** ou **PROSSIGA** | Autorização explícita para continuar — equivale ao **selo do Diretor** naquela fase. |
| Pedir alterações | A equipa ajusta o desenho e volta a pedir a sua confirmação. |

A equipa **regista** essas aprovações nos documentos da pasta da demanda (por exemplo `03_confirmacao_diretor.md`), para haver **rasto** sem o Diretor ter de editar o Git.

---

## 5. Registo de retrabalhos (reabertura de etapas)

Use esta tabela quando uma **correção obrigue a refazer** uma fase já considerada fechada (ex.: desenho funcional rebentado nos testes, veto do Arquiteto, falha na verificação automática no servidor).

| Data | Demanda | Etapa afectada | Origem | Resumo do problema | O que se fez | N.º de vezes (nesta demanda) |
|:---|:---|:---|:---|:---|:---|:---:|
| *—* | *—* | *—* | *—* | *Nenhum registo ainda.* | *—* | *—* |

**Como preencher:** a **EQUIPE** acrescenta uma **linha nova** por evento; o campo **Origem** pode ser: Diretor, Analista, Arquiteto, Dev, QA ou CI (verificação automática).

---

## 6. Esclarecimento: nome do ficheiro no repositório (histórico `SUCESSO_E_FALHA`)

*(Isto responde à dúvida sobre as duas «fases» que tinham sido sugeridas para o nome do fluxo.)*

Hoje o ficheiro normativo chama-se **`FLUXO_SUCESSO_E_FALHA.md`**. «Sucesso» aí significa **percurso normal até à entrega**; «Falha» significa **percurso quando há veto ou retrabalho** — são **dois caminhos** no mesmo regulamento, não um «prémio» ou «castigo».

**Duas formas de alinhar o nome com «Fluxo oficial de governança»:**

| Opção | O que implica |
|:---|:---|
| **A — Só palavras no Painel** | Continuamos a chamar o fluxo de **Fluxo oficial de governança** aqui e nas conversas. O **ficheiro mantém o nome antigo**; os links no projecto **não** mudam. |
| **B — Renomear o ficheiro** | Mudar o nome para algo como `FLUXO_OFICIAL_GOVERNANCA.md` e **actualizar todas as referências** no código, testes, regras do Cursor e documentação. |

**Pode usar qualquer uma.** Para **avançar etapas**, o que vale é a **sua confirmação** (**CONFIRMO** / **PROSSIGA**) e os **pareceres da equipa** nos documentos da demanda — não depende de escolher A ou B.

---

## 7. Pontos de controlo (resumo técnico)

Cada **entrega na nuvem** (repositório Git) vem a pares com **actualização deste Painel** e do ficheiro de estado na app. Os **pontos ímpares** fecham com: alterações guardadas + registo no histórico do Git + envio para o servidor.

| Ponto | Depois de… | O que fica guardado no repositório | O que se actualiza no Painel / estado |
|:---:|:---|:---|:---|
| **PC1** | O Diretor aprovar o desenho funcional no chat | Ficheiros `01`–`03` da pasta da demanda | **PC2** |
| **PC3** | Validado o desenho técnico | Desenho lógico + validação do Analista | **PC4** |
| **PC5** | Validado o código pelo Arquiteto | Parecer do Arquiteto | **PC6** |
| **PC7** | Validado o código pelo Analista + plano de testes | Parecer + caderno de testes | **PC8** |
| **PC9** | Ajustes ao plano de testes (se existirem) | Actualização do plano | **PC10** |
| **PC11** | Testes finais | Parecer do QA | **PC12** |
| **PC13a** | Informação de conclusão | `99_encerramento.md` | **PC13b** |

*Definição completa de «ponto de controlo no repositório»:* ver secção no [`FLUXO_SUCESSO_E_FALHA.md`](governanca/FLUXO_SUCESSO_E_FALHA.md).

### 7.1 GitHub Actions no ramo `develop`

Cada **push** para **`origin/develop`** dispara verificações na nuvem. Duas workflows complementam-se:

| Nome na lista do GitHub | Ficheiro | Papel |
|:---|:---|:---|
| **FLUXO OFICIAL DE GOVERNANCA** | [`.github/workflows/fluxo_oficial_governanca.yml`](../.github/workflows/fluxo_oficial_governanca.yml) | Confirma **artefactos** do Fluxo oficial (norma, Painel, `.cursorrules`, `status_demanda.json`, README de demandas, `CADERNO_TESTES_MASTER`, base `src/`) e corre **`pytest tests/test_governanca.py`**. Os passos seguem as **fases A–F** / **PC1–PC13** (rótulos no log da Action). |
| **Validador Maestro V2** | [`.github/workflows/qa_automatico.yml`](../.github/workflows/qa_automatico.yml) | **Suite completa** `pytest tests/` + dependências do projecto — barreira principal de regressão técnica. |

**Branch protection:** se alguma regra exigir um *required status check* pelo **nome antigo** da workflow (*Fabrica Zimmermann…*), actualize no GitHub (**Settings → Rules / Branches**) para o novo nome **FLUXO OFICIAL DE GOVERNANCA** (ou para o job **Verificação — Fluxo oficial…**, conforme a UI mostrar).

---

## 8. Marcos de produto já entregues (resumo)

| Marco | Estado | Notas para o negócio |
|:---|:---:|:---|
| **E11 — Pré-venda na agenda** | ✅ | Marcar sem venda imediata; fechar na Venda; ligar vendas à visita. |
| **E09 — Agendamentos** | ✅ | Calendário, estados, buffer com vendas, colaboradores. *Detalhe técnico extenso:* [Anexo A — E09](#anexo-a--e09-agendamentos-detalhe). |
| **E08 — Relatórios** | ✅ | Gráficos, filtros, exportar dados. |
| **E07 — Vendas** | ✅ | Registo de venda, descontos, pagamentos, parcelas. |
| **E06 — Catálogo e colaboradores** | ✅ | Serviços (vários tipos), pacotes, eventos, equipa. |

---

## 9. Plano das 15 etapas técnicas (por marco)

Cada grande entrega (E06, E07, …) segue internamente **15 passos** (desde configuração até envio para o `develop`). Estado global: **concluído** para o que já está no ar.

| # | Etapa | Onde validar | Estado |
|:---:|:---|:---|:---:|
| 01 | Configuração | [`.cursorrules`](../.cursorrules) · [Fluxo oficial](governanca/FLUXO_SUCESSO_E_FALHA.md) · [`CADERNO_MESTRE.md`](CADERNO_MESTRE.md) · [`app.py`](../src/app.py) | ✅ |
| 02 | Clientes | [`cliente.py`](../src/modules/cliente.py) · [`test_qa_auto.py`](../tests/test_qa_auto.py) | ✅ |
| 03 | Colaboradores | [`colaborador.py`](../src/modules/colaborador.py) · [`test_colaborador.py`](../tests/test_colaborador.py) | ✅ |
| 04 | Proposta / escopo | [`CONTROLE_DE_VOO.md`](../CONTROLE_DE_VOO.md) | ✅ |
| 05 | Estrutura de dados | [`MODELO_ARQUITETURA.md`](MODELO_ARQUITETURA.md) | ✅ |
| 06 | Aspecto visual / páginas | [`theme.py`](../src/ui/theme.py) · páginas em [`ui/`](../src/ui/) | ✅ |
| 07 | Base de dados | [`connection.py`](../src/database/connection.py) | ✅ |
| 08 | Regras de negócio no código | `modules/` (`venda`, `agendamento`, …) | ✅ |
| 09 | Testes automáticos | [`tests/`](../tests/) | ✅ |
| 10 | Verificação no servidor (CI) | **FLUXO OFICIAL DE GOVERNANCA** + **Validador Maestro V2** em [`.github/workflows/`](../.github/workflows/) | ✅ |
| 11 | Testes locais antes de enviar | `pytest tests/` | ✅ |
| 12 | Documentação | `docs/` · `CONTROLE` · este painel | ✅ |
| 13 | Revisão de links | Esta tabela | ✅ |
| 14 | Revisão visual na app | Vendas, Dashboards, Agendamentos (incl. pré-venda) | ✅ |
| 15 | Envio final para `develop` | Histórico Git | ✅ |

**Legenda:** ✅ Feito · 🚧 Em curso · ⚪ Ainda não começado

**Nota:** as alterações só ficam **visíveis no servidor de verificação (GitHub Actions)** depois de estarem **enviadas para o repositório na nuvem** (`develop`).

---

## 10. Concordância marcos ↔ 15 etapas

| Marco | Cobertura (resumo) |
|:---|:---|
| E01 V11 | Configuração, tema, base, documentação |
| E02/E03 Clientes e morada | Cadastro, migrações, testes |
| Governança / Fluxo oficial | [`FLUXO_SUCESSO_E_FALHA.md`](governanca/FLUXO_SUCESSO_E_FALHA.md), pontos PC1–PC13, estado na app |
| E04 Colaboradores | Módulo colaboradores, testes |
| E06 Catálogo | Pacotes, eventos, UI catálogo |
| E07 Vendas | Vendas, testes `test_venda` |
| E08 Relatórios | Dashboards, Plotly, `test_relatorios` |
| E09 Agendamentos | Agenda, buffer, testes |
| E11 Pré-venda | Extensão E09 + vendas, 49 testes |

---

## 11. Histórico de entregas (mais recente primeiro)

- **CI — Fluxo oficial no GitHub:** workflow renomeada para **FLUXO OFICIAL DE GOVERNANCA** (`fluxo_oficial_governanca.yml`); removido `orquestrador_zimmermann.yml`; verificações alinhadas às fases A–F / PC1–PC13 + smoke `test_governanca.py` (2026-04-06).
- **E11 fechada** — Pré-venda na agenda; código `a6a9a8f`; documentação de fecho `f07f85b`; **49** testes; estado da app reposto sem demanda activa.
- **`6671f3d`** — Entrada **`@Files`**, documentação automática pela EQUIPE, regras do Cursor, painel de fluxo na app.
- **`f92c4f2`** — Fluxo de governança completo no documento normativo; **43** testes.
- **`f07395c`** — Checkpoints por persona no Painel.
- **`7dfc53d`** — Sincronização E07–E09 no `develop` (**40** testes nessa altura).
- **E08, E07, E06** — Ver registos anteriores no Git e em [`CONTROLE_DE_VOO.md`](../CONTROLE_DE_VOO.md).

**Ideias para próximas melhorias de produto:** conflitos de horário na agenda; mais relatórios; datas na venda — a definir com novo pedido **`@Files`**.

---

## Anexo A — E09 Agendamentos (detalhe)

**Estado do ciclo:** etapas 01–15 **concluídas** (inclui envio para `develop`).

| # | Etapa | Estado | Nota breve |
|:---:|:---|:---:|:---|
| 01–03 | Configuração, Clientes, Colaboradores | ✅ | Suporte a filtros e equipa na agenda |
| 04 | Proposta / escopo | ✅ | Alinhado com o Diretor |
| 05 | Estrutura de dados | ✅ | Tabelas `agendamentos`, `agendamento_colaboradores` — [`MODELO`](MODELO_ARQUITETURA.md) |
| 06 | UI | ✅ | [`page_agendamentos.py`](../src/ui/page_agendamentos.py), tema `AGENDA_*` |
| 07 | Base de dados | ✅ | [`connection.py`](../src/database/connection.py) |
| 08 | Regras | ✅ | [`agendamento.py`](../src/modules/agendamento.py) — estados, buffer, cancelamento |
| 09 | Testes | ✅ | [`test_agendamento.py`](../tests/test_agendamento.py) — **inclui E11 pré-venda** |
| 10–12 | CI, documentação | ✅ | — |
| 13–15 | Revisão, QA visual, Git | ✅ | Smoke: Início → Agendamentos |

**Lembrete:** na altura do fecho E09 contavam-se **40** testes; com **E11** a suite passou a **49**.

**Escopo pedido (resumo):** data + hora início/fim + colaboradores; calendário com sessões, eventos e coworking; estados Agendado / Confirmado / Concluído / Cancelado; ligação ao pagamento da venda; buffer de sessões por agendar; filtros e cores por estado e tipo.

**Decisões do Diretor (validadas):** ao cancelar, escolher se o crédito **volta** ao buffer ou **não**; buffer inclui pacote e sessão avulsa; horário com fim > início; léxico visual por tipo (sessão avulsa, pacote, coworking, evento).

**Sugestões técnicas registadas (Analista):** modelo crédito + ocorrência; máquina de estados; rótulos de pagamento derivados da venda; fases futuras (conflito de horário, relatórios).

---

## Anexo B — E08 Dashboards

**Estado:** ✅ concluído. Filtros, agrupamentos, KPIs, gráficos Plotly, CSV. Ver [`page_dashboards.py`](../src/ui/page_dashboards.py), [`relatorios.py`](../src/modules/relatorios.py). Testes: **36** na altura do fecho E08.

---

## Anexo C — E07 Vendas

**Estado:** ✅ concluído. Cliente, itens, descontos, pagamento integral/parcial/previsto. Ver [`page_vendas.py`](../src/ui/page_vendas.py), [`venda.py`](../src/modules/venda.py). Testes: **33** na altura do fecho E07.

---

## Anexo D — E06 Catálogo híbrido

**Estado:** ✅ concluído. Sessão, Produto, Coworking, Pacote, Evento; evolução de colaboradores. Ver [`catalogo.py`](../src/modules/catalogo.py), `app.py`. **28** testes na altura do fecho E06.

---

## Glossário rápido

| Termo | Significado simples |
|:---|:---|
| **EQUIPE** | O agente no Cursor que desempenha Analista, Arquiteto, programador e QA. |
| **`develop`** | Ramo principal de desenvolvimento no Git — é para lá que vão as entregas. |
| **PC** | Ponto de controlo — momento em que se guarda prova no repositório e se actualiza este painel. |
| **pytest** | Programa que corre os testes automáticos do projecto. |
| **CI / Actions** | Verificações no GitHub ao enviar para `develop`: **FLUXO OFICIAL DE GOVERNANCA** (governança) e **Validador Maestro V2** (pytest completo). |
