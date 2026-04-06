# Dossiers de demanda (rastreio do fluxo SUCESSO / FALHA)

Para **cada** demanda em curso ou encerrada, criar uma pasta:

`docs/governanca/demandas/<ID_DEMANDA>/`

Sugestão de `ID_DEMANDA`: `YYYY-MM-DD_slug_curto` (ex.: `2026-04-06_E10_estoque`).

## Ficheiros mínimos (adaptar aos PCs)

| Ficheiro | Conteúdo |
|:---|:---|
| `01_demanda_diretor.md` | Texto ou resumo da demanda original; data. |
| `02_desenho_funcional.md` | Desenho funcional; versão. |
| `03_confirmacao_diretor.md` | **Selo Diretor** — texto explícito de confirmação formal, data, nome. |
| `04_desenho_logico.md` | Desenho lógico (Arquiteto). |
| `05_validacao_analista_desenho_logico.md` | **Selo Analista** sobre desenho lógico. |
| `06_parecer_arquiteto_codigo.md` | Parecer de avaliação do código (Arquiteto). |
| `07_parecer_analista_codigo.md` | Parecer de avaliação do Analista sobre código. |
| `08_plano_testes_referencia.md` | Referência ou diff face a `docs/CADERNO_TESTES_MASTER.md`. |
| `09_parecer_final_qa.md` | Resultados massivos + **selo QA**. |
| `99_encerramento.md` | Informação ao Diretor; data; referência ao parecer QA (PC13). |

Em caso de **FALHA**, acrescentar `FALHA_<data>_<actor>.md` com parecer negativo completo.
