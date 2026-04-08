# 04 — Desenho lógico — E17 Backup e DR (SQLite)

**Demanda:** `2026-04-08_E17_backup_dr` · **2026-04-08**

## 1. Componentes

| Componente | Responsabilidade |
|:---|:---|
| [`scripts/backup_sqlite_hourly.py`](../../../../scripts/backup_sqlite_hourly.py) | Conexão RO à origem (`file:…?mode=ro`), `backup()` para `backups/hourly/beaba_gestao_UTC_%Y%m%d_%H%M%S_%f.db`, `PRAGMA quick_check`, rotação, cópia opcional para `backups/cloud_queue/`. |
| [`scripts/verify_restore_weekly.py`](../../../../scripts/verify_restore_weekly.py) | Último ficheiro horário por `st_mtime`; `shutil.copy2` → `backups/restore_verify/staging_*.db`; `integrity_check` + `foreign_key_check`; apaga staging. |
| [`src/database/connection.py`](../../../../src/database/connection.py) | `PRAGMA journal_mode=WAL` após `foreign_keys=ON` (melhor concorrência e backup online). |
| `.gitignore` | `backups/logs/*.log` — logs não versionados; `*.db` cobre réplicas. |

## 2. Variáveis de ambiente

| Variável | Efeito |
|:---|:---|
| `BEABA_REPO_ROOT` | Raiz do projecto (dados em `data/beaba_gestao.db`, árvore `backups/`). |
| `BEABA_BACKUP_KEEP` | Máximo de ficheiros em `backups/hourly` (defeito **168**). |
| `BEABA_BACKUP_CLOUD_QUEUE` | `0` / `false` / `no` desliga cópia para `backups/cloud_queue/`. |

## 3. Códigos de saída

- **0** — sucesso.
- **1** — fonte em falta, falha de API/quick_check, sem backups para verificar, `integrity_check` ≠ `ok`, ou violações em `foreign_key_check`.

## 4. Testes automatizados

`tests/test_e17_backup_dr.py` — subprocess com `BEABA_REPO_ROOT` apontando para árvore temporária; compilação dos scripts; rotação com `BEABA_BACKUP_KEEP=2`; corrupção binária → verificação semanal falha.
