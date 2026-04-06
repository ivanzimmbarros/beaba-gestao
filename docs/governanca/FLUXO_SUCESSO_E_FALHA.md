# Fluxo obrigatório — SUCESSO e FALHA (regra máxima)

**Normativo:** este documento define o processo **obrigatório** para **toda** evolução do BeaBa Gestão, em conjunto com [`.cursorrules`](../../.cursorrules) e [`PAINEL_OPERACIONAL.md`](../PAINEL_OPERACIONAL.md).

**Selos de aprovação:** cada “selo” deve ser **rastreável no Git** — preferencialmente num **commit** em `develop` com mensagem explícita (`selo(diretor): …`, `selo(analista): …`, etc.) **e** bloco datado no artefacto em `docs/governanca/demandas/<ID>/` (ver `README` dessa pasta).

---

## Canal oficial de demanda e responsabilidade da EQUIPE (@Files) — **mandatório**

1. **Entrada da demanda:** o Diretor envia a instrução **exclusivamente** através do **Cursor**, usando **`@Files`** dirigido à persona **Analista** (ou menção explícita equivalente à **EQUIPE** / Analista no mesmo sentido). Essa mensagem é a **fonte autoritativa** da demanda inicial.
2. **Sem documentação manual pelo Diretor:** o Diretor **não** é obrigado a criar, editar ou anexar ficheiros complementares no repositório (Markdown, JSON, etc.). **É proibido** ao processo **exigir** do Diretor a elaboração manual desses artefactos para avançar.
3. **EQUIPE = agente Cursor** que executa as personas (Analista, Arquiteto, Dev, QA) em sequência lógica: a EQUIPE **gera, actualiza e comita automaticamente** toda a documentação necessária — `docs/governanca/demandas/<ID>/` (incluindo transcrição/síntese da demanda, desenhos, pareceres, selos), [`PAINEL_OPERACIONAL.md`](../PAINEL_OPERACIONAL.md), [`CONTROLE_DE_VOO.md`](../../CONTROLE_DE_VOO.md), [`MODELO_ARQUITETURA.md`](../MODELO_ARQUITETURA.md), [`CADERNO_TESTES_MASTER.md`](../CADERNO_TESTES_MASTER.md), [`status_demanda.json`](status_demanda.json), código, testes, e **`commit` + `push`** em `develop` em cada ponto de controlo aplicável.
4. **Após a primeira intervenção** do Diretor na thread da demanda, **toda** a actividade complementar (documentação, painéis, evolução de ficheiros de controlo, implementação) fica **sob gestão da EQUIPE** até ao próximo marco que exija **resposta explícita** do Diretor no chat (ex.: confirmação formal do desenho funcional, **PROSSIGA**, decisão de veto).
5. **Confirmações do Diretor no chat:** quando o Diretor aprovar ou ordenar no Cursor (texto na conversa), a EQUIPE **regista** essa decisão no Git (`03_confirmacao_diretor.md` ou equivalente, com data e citação/sumário da aprovação) **sem** exigir que o Diretor edite o repositório.

---

## Validação, críticas e sugestões (equipa)

| Tópico | Crítica / risco | Sugestão |
|:---|:---|:---|
| Numeração original | Passos **20** e **21** duplicados no texto recebido | Renumerados de **22** a **25** abaixo; manter sempre este ficheiro como referência. |
| Ordem Git → Painel | Inverter Painel antes do Git gera divergência com a Action | **Sempre:** primeiro **GitHub** (working copy + **commit** + **push** `origin/develop`), depois **Painel** / `CONTROLE` no **mesmo** ciclo de entrega. |
| “Selo” ambíguo | Sem traço no Git, o selo não existe para auditoria | Commit + ficheiro em `demandas/<ID>/` com texto **APROVADO POR: papel, data, referência**. |
| Desenho funcional quebrado por QA | Exige novo ciclo completo | Regra explícita em **FALHA** — nova confirmação formal do **Diretor** e reexecução desde o passo **1**. |
| Paralelismo | Dev “adiantar” QA sem pareceres | Fluxo **estritamente sequencial**; regressões voltam ao **primeiro** passo afectado. |
| PC13 | Texto mencionava só Painel após GitHub | **PC13a** Git (encerramento) **antes** de **PC13b** Painel. |
| Documentação “manual” pelo Diretor | Gargalo e incoerência com o uso de Cursor | **Proibido exigir**; EQUIPE gera **todos** os ficheiros a partir do `@Files` + respostas no chat. |

---

## Definição: ponto de controlo **GitHub** = local **e** cloud (obrigatório)

Cada PC cujo título inclui **GitHub** (PC1, PC3, PC5, PC7, PC9 quando aplicável, PC11, PC13a) exige **cumulativamente**:

