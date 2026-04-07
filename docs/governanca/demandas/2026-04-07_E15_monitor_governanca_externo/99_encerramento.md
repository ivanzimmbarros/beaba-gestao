# 99 — Encerramento — E15 Monitor de governança externo

**Demanda:** `2026-04-07_E15_monitor_governanca_externo`  
**Data de encerramento:** 2026-04-07  
**Percurso:** normal (SUCESSO).

---

## Entregas

- [`monitor_governanca.py`](../../../../monitor_governanca.py) (raiz): STATUS LIVE, Torre A–F, métricas (4 colunas), Diário, pendente, expanders, JSON; `layout="wide"`; `streamlit-autorefresh` sempre activo (10 s); leitura de `docs/governanca/status_demanda.json`.
- Removidos: [`src/ui/page_fluxo_gestao.py`](../../../../src/ui/page_fluxo_gestao.py); entrada **Fluxo e governança** e ramo `fluxo_gestao` em [`src/app.py`](../../../../src/app.py).
- [`docs/PAINEL_OPERACIONAL.md`](../../../PAINEL_OPERACIONAL.md): secção **Dois pontos de acesso**; referências actualizadas ao Monitor de Voo.
- [`.cursorrules`](../../../../.cursorrules), [`FLUXO_SUCESSO_E_FALHA.md`](../../FLUXO_SUCESSO_E_FALHA.md), [`CONTROLE_DE_VOO.md`](../../../../CONTROLE_DE_VOO.md), [`CADERNO_TESTES_MASTER.md`](../../../CADERNO_TESTES_MASTER.md): alinhamento com o monitor stand-alone.
- Teste `test_monitor_governanca_script_existe_e_compila` em [`tests/test_governanca.py`](../../../../tests/test_governanca.py).

---

## Comandos

- App de gestão: `streamlit run app.py`
- Monitor de Voo: `streamlit run monitor_governanca.py`
