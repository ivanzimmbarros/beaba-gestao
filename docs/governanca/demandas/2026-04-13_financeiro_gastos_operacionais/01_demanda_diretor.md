# Demanda — Página Financeiro (sector 1. Gastos Operacionais)

**ID:** `2026-04-13_financeiro_gastos_operacionais`  
**Canal:** @Files / EQUIPE  
**Data (ISO):** 2026-04-13  

## Resumo

Nova página **Financeiro** na shell Streamlit, com o primeiro sector **«1. Gastos Operacionais»** (sem subtítulo complementar), expander **«Manutenção das Categorias de Gastos»** e subárea de cadastro/filtros/tabela conforme proposta funcional.

## Decisões do Diretor (chat)

- Terminologia canónica: **Natureza** (descartado «Classe»).
- Imutabilidade: **desactivação lógica** (`ativo=0`) + novo registo quando existem lançamentos em `financeiro_gasto_lancamentos`; sem lançamentos, UPDATE in-place.
- **Limpar Campos:** apenas o formulário de cadastro (três linhas); filtros e tabela mantêm-se.

## Referências

- `.cursorrules` (Constituição visual + governança).
- `Template Master - Design Grafico.txt`.
