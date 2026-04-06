# Painel operacional — Fluxo de 15 Etapas

**Processo padrão de entrega:** *Fluxo de 15 Etapas* (governança em `.cursorrules`).  
**Instrução:** este ficheiro deve ser atualizado **antes** de iniciar alterações de código (intenção / etapas tocadas) e **depois** de as concluir (estado, links de validação e notas).

**Última revisão do painel:** *(atualizar a cada entrega)*

---

## Tabela das 15 etapas

| # | Etapa | Documentos / testes de validação (links) | Estado |
|:---:|:---|:---|:---:|
| 01 | Requisito alinhado ao negócio | [`CONTROLE_DE_VOO.md`](../CONTROLE_DE_VOO.md), [`CADERNO_MESTRE.md`](CADERNO_MESTRE.md) | ⚪ |
| 02 | Proposta / escopo fechado (Analista) | [`CONTROLE_DE_VOO.md`](../CONTROLE_DE_VOO.md) | ⚪ |
| 03 | Estrutura e dados (Arquiteto) | [`MODELO_ARQUITETURA.md`](MODELO_ARQUITETURA.md), `src/`, `docs/` | ⚪ |
| 04 | Implementação (Dev) | `src/`, `app.py` | ⚪ |
| 05 | Tema / UI (se aplicável) | [`CADERNO_MESTRE.md`](CADERNO_MESTRE.md), `src/ui/` | ⚪ |
| 06 | Persistência / migrações | `src/database/connection.py` | ⚪ |
| 07 | Regras de domínio | `src/modules/` | ⚪ |
| 08 | Testes automáticos | [`tests/test_qa_auto.py`](../tests/test_qa_auto.py) | ⚪ |
| 09 | CI / workflow | [`.github/workflows/qa_automatico.yml`](../.github/workflows/qa_automatico.yml) | ⚪ |
| 10 | `pytest` local | `python -m pytest tests/test_qa_auto.py -v` | ⚪ |
| 11 | Atualização documentação técnica | `docs/` (Caderno, Modelo, este painel) | ⚪ |
| 12 | Atualização painel de voo | [`CONTROLE_DE_VOO.md`](../CONTROLE_DE_VOO.md) | ⚪ |
| 13 | Revisão de links desta tabela (Analista) | *esta tabela* | ⚪ |
| 14 | Validação visual do painel (QA) | *este ficheiro aberto e coerente com o commit* | ⚪ |
| 15 | Commit final + push `develop` | Git — apenas após etapa 14 | ⚪ |

**Legenda sugerida:** ⚪ Pendente · 🔵 Em curso · 🟢 Concluído

---

## Registo da última entrega

*(Preencher após cada ciclo: resumo, hash do commit, notas.)*

- **Entrega:** —
- **Commit:** —
- **Notas:** —
