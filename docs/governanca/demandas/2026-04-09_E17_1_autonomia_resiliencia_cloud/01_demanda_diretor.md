# 01 — Demanda do Diretor (fonte: Cursor `@Files` → Arquiteto / Dev / Analista / EQUIPE)

**ID da demanda:** `2026-04-09_E17_1_autonomia_resiliencia_cloud`  
**Marco de produto:** **E17.1** — Autonomia e Resiliência **Cloud Total**  
**Data de registo pela EQUIPE:** 2026-04-09  
**Canal:** **`@Files`**, **Arquiteto**, **Dev**, **Analista**, **EQUIPE**.

---

## Síntese do pedido

Migrar o ciclo **Backup + DR** (hoje com scripts locais E17) para **GitHub Actions** como orquestração principal, com **RPO ~1 h**, **sem dependência obrigatória do Windows**, **criptografia AES-256-GCM** antes de armazenamento frio, **workflow de restore de prova semanal** com evidências (checksum, contagens, `integrity_check`), e **nova aba** no **Monitor de Voo** com matriz temporal e grupos de saúde (Ambiente, Estrutura, Configuração, Arquivos, User Data, Logs).

**Objectivo final:** capacidade de **reconstruir** ambiente + dados + configurações a partir de artefactos na nuvem, documentada e testada.

**Fase actual (§7 + Monitor):** **B — Desenho lógico Cloud** — entrega **`04_desenho_logico.md`** (infra + esquema de telemetria + dashboard); **sem** workflows `.yml` nem alteração a `monitor_governanca.py` até **CONFIRMO** / **PROSSIGA** explícito para implementação.

---

## Próximo passo

- Revisão do [`04_desenho_logico.md`](04_desenho_logico.md) pelo Diretor.  
- Depois: Fase C/D — workflows, scripts partilhados, aba Streamlit, testes, `status_demanda.json`, encerramento.
