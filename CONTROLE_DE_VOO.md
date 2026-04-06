# 🚀 PAINEL DE CONTROLE DE VOO - BEABA GESTÃO (V11.0 / V8.1)

**PROJETO:** Centro Terapêutico BeaBa Materno  
**DESENHO FUNCIONAL:** V11.0 — Identidade integrada (ver `docs/CADERNO_MESTRE.md`)  
**STATUS ATUAL:** 🔵 DESENVOLVIMENTO EM CURSO (#01)  
**CONTADOR DE INTEGRIDADE MASSIVA (N+1):** [ 0 ] Funcionalidades Validadas

---

## 📦 MÓDULO 01: GESTÃO CORE (CLIENTES, COLABORADORES, CATÁLOGO)

| ID | FUNCIONALIDADE | ANALISTA | ARQUITETO | DEV | QA (REGRESSÃO) | STATUS FINAL |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| #01 | Cadastro de Clientes (contacto 11 + ficha alargada) | 🟢 | 🟢 | 🔵 | 🟢 | EM CURSO |
| #02 | Cadastro de Colaboradores (habilitações + % repasse + edição + data linha) | 🟢 | 🟢 | 🟢 | 🟢 | EM CURSO |
| #03 | Catálogo Híbrido (4 Naturezas) | 🟢 | 🟢 | 🔵 | 🟢 | Fase 2 OK (Pacote) — Evento Fase 3 |
| #04 | Gatilho de Exceção Financeira | ⚪ | ⚪ | ⚪ | ⚪ | AGUARDANDO |

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
