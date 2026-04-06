# Caderno mestre de testes — BeaBa Gestão

**Normativo:** a **EQUIPE** (persona Dev no passo **18** do fluxo [`governanca/FLUXO_SUCESSO_E_FALHA.md`](governanca/FLUXO_SUCESSO_E_FALHA.md)) **actualiza** este documento com o **plano de testes** de cada demanda. O **QA** (EQUIPE) valida, incrementa se necessário, e executa testes massivos. O Diretor **não** edita este ficheiro manualmente.

## 1. Testes automatizados (regressão obrigatória)

| Âmbito | Comando | Notas |
|:---|:---|:---|
| Suite completa | `python -m pytest tests/ -v` | Deve passar antes de **selo QA** e push em `develop`. |

## 2. Por módulo (referência rápida)

- `tests/test_qa_auto.py` — clientes, validações
- `tests/test_colaborador.py` — colaboradores
- `tests/test_catalogo.py` — catálogo, pacotes, eventos
- `tests/test_venda.py` — vendas (incl. `agendamento_contexto_id` / cliente ≠ agendamento)
- `tests/test_relatorios.py` — relatórios / dashboards
- `tests/test_agendamento.py` — agendamentos (incl. E11 pré-venda, migração `modo_origem`, associação a `venda_item`)

## 3. Plano por demanda (template)

Para cada **ID de demanda**, acrescentar secção:

```markdown
### Demanda <ID> — <título>

- **Objectivo:** …
- **Novos casos:** …
- **Regressão:** pytest completo + smoke Streamlit: …
- **Critérios de aceite:** …
```

### Demanda `2026-04-06_E11_pre_venda_agenda` — pré-venda na agenda

- **Objectivo:** `modo_origem` / `pre_venda`, `associar_agendamento_pre_venda_a_item`, `registrar_venda` + `agendamento_contexto_id`, UI Agendamentos + Vendas.
- **Novos casos:** `test_schema_agendamentos_tem_modo_origem`, `test_pre_venda_sessao_concluir_bloqueado`, `test_pre_venda_associar_apos_venda`, `test_pre_venda_pacote_natureza_rejeita`, `test_cancelar_pre_venda`, `test_registrar_venda_contexto_agendamento_cliente_diferente_falha`.
- **Regressão:** `python -m pytest tests/ -v` (suite **49** testes após E11).
- **Critérios de aceite:** alinhados ao [`04_desenho_logico.md`](governanca/demandas/2026-04-06_E11_pre_venda_agenda/04_desenho_logico.md) §8.

## 4. Histórico

- **2026-04-06:** Documento criado para cumprir passo 18 do fluxo SUCESSO (plano de testes mestre).
- **2026-04-06:** Plano E11 (pré-venda) acrescentado; suite pytest **49** testes.
