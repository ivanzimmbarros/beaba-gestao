# Dossiers de demanda — geração pela **EQUIPE** (@Files)

**Mandatório:** estas pastas **não** são criadas pelo Diretor. O Diretor envia a demanda via **Cursor** com **`@Files` → Analista**. A **EQUIPE** (agente) **cria** `docs/governanca/demandas/<ID_DEMANDA>/`, preenche os ficheiros, faz **commit** e **push**, e **actualiza** o Painel e `status_demanda.json`.

Sugestão de `ID_DEMANDA`: `YYYY-MM-DD_slug_curto` (ex.: `2026-04-06_E10_estoque`).

## Ficheiros (todos produzidos pela EQUIPE, salvo texto citado do chat do Diretor)

| Ficheiro | Conteúdo |
|:---|:---|
| `01_demanda_diretor.md` | Transcrição ou síntese **datada** do pedido no Cursor (`@Files`). |
| `02_desenho_funcional.md` | Desenho funcional. |
| `03_confirmacao_diretor.md` | Registo da **aprovação** do Diretor **no chat** (data, sumário ou citação). |
| `04_desenho_logico.md` | Desenho lógico (Arquiteto). |
| `05_validacao_analista_desenho_logico.md` | Selo Analista sobre desenho lógico. |
| `06_parecer_arquiteto_codigo.md` | Parecer técnico do código. |
| `07_parecer_analista_codigo.md` | Parecer de negócio sobre código. |
| `08_plano_testes_referencia.md` | Ligação ao `CADERNO_TESTES_MASTER` / delta da demanda. |
| `09_parecer_final_qa.md` | Testes massivos + selo QA. |
| `99_encerramento.md` | Conclusão informada ao Diretor no chat + referência ao parecer QA. |

Opcional: `00_indice.md` — linha temporal dos PCs.

Em **FALHA:** `FALHA_<data>_<actor>.md` (pela EQUIPE, com detalhe completo).
