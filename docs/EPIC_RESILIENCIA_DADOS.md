# Épico: Resiliência de Dados e Preparação para Produção (Backup & Restore)

**Público:** gestão e operação (linguagem de negócios)  
**Estado:** **Concluído** (Fases 1–3)  
**Última actualização:** 2026-05-16

---

## O conceito — duas coisas que nunca se misturam

| O quê | Onde vive | O que contém |
|--------|-----------|--------------|
| **Estrutura** | Código nas branches **DEV**, **STG** e **MAIN** (GitHub) | Ecrãs, regras de negócio, relatórios |
| **Dados** | Cópias encriptadas no **Cloudflare R2** + cópias locais em `backups/` | Clientes, vendas, agendamentos |

**Princípio de ouro:** falha no código **não apaga** os dados de clientes. Os dados vivem no cofre (R2), independentes do Git.

---

## Fases do épico

| Fase | Nome | Estado |
|------|------|--------|
| **1** | Comunicação e Estabilidade de RAM | **Concluída** |
| **2** | O Cofre de Produção e Restauração Inteligente | **Concluída** |
| **3** | Relatórios Executivos e Simulação de Desastre | **Concluída** |

### Fase 3 — entregas

- E-mails semanais e logs com linguagem de gestão (RPO, integridade, sem jargão PRAGMA/FK na frente).
- `scripts/web_startup.py` — arranque autónomo na Web (restaura DB + estado de governança a partir do R2).
- `scripts/sync_trigger.py` — gatilho pós-escrita em **produção** (debounce 120s → backup + sync).
- Painel de Governança com etiquetas executivas (`✅ ÍNTEGRO`, `⏱️ [TEMPO DE RECUPERAÇÃO]`, etc.).
- Testes de contrato para mensagens `✅ [Cloud S3 - Ambiente: …]`.
- `tests/test_resilience_e2e.py` — gatilho, debounce e arranque sem bloqueio em falha de rede.

---

## Protocolo de lançamento (Web)

### Comportamento no arranque (`src/app.py`)

1. **Antes de criar tabelas**, corre `scripts/web_startup.ensure_web_environment_status()`.
2. Se `data/beaba_gestao.db` **já existe** → continua normalmente.
3. Se **não existe** e há credenciais R2 (Secrets ou `.env`):
   - Mensagem: `🛠️ [WEB STARTUP] Restaurando ambiente...`
   - Descarrega o `.beaba.enc` mais recente do prefixo `{env}/hourly/`
   - Repõe `backups/{env}/cloud_sync_manifest.json` e `staging_restore_drill_state.json` de `{env}/state/` no bucket (quando existirem)
   - Mensagem: `✅ [WEB STARTUP] Pronto.`
4. Se **não existe** e **falha de rede** na restauração → `st.warning` para o gestor e **boot continua** (base vazia + `create_tables()`).
5. Se **não existe** e **não há credenciais** (ex.: pytest local):
   - Aviso informativo; `create_tables()` inicializa base vazia.
6. Se **Streamlit Cloud** sem Secrets → erro visível na UI e a app não arranca (protecção).

### Sync automático pós-escrita (`scripts/sync_trigger.py`)

Em `BEABA_ENV=production` (ou `prod` / `main`), após cada gravação bem-sucedida nos módulos **cliente**, **agendamento**, **venda** (venda directa, reconciliação, liquidação de pendências), **financeiro_entradas_convertidas** (status de fatura), **colaborador**, **catálogo**, **usuarios_db** (criar, perfil, activar/inactivar) e **auth_db** (senha, reset, `create_usuario`), o sistema tenta `backup_sqlite_hourly.py` + `backup_sync_cloud.py`, respeitando **debounce de 120 segundos** entre envios.

**Painel de Vendas (`page_vendas.py`):** cadastro/actualização de cliente, **Finalizar Venda** (`registrar_venda` + fatura solicitada), associação pós-venda e liquidação de pendências — todas com gatilho nos módulos de domínio. Não existe exclusão de venda na BD neste ecrã (remover item do carrinho é só estado de sessão).

### Rotina operacional recomendada

