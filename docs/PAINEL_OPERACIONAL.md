# Painel operacional — Fluxo de 15 Etapas

**Processo padrão de entrega:** *Fluxo de 15 Etapas* (governança em `.cursorrules`).  
**Instrução:** este ficheiro deve ser atualizado **antes** de iniciar alterações de código (intenção / etapas tocadas) e **depois** de as concluir (estado, links de validação e notas).

**Última revisão do painel:** 2026-04-06 — pré-código: módulo Colaboradores + serviços seed. **Pós-código:** entrega E04 fechada (tabela e links revistos).

---

## Tabela das 15 etapas

| # | Etapa | Link de Validação | Estado |
|:---:|:---|:---|:---:|
| 01 | Configuração | [`CADERNO_MESTRE.md`](CADERNO_MESTRE.md) · [`app.py`](../app.py) | ✅ |
| 02 | Cadastro de Clientes | [`CADERNO_MESTRE.md`](CADERNO_MESTRE.md) · [`src/app.py`](../src/app.py) · [`src/modules/cliente.py`](../src/modules/cliente.py) · [`tests/test_qa_auto.py`](../tests/test_qa_auto.py) | ✅ |
| 03 | Colaboradores + habilitações | [`CADERNO_MESTRE.md`](CADERNO_MESTRE.md) · [`src/app.py`](../src/app.py) · [`src/modules/colaborador.py`](../src/modules/colaborador.py) · [`src/database/connection.py`](../src/database/connection.py) · [`tests/test_colaborador.py`](../tests/test_colaborador.py) | ✅ |
| 04 | Proposta / escopo (Analista) | [`CONTROLE_DE_VOO.md`](../CONTROLE_DE_VOO.md) | ⚪ |
| 05 | Estrutura e dados (Arquiteto) | [`MODELO_ARQUITETURA.md`](MODELO_ARQUITETURA.md) · `src/` · `docs/` | ⚪ |
| 06 | Tema / UI V11 | [`CADERNO_MESTRE.md`](CADERNO_MESTRE.md) · `src/ui/` | ⚪ |
| 07 | Persistência / migrações | [`src/database/connection.py`](../src/database/connection.py) | ⚪ |
| 08 | Regras de domínio | `src/modules/` · [`validators`](../src/modules/validators.py) | ⚪ |
| 09 | Testes automáticos | [`tests/`](../tests/) | ⚪ |
| 10 | CI / workflow | [`.github/workflows/qa_automatico.yml`](../.github/workflows/qa_automatico.yml) | ⚪ |
| 11 | `pytest` local | `python -m pytest tests/ -v` | ⚪ |
| 12 | Documentação técnica | `docs/` · [`CONTROLE_DE_VOO.md`](../CONTROLE_DE_VOO.md) | ⚪ |
| 13 | Revisão de links desta tabela (Analista) | *esta tabela* | ⚪ |
| 14 | Validação visual do painel (QA) | *este ficheiro coerente com o commit* | ⚪ |
| 15 | Commit final + push `develop` | Git — após etapa 14 | ⚪ |

**Legenda:** ✅ Concluído · 🚧 Em andamento · ⚪ Pendente

---

## Registo da última entrega

- **Entrega:** E04 — Módulo **Colaboradores** (UI, BD `servicos`/`colaboradores`/`colaborador_servicos`, seeds, validadores partilhados, testes, CI `tests/`).
- **Commit:** `0303aa1`
- **Notas:** Contacto exclusivo; repasse % com 2 dec (1–10000); idade ≥18; ≥1 serviço; atalho para ecrã Catálogo (placeholder).
