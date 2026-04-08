# 02 — Desenho funcional — E16 Cliente: NIF, documento internacional e telefone E.164

**Demanda:** `2026-04-08_E16_cliente_nif_telefone_internacional`  
**Marco:** **E16**  
**Data:** 2026-04-08  
**Estado:** **Implementado** — ver [`99_encerramento.md`](99_encerramento.md).

---

## 1. Objectivo

| Área | Meta |
|:---|:---|
| **NIF PT** | Validar 9 dígitos, primeiro dígito permitido e **dígito de controlo módulo 11**; opcional máscara visual `999 999 999`. |
| **Doc. internacional** | Quando o utilizador indica documento não-PT: campo obrigatório, 3–40 caracteres, padrão alfanumérico seguro (espaços, hífen, `./`). |
| **Telefone** | Normalizar para **E.164**; país por **ISO2** + indicativo; validar **movel** vs **fixo** conforme tipo de linha reportado pela lib. |
| **UX** | `render_grupo_telefone` + `ler_e164_de_widgets` para reutilização; filtro de país por texto (nome, ISO2, indicativo). |
| **Integração** | `cliente.cadastrar_cliente` (e fluxos afins) consomem `normalizar_nif_armazenamento` e normalização de telefone; mensagens de erro claras em PT. |

**Dependência:** `phonenumbers` (já prevista em `requirements.txt`).

---

## 2. Comportamento esperado (negócio)

- **Alternância NIF PT / internacional:** um único campo de “identificação” com flag explícita no UI; backend recusa combinações inválidas com mensagem única por caso.
- **WhatsApp / principal:** armazenar **E.164** na coluna existente (ex. `whatsapp`), mantendo compatibilidade com testes que usam formato legado quando a função de migração o aceitar.
- **Emergência / listas:** mesma semântica de normalização onde o desenho lógico (Fase B) fixar o contrato por coluna.

---

## 3. Mapa técnico (alvo de implementação)

| Componente | Função |
|:---|:---|
| [`src/modules/nif.py`](../../../../src/modules/nif.py) | Validação PT, documento internacional, `normalizar_nif_armazenamento`. |
| [`src/modules/telefone.py`](../../../../src/modules/telefone.py) | `normalizar_telefone_e164`, legado → E.164 onde aplicável. |
| [`src/modules/country_dial_codes.py`](../../../../src/modules/country_dial_codes.py) | Lista e pesquisa de países / indicativos. |
| [`src/ui/telefone_widgets.py`](../../../../src/ui/telefone_widgets.py) | Widgets Streamlit e leitura para E.164. |
| [`src/modules/validators.py`](../../../../src/modules/validators.py) | E-mail, código postal, datas. |
| [`src/modules/cliente.py`](../../../../src/modules/cliente.py) | Orquestração no cadastro/edição. |

*(Caminhos relativos à raiz do repositório.)*

---

## 4. Critérios de aceite (implementação — Fases C–E)

- [x] NIF PT inválido **não** grava; doc. internacional fora do padrão **não** grava.  
- [x] Telefone: país + nacional + tipo de linha → E.164 válido ou erro explicável.  
- [x] UI: grupo telefone reutilizável sem duplicar lógica nos ecrãs principais.  
- [x] `pytest` verde; CI **Validador Maestro** e **Fluxo oficial** sem regressão.  
- [x] `CADERNO_TESTES_MASTER` actualizado no passo normativo (PC7 / Dev).

---

## 5. Pedido ao Diretor *(cumprido)*

Aprovação formal recebida — seguir para **Fase B** (Arquiteto: `04_desenho_logico.md`, PC3–PC4).
