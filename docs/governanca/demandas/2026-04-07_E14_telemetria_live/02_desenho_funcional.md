# 02 — Desenho funcional — E14 Telemetria “ao vivo” (Torre → STATUS LIVE)

**Demanda:** `2026-04-07_E14_telemetria_live`  
**Data:** 2026-04-07  
**Estado:** **Proposta — aguarda CONFIRMO / PROSSIGA do Diretor no Cursor.**

---

## 1. Problema e objectivo

| Hoje | Desejado |
|:---|:---|
| O Diretor infere o progresso sobretudo **depois** de commits / actualizações do Painel. | **Visibilidade contínua** da micro-operação actual e da **fila imediata**, na app, alimentada por `status_demanda.json`. |
| A Torre (fases A–F) reflecte **estado grosso**, não “o que está a acontecer neste segundo”. | Bloco **STATUS LIVE** no topo: texto claro + fila + (opcional) indicador de actividade. |

**Princípio:** o **Painel .md** mantém-se como **histórico e auditoria** nos PCs; o **JSON + Streamlit** tornam-se o **coração operacional ao vivo** para quem acompanha a sessão de trabalho.

---

## 2. Novo padrão de comportamento da EQUIPE (obrigatório após implementação)

**Primeira acção** ao iniciar **qualquer microtarefa** com impacto visível para o Diretor (ex.: “Redigir `04_desenho_logico.md`”, “Implementar `test_venda.py`”, “Corrigir migração”, “Actualizar Painel PC2”):

1. **Actualizar** `docs/governanca/status_demanda.json` com:
   - **`live_status`** — uma **frase curta** no presente (“A escrever testes em `test_venda.py`…”, “A actualizar `PAINEL_OPERACIONAL.md` após PC1…”).
   - **`etapas_pendentes`** — **array ordenado** de strings: fila **imediata** dos próximos passos (3–15 itens é um intervalo razoável; pode truncar com “+ N tarefas” na UI se necessário).
2. **Persistir** o ficheiro no **working copy** (gravar disco).
3. **Em seguida** executar a microtarefa (ferramentas, edições, testes).

**Quando concluir** uma microtarefa: remover ou marcar na fila (retirar o primeiro item de `etapas_pendentes` e refrescar `live_status` para a **seguinte** acção ou para “Parado — aguarda próximo passo / Diretor”).

**Sincronização com Git:**  
- Para o Diretor ver “ao vivo” na **mesma máquina** onde o ficheiro é actualizado (ex.: clone local + Streamlit local), basta **gravar** o JSON.  
- Para **outro dispositivo** ou **CI**, só há actualização após **`git push`** — o desenho assume **tempo real = ficheiro local actualizado**; o Painel continua a ser a prova **remota** nos PCs.

**Excepções:** não é obrigatório reescrever o JSON **entre** cada linha de código dentro do mesmo micro-passo; a granularidade é **por microtarefa** (unidade de trabalho que o Diretor conseguiria nomear em uma frase).

---

## 3. Evolução proposta de `status_demanda.json`

Campos **novos** (retrocompatíveis — leitores actuais ignoram chaves desconhecidas):

| Chave | Tipo | Obrigatório | Descrição |
|:---|:---|:---:|:---|
| `live_status` | `string` | não | Descrição **da acção exacta neste momento** (1–2 linhas de texto plano). Vazio ou `—` quando não há sessão activa da EQUIPE. |
| `etapas_pendentes` | `array` de `string` | não | Fila **ordenada** dos próximos passos imediatos. Lista vazia `[]` quando não há fila declarada. |
| `live_actualizado_iso` | `string` (ISO 8601) | recomendado | Momento da última actualização de telemetria pela EQUIPE; permite à UI mostrar “Actualizado há X s” e detectar **staleness**. |

**Campos existentes** (`demanda_id`, `fase_actual`, `fases_resumo`, `pc_foco`, etc.) **mantêm-se**; a Torre continua a representar **fase/PC**; o bloco **STATUS LIVE** acrescenta **granularidade fina**.

**Exemplo ilustrativo** (não aplicar até **PROSSIGA**):

