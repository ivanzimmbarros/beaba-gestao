# Painel operacional — Fluxo de 15 Etapas

**Processo padrão de entrega:** *Fluxo de 15 Etapas* (governança em [`.cursorrules`](../.cursorrules)).

**Instrução:** atualizar **antes** de alterações de código (intenção) e **depois** (estado, links, registo). **Além disso:** ao **terminar cada bloco de persona** (Analista, Arquiteto, Dev, QA), executar o **checkpoint Git** correspondente na tabela abaixo (**commit + push** em `develop`), para o painel reflectir **evolução local e remota**. Em **falha** que exija **recomeço**, repetir os checkpoints afectados com commits e mensagens **correctas** (não deixar `PAINEL`/`CONTROLE` ✅ desalinhados de `origin/develop`).

**Última revisão do painel:** 2026-04-06 — **Checkpoints Git por persona** (obrigatórios após cada bloco Analista / Arquiteto / Dev / QA + regra de reinício). Referência histórica: **E07–E09** sincronizados em `develop` (`7dfc53d` + doc); a Action só reflecte o que está no remoto.

---

## Checkpoints Git por persona (evolução local **e** remota)

O **Painel operacional** deve documentar o estado do trabalho **no repositório**, não só no disco local. Cada persona, ao **concluir o seu bloco** de actividades no ciclo de entrega, **atualiza o Git** (`develop`): **commit** (mensagem clara com persona + marco) e **push** (para Actions e auditoria).

| Ordem | Persona | Momento do checkpoint | O que entra no Git (mínimo) |
|:---:|:---|:---|:---|
| 1 | **Analista** | Fim do bloco de análise e alinhamento (ex.: etapa 04; proposta; decisões do Diretor; revisão de links / tabela global quando for o foco da entrega) | `docs/PAINEL_OPERACIONAL.md`, `CONTROLE_DE_VOO.md` e demais docs de escopo; **push** em `develop`. *Ex. mensagem:* `docs(analista): ciclo EX — etapa 04 proposta`. |
| 2 | **Arquiteto** | Fim do bloco de estrutura e dados (ex.: etapa 05; `MODELO`; contratos de BD / pastas acordados) | `docs/MODELO_ARQUITETURA.md`, actualizações ao `PAINEL` (etapas 05–07 conforme aplicável); **push** em `develop`. *Ex.:* `docs(arquiteto): MODELO + painel etapa 05`. |
| 3 | **Dev** | Fim do bloco de implementação (UI, módulos, migrações, conforme tarefas do ciclo) | Código + `connection.py` / testes novos se já existirem nesta fase; `PAINEL` **antes e depois** das alterações (intenção + fecho), alinhado à regra 4 do Diretor; **push** em `develop`. *Ex.:* `feat(dev): módulo X — painel etapas 06–08`. |
| 4 | **QA** | Fim do bloco de validação (`pytest`, smoke, coerência do `PAINEL` com o código, CI verde quando aplicável) | Ajustes finais de testes/docs; `PAINEL` com estados finais das etapas; **commit + push** que dispare as Actions. Respeitar bloqueio: **não** declarar fecho nem push se a auditoria técnica obrigatória estiver a falhar (ver [`.cursorrules`](../.cursorrules)). *Ex.:* `test(qa): pytest + painel etapas 09–14`. |

**Etapa 15 (commit final + push `develop`)** no fluxo das 15 etapas corresponde ao **fecho do ciclo** após o bloco **QA** (pode coincidir com o .º checkpoint de QA ou ser um último commit de consolidação, desde que o remoto fique fiel ao painel).

### Falha, veto ou recomeço

- Se **CI / Actions**, **pytest**, **veto de QA** ou **mudança de escopo** obrigarem a **refazer** parte do trabalho: **repetir** os checkpoints Git **a partir da persona / etapa afectada**, com novos commits (ou amend **só** se a política do repositório o permitir e o histórico continuar claro).
- Actualizar de novo o **`PAINEL`** e o **`CONTROLE`** para reflectir a **verdade corrente** (incluindo retirar ✅ prematuros ou marcar 🚧 até novo push).
- **Proibido** considerar uma persona ou etapa **concluída** no painel se o estado **não** estiver **visível em `origin/develop`** após o checkpoint respectivo (salvo decisão explícita do Diretor documentada no registo).

---

## Ciclo E09 — Agendamentos

