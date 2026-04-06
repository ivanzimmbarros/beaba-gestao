# 01 — Demanda do Diretor (fonte: Cursor `@Files` → Analista)

**ID da demanda:** `2026-04-06_E11_pre_venda_agenda`  
**Data de registo pela EQUIPE:** 2026-04-06  
**Canal:** mensagem do Diretor no Cursor com **`@Files`**, persona **Analista**.

---

## Síntese do pedido

Foi confirmado no negócio que a **confirmação das vendas** pode ocorrer em **dois momentos distintos** na intersecção **Vendas × Agendamentos**:

1. **Cenário A — Pagamento no dia do atendimento:** primeiro é feito o **agendamento**; no **dia do atendimento** é feita a **concretização do pagamento** (a venda “fecha” nesse momento, e não necessariamente antes da marcação).

2. **Cenário B — Upsell no dia de pagamento:** num dia em que já existe um **evento/sessão previamente agendado** e se efectua o **pagamento** associado, o cliente pode **solicitar e confirmar serviços adicionais** (nova venda ou linhas adicionais ligadas operacionalmente à mesma visita).

O Diretor pede que a **Analista (EQUIPE)** analise **todo o fluxo, telas, funções e estrutura** actuais e **proponha uma solução** para que seja possível construir o cenário em que a **venda ocorre após o agendamento**, permitindo **agendamentos registados sem uma venda consumada por detrás** — equivalente a uma **expectativa de venda** / **pré-venda** — e que o fluxo obedecer ao **controlo mandatório de evolução** até **validação formal** (desenho funcional + confirmação do Diretor).

---

## Confirmações de negócio já assumidas na demanda

- Existem **dois timing** de venda relativamente ao agendamento (A e B acima).
- É desejável suportar **compromissos de agenda** sem venda finalizada no momento da marcação.

---

## Próximo passo normativo (fluxo SUCESSO)

- **`02_desenho_funcional.md`** — proposta de solução para validação.  
- **`03_confirmacao_diretor.md`** — preenchido após **confirmação formal** do Diretor no chat (ex.: «CONFIRMO», «PROSSIGA»).
