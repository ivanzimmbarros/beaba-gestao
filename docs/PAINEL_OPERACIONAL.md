# Painel operacional — Fluxo de 15 Etapas

**Processo padrão de entrega:** *Fluxo de 15 Etapas* (governança em [`.cursorrules`](../.cursorrules)).

**Instrução:** atualizar **antes** de alterações de código (intenção) e **depois** (estado, links, registo).

**Última revisão do painel:** 2026-04-06 — **sincronização total** com entregas E01–E04, governança, CI e auditorias; revisão de links (etapa 13) e coerência com o repositório.

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

Todas as entregas acima seguiram o *Fluxo de 15 Etapas* com **pytest** (`tests/`) e **push em `develop`**.

---

## Tabela das 15 etapas

| # | Etapa | Link de Validação | Estado |
|:---:|:---|:---|:---:|
| 01 | Configuração | [`.cursorrules`](../.cursorrules) · [`CADERNO_MESTRE.md`](CADERNO_MESTRE.md) · [`app.py`](../app.py) | ✅ |
| 02 | Cadastro de Clientes | [`CADERNO_MESTRE.md`](CADERNO_MESTRE.md) · [`src/app.py`](../src/app.py) · [`src/modules/cliente.py`](../src/modules/cliente.py) · [`tests/test_qa_auto.py`](../tests/test_qa_auto.py) | ✅ |
| 03 | Colaboradores + habilitações | [`CADERNO_MESTRE.md`](CADERNO_MESTRE.md) · [`src/app.py`](../src/app.py) · [`src/modules/colaborador.py`](../src/modules/colaborador.py) · [`src/database/connection.py`](../src/database/connection.py) · [`tests/test_colaborador.py`](../tests/test_colaborador.py) | ✅ |
| 04 | Proposta / escopo (Analista) | [`CONTROLE_DE_VOO.md`](../CONTROLE_DE_VOO.md) (módulos + Log de Progresso) | ✅ |
| 05 | Estrutura e dados (Arquiteto) | [`MODELO_ARQUITETURA.md`](MODELO_ARQUITETURA.md) · [`src/`](../src/) · [`docs/`](.) | ✅ |
| 06 | Tema / UI V11 | [`CADERNO_MESTRE.md`](CADERNO_MESTRE.md) · [`src/ui/theme.py`](../src/ui/theme.py) | ✅ |
| 07 | Persistência / migrações | [`src/database/connection.py`](../src/database/connection.py) | ✅ |
| 08 | Regras de domínio | [`src/modules/`](../src/modules/) · [`validators.py`](../src/modules/validators.py) | ✅ |
| 09 | Testes automáticos | [`tests/`](../tests/) | ✅ |
| 10 | CI / workflows | [`qa_automatico.yml`](../.github/workflows/qa_automatico.yml) · [`arquiteto_audit.yml`](../.github/workflows/arquiteto_audit.yml) · [`analista_audit.yml`](../.github/workflows/analista_audit.yml) | ✅ |
| 11 | `pytest` local | `python -m pytest tests/ -v` (obrigatório antes de push) | ✅ |
| 12 | Documentação técnica | [`docs/`](.) · [`CONTROLE_DE_VOO.md`](../CONTROLE_DE_VOO.md) · [`PAINEL_OPERACIONAL.md`](PAINEL_OPERACIONAL.md) | ✅ |
| 13 | Revisão de links desta tabela (Analista) | *esta tabela — atualizada nesta revisão* | ✅ |
| 14 | Validação visual do painel (QA) | *ficheiro + estados ✅ alinhados ao Git; smoke Streamlit recomendado ao Diretor* | ✅ |
| 15 | Commit final + push `develop` | Git — ciclo fechado após etapas 11–14 | ✅ |

**Legenda:** ✅ Concluído · 🚧 Em andamento · ⚪ Pendente

**Próximo foco de produto (fora do fecho deste ciclo):** módulos **#03 Catálogo** e **#04 Vendas** no `CONTROLE_DE_VOO.md` — ao iniciar, reabrir etapas pertinentes como 🚧 no painel.

---

## Registo da última entrega

- **Entrega:** Sincronização **Painel Operacional** com o *Fluxo de 15 Etapas* + registo da correção CI das auditorias (`fetch-depth: 0`, fallback `HEAD^`).
- **Commits de referência:** `ac69975` (sincronização 15 etapas + CONTROLE); `185103e` (CI auditorias); `0303aa1` / `e326556` (E04).
- **Notas:** As etapas 04–15 estavam em ⚪ apesar de já cumpridas nas entregas anteriores; esta revisão corrige o desvio face ao `.cursorrules`.