**Estado do ciclo:** **etapas 01–15 concluídas** (inclui push `develop`). *Nota de governança:* entregas anteriores ficaram só no working copy até este envio; o procedimento de 15 etapas exige **commit + push** para a Action e o repositório serem prova de auditoria.

| # | Etapa | Estado | Nota |
|:---:|:---|:---:|:---|
| 01 | Configuração | ✅ | Herdado |
| 02 | Cadastro de Clientes | ✅ | Dimensão **Cliente** em filtros e buffers |
| 03 | Colaboradores + habilitações | ✅ | Colaborador(es) por ocorrência; `listar_clientes_resumo` para filtros |
| 04 | Proposta / escopo (Analista) | ✅ | Decisões Diretor incorporadas (ver bullets abaixo) |
| 05 | Estrutura e dados (Arquiteto) | ✅ | `agendamentos`, `agendamento_colaboradores`; secção E09 em [`MODELO_ARQUITETURA.md`](MODELO_ARQUITETURA.md) |
| 06 | Tema / UI | ✅ | [`page_agendamentos.py`](../src/ui/page_agendamentos.py); `AGENDA_*` em [`theme.py`](../src/ui/theme.py) |
| 07 | Persistência / migrações | ✅ | [`connection.py`](../src/database/connection.py) + índices |
| 08 | Regras de domínio | ✅ | [`agendamento.py`](../src/modules/agendamento.py) — estados, buffer, cancelamento `devolver_ao_buffer`, rótulo pagamento |
| 09 | Testes automáticos | ✅ | [`tests/test_agendamento.py`](../tests/test_agendamento.py) |
| 10 | CI / workflows | ✅ | Regressão existente |
| 11 | `pytest` local | ✅ | `python -m pytest tests/ -v` — **40** testes |
| 12 | Documentação técnica | ✅ | `MODELO`, `CONTROLE` #06, este painel; KPIs semana na página agenda (extensão fina `relatorios`/dashboards opcional) |
| 13 | Revisão de links (Analista) | ✅ | Tabela global abaixo |
| 14 | Validação visual (QA) | ✅ | Smoke recomendado: Início → **Agendamentos** → buffer → criar → semana → estado/cancelar |
| 15 | Commit final + push `develop` | ✅ | Fecho E09 no Git (`develop`; ver checkpoints por persona) |

**Escopo pedido (validação do entendimento):**

- **Área de agendamento:** **data** + **previsão hora início e hora fim** (controlo de sobreposição na agenda) e **colaborador(es)** por ocorrência (sessão / evento / coworking).
- **Calendário unificado:** visão com **Serviços (sessões), Eventos e Coworking** integrados, com **detalhe** dos registos (cliente, serviço, estado, pagamento, colaboradores).
- **Janelas operacionais:** destaque **semana atual** e **próxima semana** para fluxo de **confirmação** com o cliente.
- **Estados operacionais:** criação em **AGENDADO** (default); pode passar a **CONFIRMADO** (cliente confirmou); após execução **CONCLUÍDO**; **cancelamento** possível **sem** data de remarcação obrigatória, alimentando contadores de **pendentes** / filas de tratamento (ver sugestões).
- **Pagamento na UI do agendamento:** indicar se a **sessão/ocorrência** está **paga** ou **em aberto**, com ligação ao modelo de **vendas** (`vendas` / `estado_pagamento` / recebimentos).
- **Ligação à venda:** no **ato da venda**, permitir associar **datas** (0..N conforme tipo de item); para **pacotes** com várias sessões, **nem todas** obrigatoriamente no momento da venda — **agendar sob demanda**.
- **Buffer «sessões por agendar»:** por **cliente** e por **natureza**, total de **unidades pendentes de agendamento** (pacotes e vendas que gerem créditos de sessão); prioridade operacional; distinguir **pagas vs em aberto** no buffer.
- **Dashboards / relatórios (extensão E08):** totais **agendados**, **confirmados**, **com pagamento em aberto** por período (**previsto** vs **atrasado** conforme regra a fechar).
- **Edição:** alterar **datas** e **colaboradores** em registos existentes.
- **Visual «calendário real»:** **ícones + cor de fundo** por estado operacional e por **tipo de ocorrência**; **filtros no topo** (cliente, serviço, colaborador, agendado/confirmado/concluído/cancelado, situação de pagamento, natureza, período).

