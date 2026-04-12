# Épico 22 — Redesign visual global «Verde Sereno»

**ID:** `2026-04-10_E22_redesign_visual_verde_sereno`  
**Fase 0 (actual):** Análise, governança, motor de tema e plano faseado — **sem** «mata-tabelas» nas páginas até **OK FORMAL** do Diretor por fase.

## Pedidos do Diretor (síntese)

| Área | Objectivo |
|------|-----------|
| Menu / shell | Fundo acolhedor, navegação fluida |
| Clientes, Colaboradores, Catálogo, Agendamentos | Eliminar tabelas intermináveis → **cards** em grelha |
| Painel de Vendas | Semáforo em **card**; itens como **comanda** |
| Colaboradores | Cards estilo **perfil** (ícones especialidade / contacto) |
| Catálogo | **Vitrine / grid** com preço e descrição |
| Dashboards / Relatórios | Coerência cromática e legibilidade (fases posteriores) |

## Reaproveitamento da busca (sem duplicar código)

- **Já implementado (E21):** `src/ui/widgets/cliente_search.py` → `render_cliente_search_widget(key_prefix=...)`.
- **Clientes:** `key_prefix="cli_busca"`.
- **Vendas:** `key_prefix="vnd_busca"` + lógica de resultado em `page_vendas.py` (uma só implementação de UI).
- **Colaboradores:** hoje replica layout semelhante; **Fase recomendada:** substituir o bloco de busca por **a mesma** `render_cliente_search_widget(key_prefix="col_busca")` e manter apenas o *handler* específico (`buscar_colaboradores_*`, carregar ficha). Assim, labels HTML, calendários e botão «Procurar» ficam num único sítio.

## Faseamento (1 módulo por fase — inviolável)

| Fase | Âmbito | Entregas | Após OK Diretor |
|------|--------|----------|-----------------|
| **0** | Governança + tema | `styles_theme.py`, `get_beaba_css()`, integração em `app.py`, JSON + monitor, este plano | OK para Fase 1 |
| **1** | Shell / `app.py` + Home | Cards de menu, breadcrumbs, remates do tema no hub | pytest + smoke |
| **2** | **Clientes** | Lista resultados / saldo em cards; retirar `st.dataframe` onde aplicável | pytest `test_cliente` |
| **3** | **Colaboradores** | Busca via widget partilhado; resultados em cards perfil | pytest `test_colaborador` |
| **4** | **Catálogo** | Vitrine grid; seleção mantém lógica actual de `session_state` | pytest `test_catalogo` |
| **5** | **Agendamentos** | Calendário + lista filtrada em cards (sem tabela infinita) | pytest `test_agendamento` |
| **6** | **Vendas** | Card semáforo; comanda nos itens | pytest `test_venda` |
| **7** | **Dashboards** | Tokens de gráficos alinhados ao Verde Sereno | testes dashboards se existirem |
| **8** | **Relatórios** | Mesma linha visual | testes relatórios |
| **Fecho** | QA massivo | `pytest tests/`, `python tests/e2e_stress_test.py` (≥1000 iterações), `tests/last_stress_report.txt` sem bloqueios; backup/restore conforme E17 | Encerramento épico |

## Nota sobre `src/pages/`

O projecto usa **`src/ui/page_*.py`** e **`src/app.py`** como entrada — não existe `src/pages/`. O fluxo acordado é: **`src/app.py`** chama `inject_beaba_verde_sereno()` imediatamente após `set_page_config` / tema base.

## Qualidade contínua

- Cada fase: actualizar testes afectados e, se tocar em dados críticos, rever backups/workflows (norma E17 / `protocolo_fortaleza` no JSON).
- **Última actividade do épico:** bateria E2E massiva + evidências em `last_stress_report.txt`.
