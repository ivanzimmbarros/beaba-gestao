# 01 — Demanda do Diretor (fonte: Cursor `@Files` → Analista / EQUIPE)

**ID da demanda:** `2026-04-07_E12_refatoracao_painel_operacional`  
**Data de registo pela EQUIPE:** 2026-04-07  
**Canal:** mensagem do Diretor no Cursor com **`@Files`**, menção **Analista** e **EQUIPE**.

---

## Síntese do pedido

O **Diretor** identificou que o [`docs/PAINEL_OPERACIONAL.md`](../../../PAINEL_OPERACIONAL.md) actual está **excessivamente técnico e poluído** para uso como instrumento de comando. Pretende-se:

1. **Torre de Controle** — vista **visual e executiva** no topo (não técnica), permitindo perceber **de relance** em que **fase** (A–F) e **ponto de controlo (PC)** do Fluxo oficial de governança se situa o trabalho.
2. **Diário de Bordo** — **histórico estruturado** de marcos de produto (**E01 a E11**) com **resumo executivo** de entregas e registo de **falhas de processo / retrabalhos** (quando existirem).
3. **Interface Streamlit** — actualizar o módulo **Fluxo e governança** para reflectir a **nova estrutura**, continuando a ler primariamente de [`status_demanda.json`](../../status_demanda.json).
4. **Manutenção normativa** — **não remover** as definições **PC1–PC13** (nem o conteúdo técnico necessário); **deslocá-las** para **apêndice** ou secção claramente **secundária**. O **topo** do `PAINEL_OPERACIONAL.md` deve ser **100% visual / executivo**.

**Restrição explícita do Diretor:** seguir o **percurso normal (SUCESSO)** em [`FLUXO_SUCESSO_E_FALHA.md`](../../FLUXO_SUCESSO_E_FALHA.md); **não implementar código** da app antes do **PC2** (isto é, a confirmação formal do desenho funcional e o par **PC1→PC2** fechados conforme norma).

---

## Confirmações já assumidas na demanda

- O **ficheiro normativo** do fluxo mantém-se **`FLUXO_SUCESSO_E_FALHA.md`** (nomenclatura executiva: Fluxo oficial de governança).
- A **fonte de verdade** operacional para estado em tempo real continua a ser **`status_demanda.json`**, **actualizado pela EQUIPE**.

---

## Próximo passo normativo (Fluxo oficial — percurso normal / SUCESSO)

- **`02_desenho_funcional.md`** — proposta de solução (Torre de Controle, Diário de Bordo, JSON, Streamlit, apêndice do Painel) para **validação do Diretor no chat**.  
- **`03_confirmacao_diretor.md`** — preenchido após **CONFIRMO** / **PROSSIGA** explícito no Cursor.  
- Só após **PC1** (Git com `01`–`03`) e **PC2** (Painel + JSON alinhados): implementação técnica (`PAINEL_OPERACIONAL.md`, `page_fluxo_gestao.py`, extensões ao JSON, etc.).
