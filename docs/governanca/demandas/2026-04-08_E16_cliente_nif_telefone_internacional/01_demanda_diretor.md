# 01 — Demanda do Diretor (fonte: Cursor `@Files` → Analista / EQUIPE)

**ID da demanda:** `2026-04-08_E16_cliente_nif_telefone_internacional`  
**Marco de produto:** **E16**  
**Data de registo pela EQUIPE:** 2026-04-08  
**Canal:** **`@Files`**, **Analista**, **EQUIPE**.

---

## Síntese do pedido

O **Diretor** exige reforço do módulo **Clientes** quanto a:

1. **Identificação fiscal:** NIF português com validação **módulo 11** e opção de **documento internacional** (texto estruturado, 3–40 caracteres), com armazenamento coerente na base de dados.
2. **Contacto telefónico:** normalização para **E.164** com biblioteca **`phonenumbers`**, escolha de **país / indicativo** (lista pesquisável), distinção **telemóvel vs fixo**, e compatibilidade com entradas legadas onde aplicável.
3. **UI reutilizável:** widgets Streamlit partilháveis (`telefone_widgets`) para captura consistente em formulários.
4. **Validações transversais:** apoio em módulos dedicados (e-mail, código postal PT, datas ISO) integrados no fluxo de cadastro/edição de cliente.

**Restrição (Fase A):** até **aprovação formal** do desenho funcional no chat, a EQUIPE limita-se a **`01`**, **`02`** e registo de **`03`** após **CONFIRMO** / **PROSSIGA** — sem tratar Fase B–F como fechada sem os PCs normativos.

---

## Próximo passo

- **`02_desenho_funcional.md`** — critérios de aceite e mapa técnico.  
- Após selo do Diretor: **`03`**, actualização de **`status_demanda.json`** / Painel (PC1–PC2), depois **Fase B** (desenho lógico, PC3–PC4).
