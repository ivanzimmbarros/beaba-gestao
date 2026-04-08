# 02 — Desenho funcional — E17 Backup e DR (SQLite)

**Demanda:** `2026-04-08_E17_backup_dr`  
**Marco:** **E17**  
**Data:** 2026-04-08  
**Estado:** **Encerrada** — implementação pós-**PROSSIGA**; ver [`99_encerramento.md`](99_encerramento.md).

---

## 1. Objectivo e âmbito

| Pilar | Meta |
|:---|:---|
| **RPO** | Perda máxima de dados orientativa **≤ 1 hora** (cópia horária). |
| **RTO** | Não fixado numericamente neste documento; o procedimento de restauro **manual** a partir de cópia validada deve ser **documentado e repetível** em menos de uma hora de trabalho qualificado. |
| **Âmbito** | Ficheiro SQLite principal **`data/beaba_gestao.db`** e mesma pasta (ex.: `-wal`/`-shm` se **WAL** estiver activo). **Fora de âmbito** neste marco: PostgreSQL/MySQL via secrets (futuro: política separada). |

**Princípio de segurança:** o ficheiro de base **em uso** pela app **não** é o alvo directo da sincronização com a nuvem; apenas **cópias fechadas** geradas pelo processo de backup.

---

## 2. Hot-backup horário (SQLite)

### 2.1 Definição de «hot»

**Hot-backup** = cópia **consistente** obtida **enquanto** a aplicação pode estar a usar a base, **sem** exigir paragem administrativa da app.

Mecanismo recomendado: **SQLite Backup API** (`sqlite3.Connection.backup()` em Python) a partir de uma conexão de leitura sobre o ficheiro de dados.

### 2.2 Conexão de origem

- Abrir o ficheiro de produção com URI **`mode=ro`** (read-only) quando possível, para reduzir pressão de escrita e clarificar intenção.
- Compatibilidade com **WAL**: recomenda-se activar **`PRAGMA journal_mode=WAL`** na app (Fase C) se ainda não estiver activo — melhora concorrência leitura/escrita e comportamento previsível do backup online. O desenho assume verificação do modo actual na implementação.

### 2.3 Conexão de destino

- Ficheiro novo por execução: `backups/hourly/beaba_gestao_YYYYMMDD_HHMMSS.db` (hora local ou UTC — **fixar uma** no código e documentar).
- Após `backup()` concluir com sucesso, executar no ficheiro de destino (aberto em exclusivo breve): **`PRAGMA quick_check;`** — falha ⇒ apagar cópia falhada, registar erro, não promover.

### 2.4 Rotação e retenção

- Manter as últimas **N** cópias horárias (proposta inicial: **N = 168** ≈ 7 dias; configurável por constante ou env).
- Apagar as mais antigas fora da janela (por timestamp no nome ou metadados).

### 2.5 Agendamento

- **Windows:** Tarefa agendada (Task Scheduler) a invocar `python -m ...` ou `scripts\backup_hourly.cmd` na raiz do repo / venv activo — **intervalo 1 hora**.
- **Linux/macOS:** entrada `cron` equivalente.
- Documentar no **PAINEL** ou **README** interno do dossier: caminho do interpretador, utilizador, e que a app pode estar aberta.

### 2.6 Falhas e locks

- Se o ficheiro estiver bloqueado de forma a impedir abertura `ro`, registar falha, sair com código ≠ 0, e deixar a tarefa repetir na hora seguinte (sem bloquear a app).
- Logs em `backups/logs/backup_hourly.log` (rotação simples por tamanho ou data — Fase C).

---

## 3. Auto-restauro semanal e `PRAGMA integrity_check`

### 3.1 Semântica de «auto-restauro»

Para **não** colocar em risco a base de produção sem intervenção humana, neste marco **auto-restauro** significa:

