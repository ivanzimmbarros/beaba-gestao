# Fluxo obrigatório — SUCESSO e FALHA (regra máxima)

**Normativo:** este documento define o processo **obrigatório** para **toda** evolução do BeaBa Gestão, em conjunto com [`.cursorrules`](../../.cursorrules) e [`PAINEL_OPERACIONAL.md`](../PAINEL_OPERACIONAL.md).

**Selos de aprovação:** cada “selo” deve ser **rastreável no Git** — preferencialmente num **commit** em `develop` com mensagem explícita (`selo(diretor): …`, `selo(analista): …`, etc.) **e** bloco datado no artefacto em `docs/governanca/demandas/<ID>/` (ver `README` dessa pasta).

---

## Validação, críticas e sugestões (equipa)

| Tópico | Crítica / risco | Sugestão |
|:---|:---|:---|
| Numeração original | Passos **20** e **21** duplicados no texto recebido | Renumerados de **22** a **25** abaixo; manter sempre este ficheiro como referência. |
| Ordem Git → Painel | Inverter Painel antes do Git gera divergência com a Action | **Sempre:** primeiro **GitHub** (commit + push `develop`), depois **Painel** / `CONTROLE` no **mesmo** ciclo de entrega. |
| “Selo” ambíguo | Sem traço no Git, o selo não existe para auditoria | Commit + ficheiro em `demandas/<ID>/` com texto **APROVADO POR: papel, data, referência**. |
| Desenho funcional quebrado por QA | Exige novo ciclo completo | Regra explícita em **FALHA** — nova confirmação formal do **Diretor** e reexecução desde o passo **1**. |
| Paralelismo | Dev “adiantar” QA sem pareceres | Fluxo **estritamente sequencial**; regressões voltam ao **primeiro** passo afectado. |
| PC13 | Texto mencionava só Painel após GitHub | **PC13a** Git (encerramento) **antes** de **PC13b** Painel. |

---

## Fluxo SUCESSO (obrigatório)

### Fase A — Analista + Diretor (desenho funcional)

| # | Actor | Acção |
|:---:|:---|:---|
| 1 | Analista | Recebe demanda do Diretor e **regista** requisição (`docs/governanca/demandas/<ID>/01_demanda_diretor.md`). |
| 2 | Analista | Prepara **desenho funcional** com base nos requisitos iniciais. |
| 3 | Analista | Apresenta desenho funcional ao **Diretor**, com explicação do que será desenvolvido, e **solicita confirmação formal**. |
| 4 | Diretor | Emite **confirmação formal** (registada no mesmo dossier da demanda). |

**PC1 — GitHub:** `develop` contém (1) demanda original do Diretor; (2) desenho funcional aprovado; (3) **selo / confirmação formal do Diretor** (texto + referência de commit).

**PC2 — Painel:** `docs/PAINEL_OPERACIONAL.md` e, quando aplicável, `CONTROLE_DE_VOO.md` **actualizados após** PC1 (fase, links, ID da demanda).

---

### Fase B — Arquiteto + Analista (desenho lógico)

| # | Actor | Acção |
|:---:|:---|:---|
| 5 | Analista | Aciona Arquiteto (registo no dossier da demanda). |
| 6 | Arquiteto | Recebe desenho funcional **e** demanda inicial. |
| 7 | Arquiteto | Prepara **desenho lógico** e solicita validação ao Analista. |
| 8 | Analista | Valida desenho lógico e responde ao Arquiteto. |
| 9 | Arquiteto | Recebe **confirmação explícita** da validação do Analista. |

**PC3 — GitHub:** desenho lógico aprovado pelo Analista + **selo Analista (validação funcional do desenho lógico)**.

**PC4 — Painel:** actualizado **após** PC3.

---

### Fase C — Dev + Arquiteto (código, 1.ª validação técnica)

| # | Actor | Acção |
|:---:|:---|:---|
| 10 | Arquiteto | Aciona Dev. |
| 11 | Dev | Recebe desenho lógico **e** funcional; **codifica**; envia ao Arquiteto para **validação técnica**. |
| 12 | Arquiteto | Valida código; elabora **PARECER DE AVALIAÇÃO DO CÓDIGO (Arquiteto)**; responde ao Dev. |
| 13 | Dev | Recebe confirmação do Arquiteto **e** o parecer. |

**PC5 — GitHub:** parecer do Arquiteto (ficheiro em `demandas/<ID>/` ou `docs/`) + **selo Arquiteto**.

**PC6 — Painel:** actualizado **após** PC5.

---

### Fase D — Analista + Dev (validação de negócio do código + plano de testes)

