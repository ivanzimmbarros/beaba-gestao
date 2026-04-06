# Caderno mestre de testes — BeaBa Gestão

**Normativo:** o **Dev** (passo **18** do fluxo [`governanca/FLUXO_SUCESSO_E_FALHA.md`](governanca/FLUXO_SUCESSO_E_FALHA.md)) **actualiza** este documento com o **plano de testes** de cada demanda. O **QA** valida, incrementa se necessário, e executa testes massivos (automáticos + manuais acordados).

## 1. Testes automatizados (regressão obrigatória)

| Âmbito | Comando | Notas |
|:---|:---|:---|
| Suite completa | `python -m pytest tests/ -v` | Deve passar antes de **selo QA** e push em `develop`. |

## 2. Por módulo (referência rápida)

- `tests/test_qa_auto.py` — clientes, validações
- `tests/test_colaborador.py` — colaboradores
- `tests/test_catalogo.py` — catálogo, pacotes, eventos
- `tests/test_venda.py` — vendas
- `tests/test_relatorios.py` — relatórios / dashboards
- `tests/test_agendamento.py` — agendamentos

## 3. Plano por demanda (template)

Para cada **ID de demanda**, acrescentar secção:

```markdown
### Demanda <ID> — <título>

- **Objectivo:** …
- **Novos casos:** …
- **Regressão:** pytest completo + smoke Streamlit: …
- **Critérios de aceite:** …
```

## 4. Histórico

- **2026-04-06:** Documento criado para cumprir passo 18 do fluxo SUCESSO (plano de testes mestre).
