# 01 — Demanda do Diretor (fonte: Cursor `@Files` → Analista / EQUIPE)

**ID da demanda:** `2026-04-07_E14_telemetria_live`  
**Data de registo pela EQUIPE:** 2026-04-07  
**Canal:** mensagem no Cursor com **`@Files`**, **Analista** e **EQUIPE**.

---

## Síntese do pedido

O **Diretor** identificou uma **falha grave de usabilidade**: o Painel e o fluxo actual são **reativos** — funcionam como **registo pós-execução**, não como instrumento de **acompanhamento imediato** do trabalho da IA.

**Exigência:** um **dashboard em tempo quase real** (“telemetria ao vivo”) que permita ver **onde a EQUIPE está neste momento**, **o que está a executar** e **o que está na fila**, **etapa a etapa**, enquanto a IA trabalha.

**Papel relativo dos artefactos:**

- **[`docs/PAINEL_OPERACIONAL.md`](../../../PAINEL_OPERACIONAL.md)** — continua a ser actualizado nos **PCs** (histórico e prova de governança).
- **`status_demanda.json` + página Streamlit “Fluxo e governança”** — passam a ser o **núcleo “ao vivo”** da percepção operacional (telemetria).

---

## Restrições explícitas (Fase A)

- Seguir o **Fluxo oficial de governança** — **percurso normal (SUCESSO)**, passos **1–3** (demanda → `02_desenho_funcional` → apresentação para aprovação).
- **Não alterar** neste momento: código Python, estrutura efectiva de `status_demanda.json`, nem dependências — **apenas** `01` e `02` no dossier.
- Implementação (**PROSSIGA** do Diretor) fica para fases posteriores (PC1 completo com `03`, etc.).

---

## Próximo passo normativo

- **`02_desenho_funcional.md`** — proposta de campos JSON, protocolo da EQUIPE e UI **STATUS LIVE** (incl. opções de actualização automática da página).  
- Após **CONFIRMO** / **PROSSIGA** no chat: `03_confirmacao_diretor.md`, PCs, código e encerramento conforme norma.
