# 01 — Demanda do Diretor (fonte: Cursor `@Files` → Analista / EQUIPE)

**ID da demanda:** `2026-04-08_E17_backup_dr`  
**Marco de produto:** **E17**  
**Data de registo pela EQUIPE:** 2026-04-08  
**Canal:** **`@Files`**, **Analista**, **EQUIPE**.

---

## Síntese do pedido

O **Diretor** exige **Backup e recuperação (DR)** sobre a base **SQLite** usada em `data/beaba_gestao.db` (fallback actual em [`src/database/connection.py`](../../../../src/database/connection.py)):

1. **Hot-backup de hora em hora** — cópia consistente da base **em serviço**, sem parar a aplicação, via mecanismos suportados pelo SQLite (API de *backup* online).
2. **Script de auto-restauro semanal** — procedimento automatizado que valide integridade com **`PRAGMA integrity_check`** (e variantes seguras), com registo de resultado.
3. **Estratégia de sincronização externa (nuvem)** — definir como réplicas de backup saem da máquina local (ex.: pasta sincronizada, object storage, regras de exclusão do ficheiro **vivo**).

**Restrição (Fase A — §7):** cumprida em 2026-04-08; **PROSSIGA** recebido — ver [`99_encerramento.md`](99_encerramento.md) para entregas (`scripts/`, `connection.py`, `backups/`, testes, PAINEL).

---

## Próximo passo

- Demanda **encerrada** no marco E17. Próximo pedido: **`@Files` → Analista**.
