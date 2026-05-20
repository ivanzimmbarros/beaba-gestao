# Épico 25 — Rodada de testes integrados (backlog vivo)

**ID:** `2026-05-20_E25_rodada_testes_integrados`  
**Status:** Em Aberto  
**Início:** 2026-05-20  

## Objectivo

Concentrar **todos os ajustes** descobertos durante a rodada de testes manuais em DEV (local + cloud) e STAGING (cloud), sem misturar com produção.

## Registo de entregas

| Data | Área | Resumo |
|------|------|--------|
| 2026-05-20 | Login / MFA / SMTP | Correção validação MFA (form Streamlit + ISO UTC); TTL 1 min; reenviar código; reset senha + link `?bea_recuperar=1`; mensagens «Código expirado.» / senha temporária expirada |
| 2026-05-20 | Cloud DEV | **web_startup:** não restaurar R2 quando `usuarios` activos (pós-wipe); evita apagar MFA no rerun. Sync imediato após `issue_mfa_token`. **Deploy:** push `develop`/`main` obrigatório — alterações anteriores só estavam locais. |

## Fila (a preencher nos testes)

- [ ] Demais páginas e fluxos — a informar pelo Diretor

## Referências

- `docs/governanca/demandas/2026-05-20_E25_rodada_testes_integrados/01_demanda_diretor.md`
- `docs/governanca/WIPE_AMBIENTE_TESTE.md` (limpeza de ambientes)
- `src/ui/page_auth.py`, `src/modules/auth_db.py`
