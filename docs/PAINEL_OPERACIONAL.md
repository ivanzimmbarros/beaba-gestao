# Painel operacional — Fluxo de 15 Etapas

**Processo padrão de entrega:** *Fluxo de 15 Etapas* (governança em [`.cursorrules`](../.cursorrules)).

**Instrução:** atualizar **antes** de alterações de código (intenção) e **depois** (estado, links, registo).

**Última revisão do painel:** 2026-04-06 — **E06 fechado (Fases 1–3):** Catálogo completo com **Evento** (`servico_evento_participantes`, `cadastrar_evento`, UI); **28** testes `pytest`.

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
| 14 | Validação visual (QA) | 🚧 | Smoke Streamlit: Colaboradores (novo + editar + linhas) + Catálogo — recomendado ao Diretor |
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
| **Governança — Painel + `.cursorrules`** | 01 (extensão), 11–12, 13–15 |
| **E04 — Colaboradores** | 03 Colaboradores + serviços seed, 05 MODELO, 07–10, 12 |
| **CI — Auditorias (`HEAD^`)** | 10 workflows `arquiteto_audit` / `analista_audit` |
| **E06 — Fases 1–3 (catálogo híbrido)** | 03–12 + 13 documental; 14–15 por entrega |

Todas as entregas acima seguiram o *Fluxo de 15 Etapas* com **pytest** (`tests/`) e **push em `develop`**.

---

## Tabela das 15 etapas

| # | Etapa | Link de Validação | Estado |
|:---:|:---|:---|:---:|
| 01 | Configuração | [`.cursorrules`](../.cursorrules) · [`CADERNO_MESTRE.md`](CADERNO_MESTRE.md) · [`app.py`](../app.py) | ✅ |
| 02 | Cadastro de Clientes | [`CADERNO_MESTRE.md`](CADERNO_MESTRE.md) · [`src/app.py`](../src/app.py) · [`src/modules/cliente.py`](../src/modules/cliente.py) · [`tests/test_qa_auto.py`](../tests/test_qa_auto.py) | ✅ |
| 03 | Colaboradores + habilitações | [`CADERNO_MESTRE.md`](CADERNO_MESTRE.md) · [`src/app.py`](../src/app.py) · [`src/modules/colaborador.py`](../src/modules/colaborador.py) · [`src/database/connection.py`](../src/database/connection.py) · [`tests/test_colaborador.py`](../tests/test_colaborador.py) | ✅ |
| 04 | Proposta / escopo (Analista) | [`CONTROLE_DE_VOO.md`](../CONTROLE_DE_VOO.md) (módulos + Log de Progresso) | ✅ |
| 05 | Estrutura e dados (Arquiteto) | [`MODELO_ARQUITETURA.md`](MODELO_ARQUITETURA.md) · [`src/modules/catalogo.py`](../src/modules/catalogo.py) · [`docs/`](.) | ✅ |
| 06 | Tema / UI V11 | [`CADERNO_MESTRE.md`](CADERNO_MESTRE.md) · [`src/ui/theme.py`](../src/ui/theme.py) · [`src/app.py`](../src/app.py) (Catálogo + Colaboradores) | ✅ |
| 07 | Persistência / migrações | [`src/database/connection.py`](../src/database/connection.py) | ✅ |
| 08 | Regras de domínio | [`src/modules/colaborador.py`](../src/modules/colaborador.py) · [`src/modules/catalogo.py`](../src/modules/catalogo.py) · [`src/modules/validators.py`](../src/modules/validators.py) | ✅ |
| 09 | Testes automáticos | [`tests/`](../tests/) | ✅ |
| 10 | CI / workflows | [`qa_automatico.yml`](../.github/workflows/qa_automatico.yml) · [`arquiteto_audit.yml`](../.github/workflows/arquiteto_audit.yml) · [`analista_audit.yml`](../.github/workflows/analista_audit.yml) | ✅ |
| 11 | `pytest` local | `python -m pytest tests/ -v` (obrigatório antes de push) | ✅ |
| 12 | Documentação técnica | [`docs/`](.) · [`CONTROLE_DE_VOO.md`](../CONTROLE_DE_VOO.md) · [`PAINEL_OPERACIONAL.md`](PAINEL_OPERACIONAL.md) | ✅ |
| 13 | Revisão de links desta tabela (Analista) | *esta tabela — E06 Fase 3* | ✅ |
| 14 | Validação visual do painel (QA) | *smoke Streamlit Colaboradores + Catálogo* | 🚧 |
| 15 | Commit final + push `develop` | Git — ciclo E06 Fase 3 | ✅ |

**Legenda:** ✅ Concluído · 🚧 Em andamento · ⚪ Pendente

**Próximo foco de produto:** módulo **#04 Vendas** / gatilhos financeiros no `CONTROLE_DE_VOO.md` (após validação QA do catálogo completo).

---

## Registo da última entrega

- **Entrega:** **E06 Fase 3 — Evento** — colunas `evento_*` em `servicos`; `servico_evento_participantes`; `cadastrar_evento`, `_detalhe_evento`; UI `NATUREZAS_CATALOGO_FASE3` em `src/app.py`; testes `test_evento_*`; **28** testes no total.
- **Referência técnica:** `CONTROLE_DE_VOO.md` (Log), `MODELO_ARQUITETURA.md`, `CADERNO_MESTRE.md` (regra 4).
- **Notas:** Evento: ≥1 participante; não repetir o mesmo colaborador em duas linhas; parceiro exige nome. Pacote: ver nota anterior (sessão duplicada).