| # | Actor | Acção |
|:---:|:---|:---|
| 14 | Arquiteto | Aciona **Analista** para validação do código entregue pelo Dev. |
| 15 | Analista | Recebe parecer do Arquiteto **e** código (ou referência de branch/commit); valida alinhamento ao desenho funcional. |
| 16 | Analista | Elabora **PARECER DE AVALIAÇÃO DO ANALISTA** e responde ao Dev. |
| 17 | Dev | Recebe confirmação do Analista **e** parecer. |
| 18 | Dev | Prepara **plano de testes** da demanda e **actualiza** [`docs/CADERNO_TESTES_MASTER.md`](../CADERNO_TESTES_MASTER.md) (ou secção referenciada por ID de demanda). |

**PC7 — GitHub:** evidência de código aprovado por **Arquiteto e Analista**; plano de testes actualizado; **selo Analista** (aceitação para fase QA).

**PC8 — Painel:** actualizado **após** PC7.

---

### Fase E — QA (plano de testes + execução massiva)

| # | Actor | Acção |
|:---:|:---|:---|
| 19 | Dev | Aciona QA. |
| 20 | QA | Recebe: desenho funcional, desenho lógico, pareceres finais (Analista e Arquiteto), plano de testes actualizado e código. |
| 21 | QA | Valida plano de testes; se necessário, **actualiza** o plano (incremento documentado). |

**PC9 — GitHub:** se o plano de testes tiver mudado face a PC7, **novo** commit com o plano actualizado.

**PC10 — Painel:** actualizado **após** PC9 (ou após PC8 se não houve alteração — registar explicitamente “sem alteração ao plano”).

| # | Actor | Acção |
|:---:|:---|:---|
| 22 | QA | Executa **testes massivos** (regressão + novidades) conforme documento final; elabora **PARECER FINAL DE QA** com resultados; envia a **Dev, Arquiteto e Analista**. |
| 23 | Dev, Arquiteto, Analista | Recebem confirmação de QA **e** parecer com **todos** os testes e resultados. |

**PC11 — GitHub:** resultado dos testes massivos (relatório em `demandas/<ID>/` ou anexo referenciado) + **selo QA**.

**PC12 — Painel:** actualizado **após** PC11.

---

### Fase F — Diretor (encerramento)

| # | Actor | Acção |
|:---:|:---|:---|
| 24 | Analista | Informa o **Diretor** da conclusão da demanda e **liberação para testes finais** / aceitação de produto (conforme definido com o Diretor). |

**PC13 — GitHub (13a):** acta de encerramento (`docs/governanca/demandas/<ID>/99_encerramento.md`) com data em que o Analista informou o Diretor e referência ao parecer QA; **commit + push** em `develop`.

**PC13 — Painel (13b):** actualizado **após** 13a — demanda **concluída**, registo no final de `PAINEL_OPERACIONAL.md`.

*Nota:* corresponde ao “PC13” do processo original (Painel após Git), mantendo **13a** explícito para não haver Painel sem prova no repositório.

---

## Fluxo FALHA (obrigatório)

1. **Qualquer falha** numa etapa obriga a **revalidação** das etapas anteriores afectadas, **até** restabelecer o fluxo SUCESSO.
2. Durante o fluxo reverso, **todos** os pontos de controlo aplicáveis devem ser **repetidos** (GitHub **e** Painel), com **pareceres negativos** documentados (motivo, evidências, actor).
3. **Exemplo A — Falha em QA:** QA notifica Dev, Arquiteto e Analista com **parecer completo** (o que falhou e porquê). Dev corrige; volta-se às etapas **11–18** (Arquiteto + Analista + plano de testes) **antes** de novo ciclo QA completo (19–23).
4. **Exemplo B — Falha do Analista na validação do código (após parecer favorável do Arquiteto):** Analista notifica Arquiteto e Dev com **parecer negativo**; Dev e Arquiteto tratam a causa; reexecutar **12–18** conforme necessário.
5. **Redesenho funcional exigido pelo QA (ou por qualquer actor):** nova versão do desenho funcional deve ser **reapresentada ao Diretor** e **confirmada formalmente**; em seguida, **todo** o fluxo SUCESSO é **refeito** desde o passo **1** (nova pasta `demandas/<ID_v2>/` ou sufixo de versão).

---

## Dashboard de status (obrigatório)

- **Ficheiro canónico:** [`status_demanda.json`](status_demanda.json) — estado actual: fase, responsável, pendentes, concluídos, falha.
- **Visualização:** aplicação Streamlit — **Fluxo e governança** (lê o JSON; actualizar o JSON em cada PC de Painel).

---

## Relação com o “Fluxo de 15 Etapas”

O fluxo técnico em [`PAINEL_OPERACIONAL.md`](../PAINEL_OPERACIONAL.md) (etapas 01–15 por ciclo de produto) **continua válido** como **desdobramento** principalmente nas fases de **implementação e entrega técnica** (Dev, migrações, testes automatizados, CI), **sempre dentro** deste fluxo SUCESSO/FALHA e **nunca** como atalho que salte pareceres ou pontos de controlo.
