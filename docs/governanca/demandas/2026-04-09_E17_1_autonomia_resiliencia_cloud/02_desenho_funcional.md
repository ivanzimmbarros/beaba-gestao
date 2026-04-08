# 02 — Desenho funcional — E17.1 Cloud Total (resumo)

**Demanda:** `2026-04-09_E17_1_autonomia_resiliencia_cloud`  
**Estado:** **Fase B** — detalhe técnico em [`04_desenho_logico.md`](04_desenho_logico.md).

## Objectivos de produto

1. **Orquestração na nuvem:** GitHub Actions como motor do backup horário e do restore de prova semanal, com **RPO ~1 h** e **sempre** código alinhado a **`develop`**.  
2. **Segurança em repouso:** AES-256-GCM antes de armazenamento em **Artifacts / Releases / bucket frio**.  
3. **Prova de recuperação:** download isolado, `integrity_check`, validação de esquema, **checksum** e **contagens** agregadas.  
4. **Observabilidade:** histórico JSON + **Monitor de Voo** com matriz temporal e seis grupos (Ambiente, Estrutura, Configuração, Arquivos, User Data, Logs) e links para runs/logs.  
5. **DR total:** runbook «do zero» a partir de nuvem + segredos externos (ver §8 do 04).

**Restrição:** até **PROSSIGA** para Fase C — **sem** novos workflows nem código Streamlit; apenas este dossier + `status_demanda.json`.
