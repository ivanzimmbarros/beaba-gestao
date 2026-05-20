# Wipe de ambiente de teste (DEV / STG)

Runbook para limpar dados operacionais de validação, preservando um único utilizador administrador, com snapshot prévio e sync cloud obrigatório nos deploys Streamlit.

## Quando usar

- Nova rodada de testes manuais «do zero» em DEV ou Staging.
- Pedido ao agente: *«Limpar ambiente STG»* / *«Wipe DEV cloud»* — indicar **ambiente** e **alvo**; **nunca** produção sem confirmação explícita separada.

## Pré-requisitos

- `.env` na raiz com credenciais R2/S3 e `BEABA_BACKUP_KEY`.
- Python do venv do projeto.
- Tokens de confirmação: `WIPE-DEV`, `WIPE-STG`, `WIPE-BATCH`.

## Comportamento

| Item | Detalhe |
|------|---------|
| Utilizador preservado | `ivanzimmbarros@gmail.com` — admin, ativo |
| Senha após wipe | `BeaBaTeste2026!` (`must_change_password=0`) |
| Catálogo vazio | `BEABA_SKIP_EXAMPLE_SEEDS=1` durante `create_tables()` |
| Snapshot local | `backups/pre_wipe/{dev\|stg}/{timestamp}_…/` + `manifest.json` |
| Snapshot cloud | `{dev\|stg}/pre_wipe/beaba_gestao_{timestamp}.beaba.enc` |
| Cloud pós-wipe | `backup_sqlite_hourly.py` + `backup_sync_cloud.py --force-all` |

## Comandos

```bash
# Um alvo
python scripts/wipe_ambiente_teste.py --ambiente dev --alvo local --confirm WIPE-DEV
python scripts/wipe_ambiente_teste.py --ambiente dev --alvo cloud --confirm WIPE-DEV
python scripts/wipe_ambiente_teste.py --ambiente stg --alvo cloud --confirm WIPE-STG

# Lote autorizado (dev local + dev cloud + stg cloud)
python scripts/wipe_ambiente_teste.py --run-authorized-batch --confirm WIPE-BATCH
```

## Isolamento de ambiente

O script define por execução:

| Ambiente | `ENV_TYPE` | `S3_UPLOAD_PREFIX` |
|----------|------------|-------------------|
| dev | `dev` | `dev/hourly/` |
| stg | `staging` | `stg/hourly/` |

Produção (`prod/hourly/`) **não** está exposta no CLI.

## URLs cloud

- DEV: https://dev-beabagestao.streamlit.app
- STG: https://testes-beabagestao.streamlit.app

Após wipe cloud, reiniciar a app (ou aguardar redeploy) para carregar a cópia enviada ao prefixo `hourly/`.

## Restauração em caso de falha

1. Local: copiar `backups/pre_wipe/.../beaba_gestao.db` para `data/beaba_gestao.db`.
2. Cloud: descarregar o objeto em `{env}/pre_wipe/…beaba.enc`, decriptar com `BEABA_BACKUP_KEY`, enviar de volta via `backup_sync_cloud --force-all` ou `restore_sqlite.py` conforme procedimento E17.

## Critérios de aceite pós-wipe

- `clientes`, `colaboradores`, `servicos`, `vendas`, `agendamentos` → **0**
- `usuarios` → **1** (e-mail preservado)
- `PRAGMA integrity_check` → `ok`