**Decisões do Diretor (validadas):**

1. **Cancelamento e buffer:** modelo com **opção explícita** no cancelamento: **devolver crédito ao buffer** (reabre unidade para reagendar) **ou** **não devolver** (crédito consumido / tratamento comercial a definir no ato). Persistir escolha para auditoria e KPIs.
2. **Créditos pendentes — pacote e avulso:** o buffer contempla **ambos**: (a) unidades ligadas a **linhas de pacote** (`servico_pacote_sessoes` / tipo de sessão do pacote quando aplicável); (b) **sessões avulsas** vendidas em linha (ex.: natureza Sessão, quantidade > 1 ou crédito 1:1). Agregações por cliente e por natureza **mantêm** a distinção origem pacote vs avulso quando pertinente.
3. **Horário:** toda ocorrência agendada com **previsão de hora início** e **hora fim** (validação `fim > início` no domínio).
4. **Léxico visual (tipos):** indicadores para separar **sessão avulsa**, **sessão de pacote**, **coworking**; **indicadores complementares** (badge/ícone secundário) para **subtipo** quando relevante (ex.: qual tipo de sessão no pacote, sala em coworking, evento no calendário). **Evento** integra no calendário unificado com o seu próprio marcador. **Produto** (venda de produto físico) **não** gera slot de agenda por defeito; se aparecer em contexto misto, usar marcador de **«não agendável»** ou exclusão do calendário (confirmado na etapa 05 se necessário).

**Incrementos e decisões recomendadas (Analista):**

1. **Modelo de dados em duas camadas:** (A) **Direito / crédito** por `venda_item` (e, para pacote, subtipos por **sessão componente** quando o negócio exigir fila separada por tipo); saldo = vendido − agendado − concluído − cancelado **sem** devolução ao buffer; (B) **Ocorrência** com `data`, **`hora_inicio`**, **`hora_fim`**, colaborador(es), `status`, FK venda/item, snapshot; **cancelamento** com flag **`devolver_ao_buffer`** (BOOLEAN ou equivalente) conforme decisão do utilizador no ato.
2. **Evento vs Coworking vs Sessão:** Evento pode ter **data fixa no catálogo** + ocorrência operacional; Coworking pode exigir **slot** (início/fim) e **sala** (já no catálogo); documentar no MODELO para não misturar regras.
3. **«PENDENTES» após cancelamento:** distinguir **(a)** sessões ainda **por agendar** (buffer), **(b)** agendamentos **cancelados** (KPI próprio), **(c)** **remarcar** opcional — sem obrigar `data_remarcacao`; contadores separados evitam ambiguidade.
4. **Pagamento «por ocorrência»:** enquanto não houver cobrança fracionada por sessão, derivar de **`venda` + `estado_pagamento`** e/ou **parcelas vencidas** (`venda_recebimentos_previstos` vs hoje) para rótulo **em aberto / atrasado / ok** na UI do agendamento.
5. **Máquina de estados sugerida:** `AGENDADO` → `CONFIRMADO` → `CONCLUIDO`; ramos `CANCELADO` (a partir de AGENDADO ou CONFIRMADO); opcional `NAO_COMPARECEU` futuro. Transições validadas em domínio + testes.
6. **Calendário em Streamlit:** grelha semanal custom (HTML/CSS + `st.columns`) ou componente de terceiros; **legenda fixa** com ícone + cor + texto; alinhar tokens em `theme.py` (`AGENDA_STATUS_STYLES`).
7. **Integração na venda (incremental):** **Fase 1** — criar direitos + 0..1 agendamentos na venda; **Fase 2** — buffer + calendário semanal; **Fase 3** — relatórios estendidos + regras «atrasado».
8. **Conflitos de colaborador:** opcional **alerta** (não bloqueante na v1) se colaborador já ocupado no mesmo intervalo.
9. **Auditoria:** `data_alteracao`, `usuario` (se no futuro houver login) ou campo texto «quem alterou» em v1 mínima.

**Entrega incremental sugerida (após confirmação):** **Fase A** — esquema + direitos por `venda_item` + CRUD agendamento simples + estado AGENDADO/CONFIRMADO/CANCELADO; **Fase B** — calendário semana + próxima semana + estilos; **Fase C** — CONCLUÍDO + buffer pacotes + extensão dashboards; **Fase D** — regras «atrasado»/previsto finas + conflitos horário.

---