```json
{
  "live_status": "A implementar STATUS LIVE em page_fluxo_gestao.py",
  "etapas_pendentes": [
    "Alargar test_governanca.py para novos campos",
    "pytest completo",
    "Actualizar PAINEL (PC2)",
    "Commit + push develop"
  ],
  "live_actualizado_iso": "2026-04-07T18:42:00"
}
```

---

## 4. UI Streamlit — [`page_fluxo_gestao.py`](../../../../src/ui/page_fluxo_gestao.py)

### 4.1 Bloco **STATUS LIVE** (topo, acima da Torre)

- **Título:** ex. “Telemetria ao vivo” ou “STATUS LIVE”.
- **Operação actual:** texto destacado (`live_status`); se vazio, mensagem neutra (“Sem actividade registada pela EQUIPE.”).
- **Indicador visual:** ícone ou componente que sugira **actividade** quando `live_status` não está vazio (ex.: spinner do Streamlit **apenas** quando houver texto non-empty — evitar spinner permanente a confundir).
- **Fila:** lista numerada ou bullets com `etapas_pendentes` (primeiros N itens, ex. 8, com “…” se maior).
- **Rodapé do bloco:** `live_actualizado_iso` legível (“Última actualização: …”) ou “—” se ausente.

### 4.2 Actualização automática da página (“quase real-time”)

| Opção | Prós | Contras |
|:---|:---|:---|
| **`streamlit-autorefresh`** (componente comunitário) | Simples; intervalo configurável (ex. 3–10 s). | Nova dependência em `requirements.txt`; revisar compatibilidade com versão Streamlit do projecto. |
| **`st.rerun` + `time.sleep` em loop** | Sem pacote extra. | **Não recomendado** — bloqueia ou complica o modelo de execução do Streamlit. |
| **Manual** | Zero risco. | Não cumpre “ao vivo”; só fallback. |

**Proposta:** após **PROSSIGA**, **avaliar** `streamlit-autorefresh` com intervalo **conservador** (ex. **5–15 s**) e **desactivar** ou intervalo alto quando `live_status` vazio **e** sem demanda activa (economia de CPU). Alternativa mínima: **botão “Actualizar estado”** + texto a explicar que com autorefresh a leitura é periódica.

**Segurança / robustez:** leitura só do JSON local; sem endpoints externos; falha de parse → mensagem de erro amigável (já existente na página).

### 4.3 Relação com a Torre

- **Ordem sugerida:** STATUS LIVE → Torre A–F → métricas → Diário resumo → restantes expanders.  
- A Torre **não** substitui `live_status`; **complementa** (macro vs micro).

---

## 5. Painel operacional (.md)

- **Sem mudança de papel:** continua actualizado nos **PCs**.  
- **Opcional (fase posterior):** uma linha no topo executivo a referir que a **telemetria fina** está na app — pode constar no `02` de implementação ou num PC de documentação.

---

## 6. Testes e governança

- **`tests/test_governanca.py`:** quando os campos existirem, validar tipos (`live_status` string, `etapas_pendentes` lista de strings, `live_actualizado_iso` formato opcional relaxado).  
- **`.cursorrules`:** acrescentar **uma** regra explícita: “Ao iniciar cada microtarefa visível ao Diretor, actualizar `live_status` + `etapas_pendentes` + `live_actualizado_iso` no JSON.”  
- **CADERNO_TESTES_MASTER / demanda E14:** plano de regressão + smoke “Fluxo e governança” com autorefresh ou botão.

---

## 7. Critérios de aceite (para a fase de implementação)

- [ ] EQUIPE documentada (Cursor rules + README demandas) a **preencher telemetria** antes de cada microtarefa relevante.  
- [ ] JSON com `live_status`, `etapas_pendentes`, `live_actualizado_iso` (quando implementado).  
- [ ] UI com bloco **STATUS LIVE** no topo; fila visível; última hora de actualização.  
- [ ] Mecanismo de refresco **periódico** (preferencial) ou **botão** + justificação se autorefresh for postergado.  
- [ ] `pytest` completo verde; Painel e PCs **inalterados em espírito** (histórico preservado).

---

## 8. Pedido ao Diretor

Validar este desenho com **CONFIRMO** ou **PROSSIGA** no chat. **Nenhuma** alteração a Python/JSON será aplicada até essa aprovação formal.
