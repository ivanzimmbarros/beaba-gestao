# 01 — Demanda do Diretor (fonte: Cursor `@Files` → Analista / EQUIPE)

**ID da demanda:** `2026-04-07_E15_monitor_governanca_externo`  
**Data de registo pela EQUIPE:** 2026-04-07  
**Canal:** **`@Files`**, **Analista**, **EQUIPE**.

---

## Síntese do pedido

O **Diretor** exige que o acompanhamento da **governança** e da **telemetria E14** deixe de estar integrado na **aplicação principal de gestão** (Streamlit em `src/app.py`). O objectivo é um **monitor stand-alone**, pensado para **segundo ecrã**: telemetria **independente**, só focada em fluxo, torre e diário.

**Tarefas previstas (após aprovação do desenho funcional):**

1. Criar **`monitor_governanca.py` na raiz** do repositório (fora de `src/`).
2. **Migrar** para esse ficheiro toda a lógica actual de **STATUS LIVE**, **Torre de Controle** e **Diário de Bordo** (hoje em [`src/ui/page_fluxo_gestao.py`](../../../../src/ui/page_fluxo_gestao.py)), lendo **`docs/governanca/status_demanda.json`**.
3. **Remover** da app principal a entrada **«Fluxo e governança»** e o ramo `fluxo_gestao` (import, botão no Início, `elif`).
4. No monitor: **`layout="wide"`**, **`streamlit-autorefresh` obrigatório** (monitorização contínua).
5. **Actualizar** [`PAINEL_OPERACIONAL.md`](../../../PAINEL_OPERACIONAL.md) com **dois pontos de acesso**: App de Gestão vs Monitor de Voo.

---

## Restrição (Fase A)

Seguir o **Fluxo oficial — percurso normal (SUCESSO)**. **Nesta fase só** se produz **`01`** e **`02_desenho_funcional.md`** (interface e plano de migração). **Sem** criar `monitor_governanca.py`, **sem** alterar `app.py` / `page_fluxo_gestao.py` / JSON até **CONFIRMO** / **PROSSIGA** formal no chat.

---

## Próximo passo

- **`02_desenho_funcional.md`** — desenho da interface do monitor externo e mapa técnico da migração.  
- Depois: **`03`**, PCs, implementação, `pytest`, encerramento.