1. **Seleccionar** a cópia a validar (proposta: **última cópia horária bem sucedida** **ou** cópia designada «semanal» — snapshot copiado domingos 02:00 para `backups/weekly/`).
2. **Copiar** para um ficheiro temporário `backups/restore_verify/staging_YYYYMMDD.db` (ou abrir a cópia directamente em só leitura).
3. Executar **`PRAGMA integrity_check;`** (completo, mais pesado que `quick_check`) e opcionalmente **`PRAGMA foreign_key_check;`**.
4. **Registar** resultado (OK / mensagem de erro) em `backups/logs/restore_weekly.log` e código de saída **0** só se integralidade **ok**.
5. **Remover** staging após teste (não alterar `data/beaba_gestao.db`).

### 3.2 Restauro real (produção)

- **Manual e documentado:** operador substitui `data/beaba_gestao.db` por cópia validada **com a app parada**, ou restaura a partir de cópia em nuvem para `data/` e reinicia. Checklist em `99_encerramento` ou anexo do dossier (Fase F).

### 3.3 Agendamento

- **Semanal** (ex.: domingo 03:00), mesma infra de agendamento que o backup horário.

---

## 4. Sincronização externa (nuvem)

### 4.1 Risco do ficheiro «vivo»

Sincronizar **`data/beaba_gestao.db`** activo com OneDrive/Dropbox/Google Drive **não** é política de backup: pode corromper a base ou gerar cópias inconsistentes. **Proibição normativa:** pasta **`data/`** (ou pelo menos `*.db` activo) deve constar de **exclusão** na sincronização do cliente de nuvem, **ou** o projecto deve residir fora da pasta sincronizada para `data/`.

### 4.2 Alvo recomendado

- **Pasta dedicada** apenas de **réplicas de backup** já fechadas, por exemplo:
  - `backups/cloud_queue/` — script pós-backup copia o último `.db` validado para cá; apenas esta pasta está no âmbito do cliente de nuvem **ou**
  - **rclone** / **AWS CLI** / **AzCopy** para envio a **S3**, **Azure Blob**, **Backblaze B2**, etc., em horário diferido (ex.: após backup horário).

### 4.3 Confidencialidade

- Dados de gestão podem ser sensíveis: recomendar **encriptação** antes do upload (ex.: **age**, **GPG**, ou zip com palavra-passe forte) **ou** bucket com **SSE** e políticas de acesso mínimas. A escolha concreta fica para **configuração** (secrets / env), não hardcoded.

### 4.4 Verificação

- A prova semanal (`integrity_check` sobre cópia) valida **integridade lógica** do ficheiro copiado; **restaurar** periodicamente num ambiente de teste (trimestral) é melhoria opcional pós-E17.

---

## 5. Artefactos previstos (pós-PROSSIGA)

| Artefacto | Função |
|:---|:---|
| `scripts/backup_sqlite_hourly.py` (nome definitivo na Fase B) | Backup API + `quick_check` + rotação + log. |
| `scripts/verify_restore_weekly.py` | Cópia/staging + `integrity_check` + log; sem tocar na produção. |
| `backups/.gitkeep` ou política `.gitignore` | Garantir que **ficheiros `.db` de backup** não entram no Git; apenas estrutura vazia / docs. |
| Documentação | `PAINEL_OPERACIONAL.md` ou secção E17: comandos, agendamento Windows, nuvem, restauro manual. |

---

## 6. Critérios de aceite (implementação — Fases C–E)

- [x] Backup horário corre com app em uso; ficheiros gerados passam `quick_check` no destino.  
- [x] Rotação respeita N configurável; logs com timestamp e erros claros.  
- [x] Job semanal executa `integrity_check` sobre cópia de teste; falha ⇒ código de saída ≠ 0 e registo no log.  
- [x] Documentação de nuvem: exclusão de `data/*.db` activo + destino de réplicas; nenhum segredo no repositório.  
- [x] `pytest` verde; não regressão na app; **CADERNO** actualizado no PC normativo.

---

## 7. Pedido ao Diretor *(cumprido)*

**PROSSIGA** recebido — implementação em `scripts/`, `connection.py`, testes e documentação conforme [`99_encerramento.md`](99_encerramento.md).
