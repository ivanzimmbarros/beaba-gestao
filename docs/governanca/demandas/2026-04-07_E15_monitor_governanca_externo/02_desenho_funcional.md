# 02 — Desenho funcional — E15 Monitor de governança (aplicação externa)

**Demanda:** `2026-04-07_E15_monitor_governanca_externo`  
**Data:** 2026-04-07  
**Estado:** **Proposta — aguarda CONFIRMO / PROSSIGA do Diretor.**

---

## 1. Objectivo e princípios

| | App de Gestão (`src/app.py`) | Monitor de Voo (`monitor_governanca.py`) |
|:---|:---|:---|
| **Público** | Operação diária: clientes, vendas, agenda, relatórios. | **Só** acompanhamento de governança / telemetria. |
| **Uso típico** | Ecrã principal. | **Segundo monitor** / janela dedicada. |
| **Navegação** | Multi-página com Início. | **Uma única página** (scroll); sem menu da app de gestão. |

**Fonte de dados:** única — [`docs/governanca/status_demanda.json`](../../status_demanda.json) (caminho relativo à **raiz do repositório**).

**Painel .md:** continua a ser actualizado nos **PCs**; o monitor e a app de gestão **leem** o mesmo JSON.

---

## 2. Interface do monitor externo (wireframe lógico)

**Arranque:** `streamlit run monitor_governanca.py` executado na **raiz do clone** (para que `docs/governanca/status_demanda.json` resolva correctamente).

### 2.1 Configuração global

- `st.set_page_config(page_title="Monitor de Voo — Governança BeaBa", layout="wide", initial_sidebar_state="collapsed")`.
- Cabeçalho fixo visual: título **«Monitor de Voo»** + subtítulo curto («Telemetria e fluxo oficial — leitura de `status_demanda.json`»).
- **Sem** botão «Voltar ao Início» da app de gestão; **sem** breadcrumbs da shell BeaBa.

### 2.2 Actualização contínua (obrigatória)

- **`streamlit_autorefresh.st_autorefresh`** sempre activo no script do monitor (intervalo sugerido **8–10 s**, alinhado ao E14 ou ligeiramente mais frequente para segundo ecrã).
- **Sem** opção de desligar o autorefresh por defeito (exigência «obrigatório»); opcional: nota em `st.caption` a explicar que o utilizador pode fechar a aba para parar refreshes.
- Botão **«Actualizar agora»** (`st.rerun`) pode manter-se como reforço.

### 2.3 Blocos verticais (ordem sugerida)

1. **STATUS LIVE (E14)**  
   - Mesmo comportamento semântico que hoje: `live_status`, fila `etapas_pendentes` (com limite de linhas + «…»), `live_actualizado_iso`.  
   - Destaque visual maior (ex.: `st.container` com borda via `st.markdown` + HTML mínimo **ou** `st.info` / métricas) para leitura à distância.

2. **Alerta de percurso FALHA**  
   - Se `percurso == "correccao"` ou `falha` preenchido — banner de aviso (igual à lógica actual).

3. **Torre de Controle (A–F)**  
   - Grelha de 6 colunas com ícones 🟢🔵⚪🟠; mesma derivação de `fases_resumo` / defaults.

4. **Linha de contexto**  
   - `fase_governanca`, `pc_foco` (quando aplicável).

5. **Métricas em linha**  
   - Demanda, Fase/passos, Responsável, Último marco (`ultima_entrega_marco`) — `st.columns(4)` em `wide`.

6. **Diário de Bordo (resumo)**  
   - Lista a partir de `diario_bordo_resumo`.

7. **Pendente**  
   - Texto integral do campo `pendente`.

8. **Expander «Pontos de controlo concluídos»**  
9. **Expander «Falha / fluxo reverso»**  
10. **Expander «JSON completo»** (auditoria)

11. **Rodapé**  
    - Links textuais: `PAINEL_OPERACIONAL.md`, norma `FLUXO_SUCESSO_E_FALHA.md`, pasta `demandas/`.

