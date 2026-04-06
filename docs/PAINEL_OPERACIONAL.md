# Painel operacional — Fluxo de 15 Etapas

**Processo padrão de entrega:** *Fluxo de 15 Etapas* (governança em `.cursorrules`).  
**Instrução:** este ficheiro deve ser atualizado **antes** de iniciar alterações de código (intenção / etapas tocadas) e **depois** de as concluir (estado, links de validação e notas).

**Última revisão do painel:** 2026-04-06 — ETAPA 01 (Painel) aplicada.

---

## Tabela das 15 etapas

| # | Etapa | Link de Validação | Estado |
|:---:|:---|:---|:---:|
| 01 | Configuração | [`CADERNO_MESTRE.md`](CADERNO_MESTRE.md) · [`app.py`](../app.py) | ✅ |
| 02 | Cadastro de Clientes | [`CADERNO_MESTRE.md`](CADERNO_MESTRE.md) · [`src/app.py`](../src/app.py) · [`src/modules/cliente.py`](../src/modules/cliente.py) · [`tests/test_qa_auto.py`](../tests/test_qa_auto.py) | 🚧 |
| 03 | Proposta / escopo (Analista) | [`CONTROLE_DE_VOO.md`](../CONTROLE_DE_VOO.md) | ⚪ |
| 04 | Estrutura e dados (Arquiteto) | [`MODELO_ARQUITETURA.md`](MODELO_ARQUITETURA.md) · `src/` · `docs/` | ⚪ |
| 05 | Tema / UI V11 | [`CADERNO_MESTRE.md`](CADERNO_MESTRE.md) · `src/ui/` | ⚪ |
| 06 | Persistência / migrações | [`src/database/connection.py`](../src/database/connection.py) | ⚪ |
| 07 | Regras de domínio | `src/modules/` | ⚪ |
| 08 | Testes automáticos | [`tests/test_qa_auto.py`](../tests/test_qa_auto.py) | ⚪ |
| 09 | CI / workflow | [`.github/workflows/qa_automatico.yml`](../.github/workflows/qa_automatico.yml) | ⚪ |
| 10 | `pytest` local | comando: `python -m pytest tests/test_qa_auto.py -v` | ⚪ |
| 11 | Documentação técnica | `docs/` (Caderno, Modelo, este painel) | ⚪ |
| 12 | Painel de voo | [`CONTROLE_DE_VOO.md`](../CONTROLE_DE_VOO.md) | ⚪ |
| 13 | Revisão de links desta tabela (Analista) | *esta tabela* | ⚪ |
| 14 | Validação visual do painel (QA) | *este ficheiro coerente com o commit* | ⚪ |
| 15 | Commit final + push `develop` | Git — após etapa 14 | ⚪ |

**Legenda:** ✅ Concluído · 🚧 Em andamento · ⚪ Pendente

---

## Registo da última entrega

- **Entrega:** ETAPA 01 — Painel operacional (tabela 15 etapas; Configuração ✅; Cadastro de Clientes 🚧).
- **Commit:** ver último commit em `develop` com mensagem contendo `docs(painel): ETAPA 01`
- **Notas:** Ficheiro em `/docs` conforme arquitetura de pastas.
