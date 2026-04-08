# 99 — Encerramento

**Demanda:** `2026-04-08_E17_backup_dr` · **2026-04-08**

## Entregas (produto / operação)

- **Hot-backup horário:** `scripts/backup_sqlite_hourly.py` + `scripts/backup_hourly.cmd` (Task Scheduler Windows).
- **Verificação semanal:** `scripts/verify_restore_weekly.py` + `scripts/verify_restore_weekly.cmd` — `integrity_check` + `foreign_key_check` em staging; **não** altera `data/beaba_gestao.db`.
- **Estrutura:** `backups/hourly`, `weekly`, `restore_verify`, `logs`, `cloud_queue` com `.gitkeep`; `.gitignore` para `backups/logs/*.log`.
- **App:** `PRAGMA journal_mode=WAL` na conexão SQLite em `connection.py`.
- **Documentação:** `PAINEL_OPERACIONAL.md` (secção Backup/DR); [`04_desenho_logico.md`](04_desenho_logico.md); [`02_desenho_funcional.md`](02_desenho_funcional.md) critérios marcados.

## Restauro manual (produção)

1. Parar a app Streamlit.  
2. Substituir `data/beaba_gestao.db` por cópia validada (ex.: último ficheiro de `backups/hourly` ou cópia da nuvem).  
3. Remover `-wal`/`-shm` órfãos se existirem, se a cópia for modo DELETE e o ambiente o exigir.  
4. Arrancar a app e validar smoke.

## Governança

Percurso **SUCESSO** até **PC13** (implementação + Painel + JSON + push `develop`). Próximo pedido: **`@Files` → Analista**.