### 2.4 Diferenças face à vista actual na app

- **Removidos:** integração com `session_state.page`, `_render_back_and_breadcrumb`, botões do dashboard principal.  
- **Acrescidos:** título e identidade claros de **monitor**; **wide** por defeito; autorefresh **sempre** (não depende de checkbox).

---

## 3. Migração técnica (plano pós-aprovação)

| Passo | Acção |
|:---|:---|
| M1 | Criar **`monitor_governanca.py`** na raiz com funções auxiliares copiadas/adaptadas de `page_fluxo_gestao.py` (`_repo_root` → `Path(__file__).resolve().parent`, `carregar_status_demanda`, `_fases_para_exibir`, `_render_status_live` ou equivalente unificado). |
| M2 | Implementar `main` / `if __name__ == "__main__"` com `streamlit run` entry (ficheiro único é suficiente para Streamlit). |
| M3 | Remover de [`src/app.py`](../../../../src/app.py): `from src.ui.page_fluxo_gestao import …`, botão «Fluxo e governança…», ramo `elif page == "fluxo_gestao":`. |
| M4 | **Eliminar** [`src/ui/page_fluxo_gestao.py`](../../../../src/ui/page_fluxo_gestao.py) após migração completa (evitar duplicação e imports mortos). |
| M5 | Actualizar referências em documentação: **PAINEL**, **CONTROLE**, **CADERNO**, **README demandas**, **99** de E12/E14 se citarem explicitamente só `page_fluxo_gestao` — passar a **«Monitor de Voo»** + `monitor_governanca.py`. |
| M6 | **`.cursorrules`:** onde mencionar «página Fluxo e governança», referir **monitor** `monitor_governanca.py` como superfície de telemetria; regra **6** (E14) mantém-se — JSON continua a ser actualizado antes das microtarefas. |
| M7 | **Testes:** ajustar `test_governanca` se necessário; opcional smoke: ficheiro `monitor_governanca.py` existe e importa sem erro (sem subir servidor). |
| M8 | **`requirements.txt`:** já contém `streamlit-autorefresh`; nenhuma alteração obrigatória. |

**Duplicação de código:** na primeira entrega, **duplicar** helpers no monitor é aceitável; **opcional** futura: extrair `src/ui/governanca_dashboard.py` partilhado — **fora do âmbito** deste desenho para manter o diff focado.

---

## 4. `PAINEL_OPERACIONAL.md` (actualização prevista)

Acrescentar no **topo executivo** (após Torre ou em «Estado actual») uma subsecção **«Dois pontos de acesso»**:

| Ponto de acesso | Comando / local | Função |
|:---|:---|:---|
| **App de Gestão** | `streamlit run app.py` (ou entrada actual do projecto) | Operação: clientes, colaboradores, catálogo, vendas, agendamentos, dashboards. |
| **Monitor de Voo** | `streamlit run monitor_governanca.py` (na **raiz** do repo) | Telemetria E14, Torre, Diário, JSON — **stand-alone** para segundo ecrã. |

Referência cruzada ao dossier **E15** e ao `99_encerramento` após implementação.

---

## 5. Critérios de aceite (implementação)

- [ ] `monitor_governanca.py` na raiz; `layout="wide"`; `st_autorefresh` **sempre** activo.  
- [ ] Conteúdo equivalente ao actual `page_fluxo_gestao` (STATUS LIVE, Torre, Diário, métricas, expanders, JSON).  
- [ ] App principal **sem** página Fluxo e governança; ficheiro `page_fluxo_gestao.py` **removido**.  
- [ ] PAINEL actualizado com tabela dos dois acessos.  
- [ ] `pytest` completo verde; CI **Validador Maestro** e **FLUXO OFICIAL** sem regressão.

---

## 6. Pedido ao Diretor

Confirmar com **CONFIRMO** ou **PROSSIGA** no chat para a EQUIPE executar a migração (Fases B–F / PCs conforme norma).
