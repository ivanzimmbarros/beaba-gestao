# 🚀 PAINEL DE CONTROLE DE VOO - BEABA GESTÃO (V11.0 / V8.1)

**PROJETO:** Centro Terapêutico BeaBa Materno  
**DESENHO FUNCIONAL:** V11.0 — Identidade integrada (ver `docs/CADERNO_MESTRE.md`)  
**STATUS ATUAL:** 🔵 DESENVOLVIMENTO EM CURSO (#01)  
**CONTADOR DE INTEGRIDADE MASSIVA (N+1):** [ 0 ] Funcionalidades Validadas

---

## 📦 MÓDULO 01: GESTÃO CORE (CLIENTES, COLABORADORAS, CATÁLOGO)

| ID | FUNCIONALIDADE | ANALISTA | ARQUITETO | DEV | QA (REGRESSÃO) | STATUS FINAL |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| #01 | Cadastro de Clientes (contacto 11 + ficha alargada) | 🟢 | 🟢 | 🔵 | 🟢 | EM CURSO |
| #02 | Cadastro de Colaboradoras (% Repasse) | ⚪ | ⚪ | ⚪ | ⚪ | AGUARDANDO |
| #03 | Catálogo Híbrido (4 Naturezas) | ⚪ | ⚪ | ⚪ | ⚪ | AGUARDANDO |
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
