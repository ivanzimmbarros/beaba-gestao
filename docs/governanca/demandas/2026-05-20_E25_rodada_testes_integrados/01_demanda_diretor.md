# Demanda — Rodada de testes integrados (Épico 25)

**Fonte:** Diretor via Cursor, 2026-05-20  
**Ambientes:** DEV (local + https://dev-beabagestao.streamlit.app), STG (https://testes-beabagestao.streamlit.app). Produção fora de âmbito.

## TELA DE LOGIN — erros reportados

1. **MFA:** código recebido por e-mail, mas validação devolvia «Código incorreto ou expirado.» (DEV e STG cloud).
2. **Reset senha:** e-mail com senha temporária recebido, mas login com «E-mail ou senha incorretos.» antes do ecrã de troca obrigatória.

## Melhorias solicitadas

1. Botão **Reenviar código** (invalidar código anterior).
2. **Link** no e-mail de reset para fluxo de troca de senha (`?bea_recuperar=1`).
3. **Validade máxima 1 minuto** para MFA e senha temporária; e-mails e UI devem indicar claramente; erro explícito **«Código expirado.»** quando aplicável.

## Primeira entrega (implementação)

Ver `00_indice.md` e commits associados a `page_auth`, `auth_db`, `email_utils`, `auth_public_url`.
