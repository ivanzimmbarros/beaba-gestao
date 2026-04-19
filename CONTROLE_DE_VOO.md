# 🚀 PAINEL DE CONTROLE DE VOO - BEABA GESTÃO (V11.0 / V8.1)

**PROJETO:** Centro Terapêutico BeaBa Materno  
**DESENHO FUNCIONAL:** V11.0 — Identidade integrada (ver `docs/CADERNO_MESTRE.md`)  
**STATUS ATUAL:** 🔵 DESENVOLVIMENTO EM CURSO (#01)  
**CONTADOR DE INTEGRIDADE MASSIVA (N+1):** [ 269 ] Testes automatizados na suite `pytest tests/` (auditoria 2026-04-19)

**PROCESSO OBRIGATÓRIO:** toda evolução segue o **Fluxo oficial de governança** em **`docs/governanca/FLUXO_SUCESSO_E_FALHA.md`** (passos 1–25, PC1–PC13; percurso de correção **FALHA**) e [`.cursorrules`](../.cursorrules). **Entrada:** demanda via **Cursor `@Files` → Analista**; **EQUIPE** gera toda a documentação e controlos (sem exigir ficheiros manuais do Diretor). Git (`develop`) + `PAINEL` + `status_demanda.json` **sincronizados** após cada par de ponto de controlo.

---

## 📦 MÓDULO 01: GESTÃO CORE (CLIENTES, COLABORADORES, CATÁLOGO)

| ID | FUNCIONALIDADE | ANALISTA | ARQUITETO | DEV | QA (REGRESSÃO) | STATUS FINAL |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| #01 | Cadastro de Clientes (E.164 + NIF + ficha alargada — **E16**) | 🟢 | 🟢 | 🟢 | 🟢 | E16 entregue |
| #02 | Cadastro de Colaboradores (habilitações + % repasse + edição + data linha) | 🟢 | 🟢 | 🟢 | 🟢 | EM CURSO |
| #03 | Catálogo Híbrido (5 naturezas + composições) | 🟢 | 🟢 | 🟢 | 🟢 | E06 Fases 1–3 entregues |
| #04 | Painel de Vendas (registo, descontos, split, parcelas) | 🟢 | 🟢 | 🟢 | 🟢 | E07 entregue — `venda.py` + `page_vendas.py` |
| #05 | Dashboards e Relatórios (KPI, Pareto, Top N, filtros) | 🟢 | 🟢 | 🟢 | 🟢 | E08 entregue — `relatorios.py` + `page_dashboards.py` |
| #06 | Agendamentos (calendário, estados, buffer, **pré-venda E11**, vendas) | 🟢 | 🟢 | 🟢 | 🟢 | **E09 + E11** — `agendamento.py` + `page_agendamentos.py`; pré-venda / contexto visita (`a6a9a8f` + encerramento demanda) |

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
- [x] **E02 — Cadastro cliente refinado:** inputs with fundo `#F7F7F7`; ficha with morada, email, sexo, filhos (idade in anos + sexo), gravidez + DPP if applicable, contactos with emergência dinâmicos (**E.164** since **E16**), observações opcionais; migração SQLite + testes + CI in `tests/test_qa_auto.py`.
- [x] **E16 — NIF + telefone internacional:** `nif.py`, `telefone.py`, widgets; colunas `nif_ou_documento`, `identificacao_internacional`, `cliente_filhos.data_nascimento`; migração emergências; **56** `pytest`; dossier `2026-04-08_E16_cliente_nif_telefone_internacional` with `99_encerramento.md`.
- [x] **E02b — Hotfix Streamlit:** `SEXOS` centralizado in `src/modules/constants.py` (import estável for `app.py` / `cliente.py`, evita `ImportError` by ficheiro desatualizado or cache).
- [x] **E03 — Morada estruturada + filhos with nome:** campos de endereço for pesquisa (CP PT validado; freguesia obrigatória; distrito opcional); `cliente_filhos.nome`; base limpa without migração de legado in filhos.
- [x] **E04 — Colaboradores:** label **Gestão de Colaboradores**; cadastro with morada espelhada, idade ≥18, contacto exclusivo; `servicos` + seeds; `colaborador_servicos` with repasse 0,01%–100,00% (centésimos); UI with linhas incrementáveis e atalho for Catálogo; `src/modules/validators.py`; testes `tests/test_colaborador.py`.
- [x] **E05 — CI auditorias:** workflows `arquiteto_audit` / `analista_audit` with `fetch-depth: 0` e fallback when não existe `HEAD^` (evita exit 128).
- [x] **Painel 15 etapas — reconciliação:** `docs/PAINEL_OPERACIONAL.md` atualizado: etapas 04–15 marcadas conforme entregas reais; tabela de mapeamento E01–E04 ↔ plano; links de validação (incl. auditorias e `.cursorrules`).
- [x] **E06 — Fase 1 (incremental):** Colaboradores — remoção de linha de serviço (UUID), data de inserção da linha (obrigatória), edição de ficha (`atualizar_colaborador`, `obter_colaborador`); `media_repasse_percentual_servico()` for uso futuro in Pacotes (auto + editável). Catálogo — `src/modules/catalogo.py`: Sessão, Produto, Coworking; descritivo obrigatório; ativo/inativo; tabela de visualização in `src/app.py`; migrações in `connection.py`; testes `tests/test_catalogo.py` + extensão `tests/test_colaborador.py`.
- [x] **E06 — Fase 2 (Pacote):** Tabelas `servico_pacote_sessoes`, `servico_pacote_produtos`; colunas `pacote_*` in `servicos`; `cadastrar_pacote`, `repasse_medio_ponderado_pacote`; UI Pacote no catálogo (linhas 1:N, produto opcional, sugestão + campo editável de % referência, valor venda); `listar_servicos` exclui `Pacote`/`Evento` for habilitações; `PRAGMA foreign_keys=ON`; testes `test_pacote_ok_e_listagem`, `test_pacote_sessao_duplicada_rejeita`.
- [x] **E07 — Painel de Vendas:** tabelas `vendas`, `venda_itens`, `venda_pagamentos`, `venda_recebimentos_previstos`; `cliente` with pesquisa/atualização; `catalogo` with `listar_servicos_para_venda` + `resolver_snapshot_venda` (bónus ligado a `servico_id`); UI `src/ui/page_vendas.py`; testes `tests/test_venda.py`; decisões: split de meios; bónus sempre linha de serviço.
- [x] **E08 — Dashboards e Relatórios:** `src/modules/relatorios.py`; `src/ui/page_dashboards.py` (Plotly + paleta `ANALYTICS_COLORS`); filtros + Group by + Pareto/Top N + CSV; `venda_itens.colaborador_id` + UI; Fase A receita as proxy de lucro; testes `tests/test_relatorios.py`; módulo **#05**.
- [x] **E09 — Agendamentos:** tabelas `agendamentos`, `agendamento_colaboradores`; `src/modules/agendamento.py`; `src/ui/page_agendamentos.py` + botão no Início; buffer (pacote + avulso + coworking + evento); `devolver_ao_buffer` no cancelamento; `tests/test_agendamento.py`; **40** testes in `pytest`; módulo **#06** — **commit + push `develop`** na mesma entrega que sincroniza **E07 e E08** (antes só existiam no disco local).
- [x] **Governança — Evidência no GitHub:** **antes** da sincronização **E07–E09** in `develop`, o remoto **não continha** esses ficheiros (último commit visível: **`95f093d`** / E06). A Action **FLUXO OFICIAL DE GOVERNANCA** (`.github/workflows/fluxo_oficial_governanca.yml`) e o **Validador Maestro V2** reflectem o que está in `develop`; após **commit + push**, o histórico e a CI alinham with `PAINEL_OPERACIONAL` / `CONTROLE_DE_VOO`.
- [x] **Governança — Checkpoints Git by persona:** `docs/PAINEL_OPERACIONAL.md` passa a exigir **commit + push** in `develop` ao fim de cada bloco **Analista**, **Arquiteto**, **Dev** e **QA**, with regra de **reinício** if houver falha; `.cursorrules` alinhado. O painel reflecte evolução **local e remota** (`origin/develop`).
- [x] **Governança — Fluxo oficial de governança (ficheiro `FLUXO_SUCESSO_E_FALHA.md`):** processo completo, críticas/sugestões, exemplos de percurso **FALHA**; PC1–PC13 (Git→Painel); `docs/CADERNO_TESTES_MASTER.md`; `docs/governanca/status_demanda.json` + **Monitor de Voo** `monitor_governanca.py`; `.cursorrules` as norma suprema.
- [x] **Governança — Canal @Files e documentação automática:** entrada obrigatória da demanda via **Cursor `@Files` → Analista**; **EQUIPE** gera e mantém toda a documentação e painéis (without exigir ficheiros complementares do Diretor); `.cursorrules` e norma **`FLUXO_SUCESSO_E_FALHA.md`** (Fluxo oficial) actualizados.
- [x] **E06 — Fase 3 (Evento):** Colunas `evento_*` in `servicos`; tabela `servico_evento_participantes`; `cadastrar_evento`; UI Evento (data, local, observações, interno/convidado, preços criança/adulto/desconto filho adicional, participantes colaborador or parceiro with repasse % or €); listagem detalhada; testes `test_evento_ok_e_listagem`, `test_evento_sem_participantes_falha`, `test_evento_colaborador_duplicado_falha`.
- [x] **E11 — Pré-venda × Agenda (demanda `2026-04-06_E11_pre_venda_agenda`):** **Concluída** — código **`a6a9a8f`**, migração E11, UI, **49** `pytest`; pareceres **`06`–`09`**, **`99_encerramento.md`**; **Fluxo oficial** — percurso normal (SUCESSO) PC1–PC13 fechado (2026-04-06).
- [x] **CI — Workflow FLUXO OFICIAL DE GOVERNANCA:** substitui *Fabrica Zimmermann Governanca de 15 Etapas*; ficheiro `.github/workflows/fluxo_oficial_governanca.yml`; passos nomeados by fase A–F / PC; smoke `tests/test_governanca.py`; **Validador Maestro V2** mantém suite completa (2026-04-06).
- [x] **E12 — Refactoração Painel operacional (`2026-04-07_E12_refatoracao_painel_operacional`):** **Concluída** — `PAINEL_OPERACIONAL.md` tipo **Torre de Controle** + **Diário de Bordo** (topo executivo; PC1–PC13 in apêndices); `status_demanda.json` alargado; UI governança with grelha A–F (posteriormente **E15** → `monitor_governanca.py`); **49** `pytest` no fecho E12; `99_encerramento.md` (2026-04-07).
- [x] **E13 — Ajustes copy formulários (`2026-04-07_E13_ajustes_copy_formularios`):** **Concluída** — textos in **Clientes**, **Colaboradores** e **Catálogo** (`src/app.py`); mensagem alinhada in `catalogo.py`; **49** `pytest`; `99_encerramento.md` (2026-04-07).
- [x] **E14 — Telemetria ao vivo (`2026-04-07_E14_telemetria_live`):** **Concluída** — `live_status`, `etapas_pendentes`, `live_actualizado_iso` in `status_demanda.json`; **STATUS LIVE** + autorefresh na UI de governança (até **E15**); `streamlit-autorefresh` in `requirements.txt`; regra **6** in `.cursorrules`; **49** `pytest` no fecho E14; `99_encerramento.md` (2026-04-07).
- [x] **E15 — Monitor governança externo (`2026-04-07_E15_monitor_governanca_externo`):** **Concluída** — `monitor_governanca.py` na raiz; remoção de `page_fluxo_gestao.py` e entrada na app; PAINEL with dois acessos; **50** `pytest`; `99_encerramento.md` (2026-04-07).
- [x] **Hotfix Streamlit + sync Git (2026-04-08):** `src/app.py` — País (clientes/colaboradores) e Repasse % without conflito `value=` vs `session_state` após «Carregar for edição»; **commit + push `develop`**; backup D1 continua cópia integral de `data/beaba_gestao.db` (without alteração de percursos).
- [x] **Auditoria 360º + sync nuvem (2026-04-12):** Diff local (`workflows` backup, `monitor_governanca`, `seed_validacao_massiva`, `src/*` módulos core+UI, `tests/*`) fechado with **commit + push `origin/develop`**; mapa mestre de testes actualizado (**89** casos); **restore:** provas automatizadas + simulação semanal in sandbox; `status_demanda.json` / PAINEL / CADERNO alinhados — cumprimento protocolo Git→Painel (`.cursorrules`).
- [x] **Orientações Mestres Mandatórias (2026-04-19):** Implementação de persistência de expander e reposicionamento de mensagens no Setor 5 Entradas; suite de testes estendida para **269** casos; docstrings de backup/restore actualizadas; alinhamento local vs cloud concluído.