## Ciclo E08 — Dashboards e Relatórios

**Estado do ciclo:** **E08 concluído** — filtros (Cliente, Serviço, Colaborador, Produto/natureza, Período), Group by, KPIs, série temporal, Top N, Pareto, tabela + CSV; entrada no Início.

| # | Etapa | Estado | Nota |
|:---:|:---|:---:|:---|
| 01 | Configuração | ✅ | Herdado |
| 02 | Cadastro de Clientes | ✅ | Dimensão **Cliente** nos filtros |
| 03 | Colaboradores + habilitações | ✅ | `colaborador_id` opcional por linha de venda + filtro nos relatórios |
| 04 | Proposta / escopo (Analista) | ✅ | Confirmado — Fase A receita; colaborador na linha; Plotly |
| 05 | Estrutura e dados (Arquiteto) | ✅ | [`MODELO_ARQUITETURA.md`](MODELO_ARQUITETURA.md) — analytics E08 |
| 06 | Tema / UI | ✅ | [`page_dashboards.py`](../src/ui/page_dashboards.py) · [`theme.py`](../src/ui/theme.py) `ANALYTICS_COLORS` · [`app.py`](../src/app.py) |
| 07 | Persistência / migrações | ✅ | `venda_itens.colaborador_id` + índices em [`connection.py`](../src/database/connection.py) |
| 08 | Regras de domínio | ✅ | [`relatorios.py`](../src/modules/relatorios.py) · [`venda.py`](../src/modules/venda.py) (colaborador na linha) |
| 09 | Testes automáticos | ✅ | [`tests/test_relatorios.py`](../tests/test_relatorios.py) |
| 10 | CI / workflows | ✅ | Sem alteração estrutural |
| 11 | `pytest` local | ✅ | `python -m pytest tests/ -v` — **36** testes |
| 12 | Documentação técnica | ✅ | `MODELO`, `CONTROLE` #05, este painel |
| 13 | Revisão de links (Analista) | ✅ | Tabela global abaixo |
| 14 | Validação visual (QA) | ✅ | Smoke Streamlit: **Dashboards e Relatórios** |
| 15 | Commit final + push `develop` | ✅ | Após `pytest`; fecho E08 |

**Escopo entregue (E08):**

- **Fase A — «Lucro»:** receita em **linhas** (`SUM(total_linha_centavos)`) como proxy sem custos; **receita em vendas** (cabeçalhos) para comparar com desconto global; texto de ajuda na UI.
- **Filtros:** período, multiselect Cliente / Serviço / Colaborador, checkbox **apenas natureza Produto**.
- **Group by:** Serviço, Cliente, Colaborador, Natureza, Dia, Mês — alimenta ranking, Pareto e tabela.
- **Visual:** cards `st.metric`, gráficos Plotly (linha temporal, barras horizontais Top N, Pareto barras + % cumulativo), cores `ANALYTICS_COLORS`.
- **Export:** CSV do relatório tabular.
- **Vendas:** por linha, **Colaborador (opcional)** no [`page_vendas.py`](../src/ui/page_vendas.py).

---

## Ciclo E07 — Painel de Vendas

**Estado do ciclo:** **E07 concluído** — registo de vendas com cliente (pesquisa + edição + cadastro), catálogo ativo (todas as naturezas), descontos linha/total, bónus, estados de pagamento e `venda_recebimentos_previstos`.