1. **Arquivos locais** — working copy actualizada (ficheiros editados ou criados no clone).
2. **`git commit`** — alterações registadas no repositório **local**.
3. **`git push`** para o **remoto** (ex.: **`origin/develop`**) — **obrigatório** — para que a **cloud** (GitHub) e as **Actions** reflitam o mesmo estado.

**Não cumpre** o ponto de controlo: apenas editar ficheiros sem commit; ou commit **sem** push (histórico só na máquina local). A EQUIPE deve considerar o PC **fechado** só após verificar que **`origin/develop`** (ou ramo acordado) contém o commit.

---

## Fluxo SUCESSO (obrigatório)

### Fase A — Analista + Diretor (desenho funcional)

| # | Actor | Acção |
|:---:|:---|:---|
| 1 | **EQUIPE (Analista)** | Recebe a demanda do Diretor **via Cursor (`@Files` → Analista)**. **Cria** `docs/governanca/demandas/<ID>/` e o ficheiro `01_demanda_diretor.md` com **transcrição fiel ou síntese datada** do pedido (fonte = conversa). **Actualiza** `status_demanda.json`. |
| 2 | **EQUIPE (Analista)** | Prepara **`02_desenho_funcional.md`** com base nos requisitos extraídos da demanda. |
| 3 | **EQUIPE (Analista)** | Apresenta o desenho funcional ao **Diretor no chat** (explicação detalhada) e **solicita confirmação formal** (ex.: “CONFIRMO”, **PROSSIGA**). |
| 4 | Diretor | Responde **no Cursor** com **confirmação formal**. A **EQUIPE** regista em **`03_confirmacao_diretor.md`** (data, sumário ou citação da aprovação) — o Diretor **não** precisa editar o repo. |

**PC1 — GitHub:** ficheiros `01`–`03` no dossier; **commit** + **`push` para `origin/develop` (local + cloud)** — ver secção *Definição: ponto de controlo GitHub* neste documento.

**PC2 — Painel:** `docs/PAINEL_OPERACIONAL.md` e, quando aplicável, `CONTROLE_DE_VOO.md` **actualizados após** PC1 (fase, links, ID da demanda).

---

### Fase B — Arquiteto + Analista (desenho lógico)

| # | Actor | Acção |
|:---:|:---|:---|
| 5 | **EQUIPE (Analista)** | Aciona fase Arquiteto; **actualiza** `status_demanda.json` e registo no dossier (linha temporal / `00_indice.md` opcional). |
| 6 | **EQUIPE (Arquiteto)** | Consome `01`–`03` e `02`. |
| 7 | **EQUIPE (Arquiteto)** | Produz **`04_desenho_logico.md`**; solicita validação interna (Analista na EQUIPE). |
| 8 | **EQUIPE (Analista)** | Valida desenho lógico; produz **`05_validacao_analista_desenho_logico.md`**. |
| 9 | **EQUIPE (Arquiteto)** | Encerra ciclo de desenho lógico com parecer favorável documentado. |

**PC3 — GitHub:** desenho lógico + selo Analista; **commit + push** para **origin** (local + cloud).

**PC4 — Painel:** actualizado **após** PC3.

---

### Fase C — Dev + Arquiteto (código, 1.ª validação técnica)

| # | Actor | Acção |
|:---:|:---|:---|
| 10 | **EQUIPE (Arquiteto)** | Aciona Dev (registo no dossier). |
| 11 | **EQUIPE (Dev)** | Codifica; mantém `PAINEL`/`MODELO`/código; prepara entrega para validação. |
| 12 | **EQUIPE (Arquiteto)** | Valida código; **`06_parecer_arquiteto_codigo.md`**. |
| 13 | **EQUIPE (Dev)** | Incorpora parecer ou corrige conforme FALHA. |

**PC5 — GitHub:** parecer Arquiteto + selo; **commit + push** para **origin** (local + cloud).

**PC6 — Painel:** actualizado **após** PC5.

---

### Fase D — Analista + Dev (validação de negócio do código + plano de testes)

| # | Actor | Acção |
|:---:|:---|:---|
| 14 | **EQUIPE (Arquiteto)** | Aciona **Analista** para validação de negócio do código. |
| 15 | **EQUIPE (Analista)** | Valida alinhamento ao funcional; referência a commit/PR em `develop`. |
| 16 | **EQUIPE (Analista)** | **`07_parecer_analista_codigo.md`**. |
| 17 | **EQUIPE (Dev)** | Recebe parecer; corrige se necessário (FALHA). |
| 18 | **EQUIPE (Dev)** | **Plano de testes** + **actualização obrigatória** de [`docs/CADERNO_TESTES_MASTER.md`](../CADERNO_TESTES_MASTER.md). |

**PC7 — GitHub:** código + plano de testes + selo Analista; **commit + push** para **origin** (local + cloud).

