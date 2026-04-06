# 🚀 PAINEL DE CONTROLE DE VOO - BEABA GESTÃO (V11.0 / V8.1)

**PROJETO:** Centro Terapêutico BeaBa Materno  
**DESENHO FUNCIONAL:** V11.0 — Identidade integrada (ver `docs/CADERNO_MESTRE.md`)  
**STATUS ATUAL:** 🔵 DESENVOLVIMENTO EM CURSO (#01)  
**CONTADOR DE INTEGRIDADE MASSIVA (N+1):** [ 0 ] Funcionalidades Validadas

**PROCESSO OBRIGATÓRIO:** toda evolução segue **`docs/governanca/FLUXO_SUCESSO_E_FALHA.md`** (passos 1–25, PC1–PC13, fluxo FALHA) e [`.cursorrules`](../.cursorrules). **Entrada:** demanda via **Cursor `@Files` → Analista**; **EQUIPE** gera toda a documentação e controlos (sem exigir ficheiros manuais do Diretor). Git (`develop`) + `PAINEL` + `status_demanda.json` **sincronizados** após cada par de ponto de controlo.

---

## 📦 MÓDULO 01: GESTÃO CORE (CLIENTES, COLABORADORES, CATÁLOGO)

| ID | FUNCIONALIDADE | ANALISTA | ARQUITETO | DEV | QA (REGRESSÃO) | STATUS FINAL |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| #01 | Cadastro de Clientes (contacto 11 + ficha alargada) | 🟢 | 🟢 | 🔵 | 🟢 | EM CURSO |
| #02 | Cadastro de Colaboradores (habilitações + % repasse + edição + data linha) | 🟢 | 🟢 | 🟢 | 🟢 | EM CURSO |
| #03 | Catálogo Híbrido (5 naturezas + composições) | 🟢 | 🟢 | 🟢 | 🟢 | E06 Fases 1–3 entregues |
| #04 | Painel de Vendas (registo, descontos, split, parcelas) | 🟢 | 🟢 | 🟢 | 🟢 | E07 entregue — `venda.py` + `page_vendas.py` |
| #05 | Dashboards e Relatórios (KPI, Pareto, Top N, filtros) | 🟢 | 🟢 | 🟢 | 🟢 | E08 entregue — `relatorios.py` + `page_dashboards.py` |
| #06 | Agendamentos (calendário, estados, buffer pacotes, vendas) | 🟢 | 🟢 | 🟢 | 🟢 | **E09 entregue** — `agendamento.py` + `page_agendamentos.py`; **push `develop`** na sincronização E07–E09 (etapa 15 do painel) |

**Legenda:** ⚪ Pendente | 🔵 Em Curso | 🟢 Sucesso | 🔴 Falha (Veto)

---

## 🛡️ PROTOCOLO DE SEGURANÇA E REGRESSÃO (V8.1)
1. **REGRESSÃO PERPÉTUA:** Validar de 1 até N-1 a cada novo deploy.
2. **INTEGRIDADE DE DADOS:** SQL Blindado com CHECK constraints (GLOB).
3. **SOBERANIA DO DIRETOR:** Deploy em main exige validação QA.

---

## Log de Progresso

- [x] Ambiente de Desenvolvimento (Cursor + Personas + Git) configurado e sincronizado.
- [x] **E01 — V11.0:** `docs/CADERNO_MESTRE.md` publicado; estrutura `src/ui` + `src/app.py` (tema Verde BeaBa, serifas, dashboard 4 blocos); shell navegável com retorno e breadcrumbs nas vistas internas.
- [x] **E02 — Cadastro cliente refinado:** inputs com fundo `#F7F7F7`; ficha com morada, email, sexo, filhos (idade em anos + sexo), gravidez + DPP se aplicável, contactos de emergência dinâmicos (11 dígitos), observações opcionais; migração SQLite + testes + CI em `tests/test_qa_auto.py`.
- [x] **E02b — Hotfix Streamlit:** `SEXOS` centralizado em `src/modules/constants.py` (import estável para `app.py` / `cliente.py`, evita `ImportError` por ficheiro desatualizado ou cache).
- [x] **E03 — Morada estruturada + filhos com nome:** campos de endereço para pesquisa (CP PT validado; freguesia obrigatória; distrito opcional); `cliente_filhos.nome`; base limpa sem migração de legado em filhos.
- [x] **E04 — Colaboradores:** label **Gestão de Colaboradores**; cadastro com morada espelhada, idade ≥18, contacto exclusivo; `servicos` + seeds; `colaborador_servicos` com repasse 0,01%–100,00% (centésimos); UI com linhas incrementáveis e atalho para Catálogo; `src/modules/validators.py`; testes `tests/test_colaborador.py`.
- [x] **E05 — CI auditorias:** workflows `arquiteto_audit` / `analista_audit` com `fetch-depth: 0` e fallback quando não existe `HEAD^` (evita exit 128).
- [x] **Painel 15 etapas — reconciliação:** `docs/PAINEL_OPERACIONAL.md` atualizado: etapas 04–15 marcadas conforme entregas reais; tabela de mapeamento E01–E04 ↔ plano; links de validação (incl. auditorias e `.cursorrules`).
- [x] **E06 — Fase 1 (incremental):** Colaboradores — remoção de linha de serviço (UUID), data de inserção da linha (obrigatória), edição de ficha (`atualizar_colaborador`, `obter_colaborador`); `media_repasse_percentual_servico()` para uso futuro em Pacotes (auto + editável). Catálogo — `src/modules/catalogo.py`: Sessão, Produto, Coworking; descritivo obrigatório; ativo/inativo; tabela de visualização em `src/app.py`; migrações em `connection.py`; testes `tests/test_catalogo.py` + extensão `tests/test_colaborador.py`.
- [x] **E06 — Fase 2 (Pacote):** Tabelas `servico_pacote_sessoes`, `servico_pacote_produtos`; colunas `pacote_*` em `servicos`; `cadastrar_pacote`, `repasse_medio_ponderado_pacote`; UI Pacote no catálogo (linhas 1:N, produto opcional, sugestão + campo editável de % referência, valor venda); `listar_servicos` exclui `Pacote`/`Evento` para habilitações; `PRAGMA foreign_keys=ON`; testes `test_pacote_ok_e_listagem`, `test_pacote_sessao_duplicada_rejeita`.
- [x] **E07 — Painel de Vendas:** tabelas `vendas`, `venda_itens`, `venda_pagamentos`, `venda_recebimentos_previstos`; `cliente` com pesquisa/atualização; `catalogo` com `listar_servicos_para_venda` + `resolver_snapshot_venda` (bónus ligado a `servico_id`); UI `src/ui/page_vendas.py`; testes `tests/test_venda.py`; decisões: split de meios; bónus sempre linha de serviço.
- [x] **E08 — Dashboards e Relatórios:** `src/modules/relatorios.py`; `src/ui/page_dashboards.py` (Plotly + paleta `ANALYTICS_COLORS`); filtros + Group by + Pareto/Top N + CSV; `venda_itens.colaborador_id` + UI; Fase A receita como proxy de lucro; testes `tests/test_relatorios.py`; módulo **#05**.
- [x] **E09 — Agendamentos:** tabelas `agendamentos`, `agendamento_colaboradores`; `src/modules/agendamento.py`; `src/ui/page_agendamentos.py` + botão no Início; buffer (pacote + avulso + coworking + evento); `devolver_ao_buffer` no cancelamento; `tests/test_agendamento.py`; **40** testes em `pytest`; módulo **#06** — **commit + push `develop`** na mesma entrega que sincroniza **E07 e E08** (antes só existiam no disco local).
- [x] **Governança — Evidência no GitHub:** **antes** da sincronização **E07–E09** em `develop`, o remoto **não continha** esses ficheiros (último commit visível: **`95f093d`** / E06). A Action *Fabrica Zimmermann* só reflete o que está em `develop`; após **commit + push** da sincronização, o histórico e a CI alinham com `PAINEL_OPERACIONAL` / `CONTROLE_DE_VOO`.
- [x] **Governança — Checkpoints Git por persona:** `docs/PAINEL_OPERACIONAL.md` passa a exigir **commit + push** em `develop` ao fim de cada bloco **Analista**, **Arquiteto**, **Dev** e **QA**, com regra de **reinício** se houver falha; `.cursorrules` alinhado. O painel reflecte evolução **local e remota** (`origin/develop`).
- [x] **Governança — Regra máxima SUCESSO/FALHA:** `docs/governanca/FLUXO_SUCESSO_E_FALHA.md` (processo completo, críticas/sugestões, exemplos FALHA); PC1–PC13 (Git→Painel); `docs/CADERNO_TESTES_MASTER.md`; `docs/governanca/status_demanda.json` + UI **Fluxo e governança**; `.cursorrules` como norma suprema.
- [x] **Governança — Canal @Files e documentação automática:** entrada obrigatória da demanda via **Cursor `@Files` → Analista**; **EQUIPE** gera e mantém toda a documentação e painéis (sem exigir ficheiros complementares do Diretor); `.cursorrules` e `FLUXO_SUCESSO_E_FALHA.md` actualizados.
- [x] **E06 — Fase 3 (Evento):** Colunas `evento_*` em `servicos`; tabela `servico_evento_participantes`; `cadastrar_evento`; UI Evento (data, local, observações, interno/convidado, preços criança/adulto/desconto filho adicional, participantes colaborador ou parceiro com repasse % ou €); listagem detalhada; testes `test_evento_ok_e_listagem`, `test_evento_sem_participantes_falha`, `test_evento_colaborador_duplicado_falha`.
- [ ] **E11 — Pré-venda × Agenda (demanda `2026-04-06_E11_pre_venda_agenda`):** Diretor **PROSSIGA** (2026-04-06); **PC1–PC4** fechados — `01`–`05` no dossier; **Fase C** (Dev) em curso — implementar [`04_desenho_logico.md`](docs/governanca/demandas/2026-04-06_E11_pre_venda_agenda/04_desenho_logico.md); a seguir **PC5** (Arquiteto) após código.