| # | Etapa | Estado | Nota |
|:---:|:---|:---:|:---|
| 01 | Configuração | ✅ | Herdado |
| 02 | Cadastro de Clientes | ✅ | `buscar_cliente_por_whatsapp`, `obter_cliente_completo`, `atualizar_cliente` em [`cliente.py`](../src/modules/cliente.py) |
| 03 | Colaboradores + habilitações | ✅ | E08: `colaborador_id` opcional em `venda_itens` + filtro dashboards |
| 04 | Proposta / escopo (Analista) | ✅ | Confirmado pelo Diretor (bónus + split) |
| 05 | Estrutura e dados (Arquiteto) | ✅ | [`MODELO_ARQUITETURA.md`](MODELO_ARQUITETURA.md) — secção vendas E07 |
| 06 | Tema / UI | ✅ | [`src/ui/page_vendas.py`](../src/ui/page_vendas.py) · entrada em [`app.py`](../src/app.py) |
| 07 | Persistência / migrações | ✅ | [`connection.py`](../src/database/connection.py) — `vendas`, `venda_itens`, `venda_pagamentos`, `venda_recebimentos_previstos` |
| 08 | Regras de domínio | ✅ | [`venda.py`](../src/modules/venda.py) · [`catalogo.py`](../src/modules/catalogo.py) `listar_servicos_para_venda`, `resolver_snapshot_venda` |
| 09 | Testes automáticos | ✅ | [`tests/test_venda.py`](../tests/test_venda.py) |
| 10 | CI / workflows | ✅ | Sem alteração; regressão `qa_automatico.yml` |
| 11 | `pytest` local | ✅ | `python -m pytest tests/ -v` — **33** testes |
| 12 | Documentação técnica | ✅ | `MODELO`, `CONTROLE_DE_VOO`, este painel |
| 13 | Revisão de links (Analista) | ✅ | Tabela global abaixo (E07) |
| 14 | Validação visual (QA) | ✅ | Smoke Streamlit: fluxo **Painel de Vendas** recomendado ao Diretor |
| 15 | Commit final + push `develop` | ✅ | Após `pytest`; fecho E07 |

**Escopo entregue (E07):**

- **Cliente:** pesquisa por contacto; carregar ficha com edição no expander; cadastro completo na mesma página se ainda não existir.
- **Itens:** serviços `ativo=1` (inclui Pacote e Evento); snapshots (`nome`, `descritivo`, `unidade`, `preço`); Evento: escolha **Adulto / Criança**; **bónus** = mesmo `servico_id` com preço 0.
- **Desconto:** por linha e global; **%** ou **€**; totais persistidos em centavos.
- **Pagamento:** estados integral / pendente / parcial / parcelado; **várias linhas** de meio (Dinheiro, Cartão, MBWay); recebimentos previstos com **data + valor**; soma meios + previstos = total final.
- **Relatórios futuros:** histórico em `venda_itens` e cabeçalho `vendas`.

---

## Ciclo E06 — Colaboradores (evolução) + Catálogo de serviços (híbrido)

**Estado do ciclo:** **E06 concluído** — Colaboradores (evolução) + catálogo híbrido **Sessão / Produto / Coworking / Pacote / Evento**; `pytest` **28** testes.

| # | Etapa | Estado | Nota |
|:---:|:---|:---:|:---|
| 01 | Configuração | ✅ | Herdado |
| 02 | Cadastro de Clientes | ✅ | Sem alteração nesta entrega |
| 03 | Colaboradores + habilitações | ✅ | Evolução: `data_insercao_linha`, remoção de linha, edição |
| 04 | Proposta / escopo (Analista) | ✅ | Confirmada pelo Diretor; incremental |
| 05 | Estrutura e dados (Arquiteto) | ✅ | MODELO + `servico_pacote_*` + `servico_evento_participantes` + `catalogo.py` |
| 06 | Tema / UI | ✅ | `src/app.py` — formulários condicionais catálogo; colaboradores UUID linhas |
| 07 | Persistência / migrações | ✅ | [`src/database/connection.py`](../src/database/connection.py) — `_ensure_column` |
| 08 | Regras de domínio | ✅ | `cadastrar_pacote` / `cadastrar_evento` + validações; `listar_servicos` sem Pacote/Evento |
| 09 | Testes automáticos | ✅ | `test_pacote_*`, `test_evento_*` em [`tests/test_catalogo.py`](../tests/test_catalogo.py) |
| 10 | CI / workflows | ✅ | Sem alteração; regressão via `qa_automatico.yml` |
| 11 | `pytest` local | ✅ | `python -m pytest tests/ -v` — 28 testes |
| 12 | Documentação técnica | ✅ | `CADERNO_MESTRE`, `MODELO`, `CONTROLE_DE_VOO`, este painel |
| 13 | Revisão de links (Analista) | ✅ | Tabela global + links módulos catálogo/colaborador |
| 14 | Validação visual (QA) | ✅ | Regressão: **pytest** (28) + **CI**; smoke Streamlit (Colaboradores + Catálogo completo) continua **recomendado** ao Diretor antes de Vendas, mas não bloqueou o fecho E06 |
| 15 | Commit final + push `develop` | ✅ | Push `develop` após `pytest` |

**Escopo entregue (E06):**