| Onde | Acção |
|------|--------|
| **Máquina / Docker** | `scheduler.py` ou cron: `backup_sqlite_hourly` → `backup_sync_cloud` |
| **Streamlit Cloud** | Secrets configurados (ver TOML abaixo); deploy da branch alvo; sync pós-escrita automático em prod |
| **GitHub** | Workflows hourly/daily/weekly + restore semanal (prova técnica CI) |

### O gestor vê (resumo)

- Backup cloud: `✅ [Cloud S3 - Ambiente: …]`
- Agendador: `✅ [AGENDADOR] Ciclo de backup concluído…`
- Restore: `✅ [RESTORE CONCLUÍDO]` ou `❌ [FALHA NO RESTORE]`
- Simulação: `✅ [SIMULAÇÃO BEM-SUCEDIDA]`
- E-mail semanal: **Ambiente Testado**, **Status de Integridade dos Dados**, **Sincronia com o Sistema**

---

## Streamlit Secrets (copiar para o painel Cloud)

No [Streamlit Cloud](https://share.streamlit.io/) → app → **Settings** → **Secrets**, cole:

```toml
# Ambiente da app (develop | staging | production)
ENV_TYPE = "production"
BEABA_ENV = "production"

# Cloudflare R2 (API S3-compatível)
S3_ACCESS_KEY = "COLE_SUA_ACCESS_KEY_ID"
S3_SECRET_KEY = "COLE_SUA_SECRET_ACCESS_KEY"
S3_ENDPOINT_URL = "https://SEU_ACCOUNT_ID.r2.cloudflarestorage.com"
S3_BUCKET_NAME = "nome-do-bucket"
S3_REGION = "auto"
S3_UPLOAD_PREFIX = "prod/hourly/"

# Chave de encriptação dos backups (32 bytes em base64 ou hex 64 chars)
BEABA_BACKUP_KEY = "COLE_SUA_CHAVE_BASE64_32_BYTES"

# Opcional: drill staging lê produção neste prefixo
S3_PRODUCTION_RESTORE_PREFIX = "prod/hourly/"
```

**Importante:** use o mesmo `BEABA_BACKUP_KEY` em todos os ambientes que partilham cópias. Após o primeiro deploy com Secrets, confirme no R2 que existem objectos em `prod/hourly/*.beaba.enc` (ou o prefixo do ambiente).

---

## Referências técnicas

| Script | Função |
|--------|--------|
| `scripts/backup_sqlite_hourly.py` | Cópia local |
| `scripts/backup_sync_cloud.py` | Envio R2 + espelho `state/` |
| `scripts/scheduler.py` | Ciclo automático |
| `scripts/restore_sqlite.py` | Restore encriptado |
| `scripts/restore_test_drill.py` | Simulação Produção → Staging |
| `scripts/web_startup.py` | Arranque Web autónomo |
| `scripts/sync_trigger.py` | Gatilho backup+cloud pós-escrita (prod) |
| `scripts/gha_email_test_restore_weekly.py` | E-mails executivos |

---

## Cobertura de testes (resiliência)

| Camada | Ficheiros / testes | O que valida |
|--------|-------------------|--------------|
| **E2E stress** | `tests/e2e_stress_test.py` (1 teste governança backup) | Shell visual Governança + backup |
| **Resiliência E2E** | `tests/test_resilience_e2e.py` (**6 testes**) | Gatilho pós-cliente, **venda/fatura**, **utilizadores**, debounce 120s, alerta rede sem bloquear boot |
| **Contrato backup** | `tests/test_backup_drill_contract.py` (**6 testes**) | Sync cloud, scheduler, linguagem gestor |
| **Contrato UI gov** | `tests/gov_ui_contract.py` | Etiquetas executivas na página |
| **Smoke UI** | `tests/smoke_test_ui.py` (**2 testes dedicados** + 9 rotas) | `test_smoke_governanca_admin_sector_widgets` (✅ ÍNTEGRO, RPO), `test_smoke_vendas_painel_faturas_totais_boot` (totais/fatura) |

**Suite completa:** `pytest tests/ -v` — **337 testes** (inclui unitários, contratos, smoke e E2E); regressão de resiliência integrada na CI local e pre-push.