**PC8 — Painel:** actualizado **após** PC7.

---

### Fase E — QA (plano de testes + execução massiva)

| # | Actor | Acção |
|:---:|:---|:---|
| 19 | **EQUIPE (Dev)** | Aciona QA (registo + `pytest` local antes de pedir selo). |
| 20 | **EQUIPE (QA)** | Consolida inputs (docs + código em `develop`). |
| 21 | **EQUIPE (QA)** | Valida plano; **actualiza** `CADERNO_TESTES_MASTER` e dossier se houver incremento. |

**PC9 — GitHub:** se o plano tiver mudado, **commit + push** para **origin** com o plano actualizado (local + cloud); se não mudou, registar em PC10 e **não** exigir commit vazio.

**PC10 — Painel:** actualizado **após** PC9 (ou após PC8 se não houve alteração — registar explicitamente “sem alteração ao plano”).

| # | Actor | Acção |
|:---:|:---|:---|
| 22 | **EQUIPE (QA)** | **Testes massivos** (`pytest` completo, smoke acordado, CI verde); **`09_parecer_final_qa.md`**; notifica no **chat** (resumo para o Diretor se aplicável). |
| 23 | **EQUIPE** | Estados internos alinhados; **nenhum** selo QA sem evidência no Git. |

**PC11 — GitHub:** parecer QA + selo; **commit + push** para **origin** (local + cloud).

**PC12 — Painel:** actualizado **após** PC11.

---

### Fase F — Diretor (encerramento)

| # | Actor | Acção |
|:---:|:---|:---|
| 24 | **EQUIPE (Analista)** | Informa o **Diretor no chat** da conclusão e libertação para testes finais / aceitação. **`99_encerramento.md`** gerado pela EQUIPE com data e referência ao parecer QA. |

**PC13 — GitHub (13a):** `99_encerramento.md`; **commit + push** para **`origin/develop`** (local + cloud).

**PC13 — Painel (13b):** actualizado **após** 13a — demanda **concluída**, registo no final de `PAINEL_OPERACIONAL.md`.

*Nota:* corresponde ao “PC13” do processo original (Painel após Git), mantendo **13a** explícito para não haver Painel sem prova no repositório.

---

## Fluxo FALHA (obrigatório)

1. **Qualquer falha** numa etapa obriga a **revalidação** das etapas anteriores afectadas, **até** restabelecer o fluxo SUCESSO.
2. Durante o fluxo reverso, **todos** os pontos de controlo aplicáveis devem ser **repetidos** (GitHub **e** Painel), com **pareceres negativos** documentados (motivo, evidências, actor).
3. **Exemplo A — Falha em QA:** QA notifica Dev, Arquiteto e Analista com **parecer completo** (o que falhou e porquê). Dev corrige; volta-se às etapas **11–18** (Arquiteto + Analista + plano de testes) **antes** de novo ciclo QA completo (19–23).
4. **Exemplo B — Falha do Analista na validação do código (após parecer favorável do Arquiteto):** Analista notifica Arquiteto e Dev com **parecer negativo**; Dev e Arquiteto tratam a causa; reexecutar **12–18** conforme necessário.
5. **Redesenho funcional exigido pelo QA (ou por qualquer actor):** a EQUIPE prepara a nova versão do desenho funcional; **reapresentação ao Diretor no chat** e **confirmação formal** (resposta no Cursor); a EQUIPE regista em Git; **todo** o fluxo SUCESSO é **refeito** desde o passo **1** (nova pasta `demandas/<ID_v2>/` ou sufixo de versão).

6. **Automático em sentido de processo:** “automático” significa que a **EQUIPE** executa as acções (ficheiros, commits, painel, JSON) **sem solicitar ao Diretor** que os faça manualmente; não dispensa **aprovações** do Diretor no chat quando o fluxo as exige.

---

## Dashboard de status (obrigatório)

- **Ficheiro canónico:** [`status_demanda.json`](status_demanda.json) — estado actual: fase, responsável, pendentes, concluídos, falha. **Actualização:** exclusivamente pela **EQUIPE** em cada par **Painel** (após o respectivo commit), **não** pelo Diretor.
- **Visualização:** aplicação Streamlit — **Fluxo e governança** (lê o JSON).

---

## Relação com o “Fluxo de 15 Etapas”

O fluxo técnico em [`PAINEL_OPERACIONAL.md`](../PAINEL_OPERACIONAL.md) (etapas 01–15 por ciclo de produto) **continua válido** como **desdobramento** principalmente nas fases de **implementação e entrega técnica** (Dev, migrações, testes automatizados, CI), **sempre dentro** deste fluxo SUCESSO/FALHA e **nunca** como atalho que salte pareceres ou pontos de controlo.