- **Fase 1 — Colaboradores + catálogo base:** remoção de linha; data de inserção da linha; edição; Sessão / Produto / Coworking.
- **Fase 2 — Pacote:** linhas 1:N; produto opcional; repasse ref. sugerido+editável; valor venda; `servico_pacote_*`.
- **Fase 3 — Evento:** data, local, observações, interno/convidado, preços criança/adulto/desconto filho adicional; participantes (colaborador ou parceiro) com repasse % ou €; `servico_evento_participantes`; **fora** de `listar_servicos`.

---

## Concordância com o plano das 15 etapas

| Marco entregue | Etapas 01–15 cobertas (resumo) |
|:---|:---|
| **E01 — V11.0** | 01 Configuração, 05 estrutura inicial, 06 tema, 07 BD base, 11 docs (Caderno), 12 CONTROLE |
| **E02 / E02b — Clientes** | 02 Cadastro clientes, 07 migrações, 08 `cliente`, 08–09 testes, 10 CI, 12 docs |
| **E03 — Morada + filhos** | 02 (evolução), 07–09, 12 |
| **Governança — Painel + `.cursorrules` + Git por persona** | 01 (extensão), 11–12, 13–15; **checkpoints** Analista → Arquiteto → Dev → QA (commit+push `develop`); reinício refaz sincronização |
| **E04 — Colaboradores** | 03 Colaboradores + serviços seed, 05 MODELO, 07–10, 12 |
| **CI — Auditorias (`HEAD^`)** | 10 workflows `arquiteto_audit` / `analista_audit` |
| **E06 — Fases 1–3 (catálogo híbrido)** | 03–12 + 13 documental; 14–15 por entrega |
| **E07 — Painel de Vendas** | 02 (evolução cliente), 05–12 MODELO/BD/`venda`/`catalogo`/UI, 09 `test_venda`, 13–15 |
| **E08 — Dashboards e Relatórios** | 05–12 `relatorios`/`page_dashboards`/migração colaborador; 09 `test_relatorios`; 13–15 |
| **E09 — Agendamentos** | 04–14 entregues; 15 commit/push `develop` |

Todas as entregas acima seguiram o *Fluxo de 15 Etapas* com **pytest** (`tests/`) e **push em `develop`**.

---

## Tabela das 15 etapas

| # | Etapa | Link de Validação | Estado |
|:---:|:---|:---|:---:|
| 01 | Configuração | [`.cursorrules`](../.cursorrules) · [`CADERNO_MESTRE.md`](CADERNO_MESTRE.md) · [`app.py`](../app.py) | ✅ |
| 02 | Cadastro de Clientes | [`CADERNO_MESTRE.md`](CADERNO_MESTRE.md) · [`src/app.py`](../src/app.py) · [`src/modules/cliente.py`](../src/modules/cliente.py) · [`tests/test_qa_auto.py`](../tests/test_qa_auto.py) | ✅ |
| 03 | Colaboradores + habilitações | [`CADERNO_MESTRE.md`](CADERNO_MESTRE.md) · [`src/app.py`](../src/app.py) · [`src/modules/colaborador.py`](../src/modules/colaborador.py) · [`src/database/connection.py`](../src/database/connection.py) · [`tests/test_colaborador.py`](../tests/test_colaborador.py) | ✅ |
| 04 | Proposta / escopo (Analista) | [`CONTROLE_DE_VOO.md`](../CONTROLE_DE_VOO.md) · Ciclo E09 | ✅ |
| 05 | Estrutura e dados (Arquiteto) | [`MODELO_ARQUITETURA.md`](MODELO_ARQUITETURA.md) · [`catalogo.py`](../src/modules/catalogo.py) · [`relatorios.py`](../src/modules/relatorios.py) | ✅ |
| 06 | Tema / UI V11 | [`CADERNO_MESTRE.md`](CADERNO_MESTRE.md) · [`theme.py`](../src/ui/theme.py) · [`app.py`](../src/app.py) · [`page_vendas.py`](../src/ui/page_vendas.py) · [`page_dashboards.py`](../src/ui/page_dashboards.py) · [`page_agendamentos.py`](../src/ui/page_agendamentos.py) | ✅ |
| 07 | Persistência / migrações | [`connection.py`](../src/database/connection.py) | ✅ |
| 08 | Regras de domínio | [`colaborador.py`](../src/modules/colaborador.py) · [`catalogo.py`](../src/modules/catalogo.py) · [`venda.py`](../src/modules/venda.py) · [`agendamento.py`](../src/modules/agendamento.py) · [`relatorios.py`](../src/modules/relatorios.py) · [`validators.py`](../src/modules/validators.py) | ✅ |
| 09 | Testes automáticos | [`tests/`](../tests/) · [`test_agendamento.py`](../tests/test_agendamento.py) · [`test_venda.py`](../tests/test_venda.py) · [`test_relatorios.py`](../tests/test_relatorios.py) | ✅ |
| 10 | CI / workflows | [`qa_automatico.yml`](../.github/workflows/qa_automatico.yml) · [`arquiteto_audit.yml`](../.github/workflows/arquiteto_audit.yml) · [`analista_audit.yml`](../.github/workflows/analista_audit.yml) | ✅ |
| 11 | `pytest` local | `python -m pytest tests/ -v` (obrigatório antes de push) | ✅ |
| 12 | Documentação técnica | [`docs/`](.) · [`CONTROLE_DE_VOO.md`](../CONTROLE_DE_VOO.md) · [`PAINEL_OPERACIONAL.md`](PAINEL_OPERACIONAL.md) | ✅ |
| 13 | Revisão de links desta tabela (Analista) | *esta tabela — E09* | ✅ |
| 14 | Validação visual do painel (QA) | *pytest **40** + CI; smoke Vendas + **Dashboards** + **Agendamentos*** | ✅ |
| 15 | Commit final + push `develop` | Git — `develop` atualizado (E07–E09) | ✅ |

