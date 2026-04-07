# 01 — Demanda do Diretor (fonte: Cursor `@Files` → Analista)

**ID da demanda:** `2026-04-07_E13_ajustes_copy_formularios`  
**Data de registo pela EQUIPE:** 2026-04-07  
**Canal:** mensagem do Diretor no Cursor com **`@Files`**, persona **Analista**.

---

## Síntese do pedido

Ajustes de **texto de interface** (copy) em três áreas da aplicação Streamlit (`src/app.py`), **sem alterar regras de negócio, validações nem persistência**:

1. **Gestão de clientes** — legendas e título de secção de morada; texto dos contactos de emergência.  
2. **Gestão de colaboradores** — remover legenda longa do topo; placeholders e títulos; legenda dos serviços habilitados; rótulo da data da linha de serviço.  
3. **Catálogo de serviços** — legenda introdutória; checkbox de item ativo; rótulo de duração no **Pacote**; opções de **Âmbito** no **Evento**.

**Restrição explícita do Diretor:** seguir o **Fluxo oficial de governança**; **não implementar código** até **aprovação formal** (`CONFIRMO` / `PROSSIGA`) sobre o `02_desenho_funcional.md`.

---

## Próximo passo normativo

- **`02_desenho_funcional.md`** — mapa texto antigo → novo (ficheiros e linhas de referência).  
- **`03_confirmacao_diretor.md`** — após aprovação no chat.  
- Depois: PC1→PC2, alteração mínima em `app.py` (+ alinhamento opcional de mensagem em `catalogo.py`), `pytest`, encerramento.