**Legenda:** ✅ Concluído · 🚧 Em andamento · ⚪ Pendente

**Nota (governança):** o **Fluxo de 15 Etapas** só fica **demonstrável na Action** quando há **commits no ramo monitorizado** (ex.: `develop`). Trabalho só em disco local **não** dispara workflows nem aparece no GitHub. Ver secção **Checkpoints Git por persona** no topo deste documento para obrigações **após cada bloco** Analista, Arquiteto, Dev e QA.

**Próximo foco de produto:** evoluções E09+ (conflitos de horário, relatórios agregados, datas na venda) conforme roadmap.

---

## Registo da última entrega

- **Entrega (esta revisão):** **Governança — Checkpoints Git por persona** no `PAINEL` (tabela + regra de reinício); instruções no topo alinhadas a [`.cursorrules`](../.cursorrules).
- **Entrega (referência anterior):** **Sincronização Git `develop` — E07, E08 e E09** — commit **`7dfc53d`** (acumulado no working copy após E06; **commit + push** restauram evidência na Action e no histórico). Inclui: **E07** `venda.py`, `page_vendas.py`; **E08** `relatorios.py`, `page_dashboards.py`, Plotly; **E09** `agendamentos`/`agendamento_colaboradores`, `agendamento.py`, `page_agendamentos.py`, **40** testes; `beaba_gestao.db` **removido do índice** Git (mantém-se local, `*.db` ignorado).
- **Entrega (referência anterior):** **E09 — Refinamento com Diretor (Agendamentos)** — validadas decisões de buffer, horários e léxico visual.
- **Entrega (referência anterior):** **E09 — Proposta Analista (Agendamentos)** — escopo inicial; **ciclo E09** aberto.
- **Entrega (referência anterior):** **E08 — Dashboards e Relatórios** — `relatorios.py`; `page_dashboards.py` (Plotly, `ANALYTICS_COLORS`); filtros + Group by + KPIs + temporal + Top N + Pareto + tabela/CSV; `venda_itens.colaborador_id` + UI venda; dependência `plotly`; **36** testes.
- **Entrega (referência anterior):** **E07 — Painel de Vendas** — BD vendas; `page_vendas.py`; **33** testes (antes de E08).
- **Entrega (referência anterior):** **E06 Fase 3 — Evento** — colunas `evento_*` em `servicos`; `servico_evento_participantes`; `cadastrar_evento`, `_detalhe_evento`; UI `NATUREZAS_CATALOGO_FASE3` em `src/app.py`; testes `test_evento_*`.
- **Referência técnica:** `CONTROLE_DE_VOO.md` (Log), `MODELO_ARQUITETURA.md`, `CADERNO_MESTRE.md` (regra 4).
- **Notas:** Evento: ≥1 participante; não repetir o mesmo colaborador em duas linhas; parceiro exige nome. Pacote: ver nota anterior (sessão duplicada).
