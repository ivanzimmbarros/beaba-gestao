# 02 — Desenho funcional — E13 Ajustes de copy nos formulários

**Demanda:** `2026-04-07_E13_ajustes_copy_formularios`  
**Data:** 2026-04-07  
**Estado:** **Proposta — aguarda CONFIRMO / PROSSIGA do Diretor no Cursor.**

---

## Princípios

- **Só texto apresentado ao utilizador** (captions, `st.subheader`, `placeholder`, rótulos de `checkbox` / `radio` / `number_input`).  
- **Sem mudança** em `cadastrar_cliente`, `cadastrar_colaborador`, `cadastrar_*` catálogo, validadores, nem testes de domínio — excepto, se necessário, **uma** string de erro em `catalogo.py` para manter coerência com os novos rótulos de Âmbito (ver §3.3).

**Ficheiro principal:** [`src/app.py`](../../../../src/app.py).

---

## 1) Gestão de clientes — `_page_clientes()`

| # | Local | Texto actual | Texto proposto |
|:---:|:---|:---|:---|
| 1.1 | `st.caption` após o título do formulário | `Campos obrigatórios, exceto contactos de emergência. Número de contacto principal: 11 dígitos (DDD + número), único na base.` | `* - Campos obrigatórios` |
| 1.2 | `st.subheader` da morada | `Morada (estruturada)` | `Informações da Morada` |
| 1.3 | `st.caption` em «Contactos de emergência» | `Pode adicionar vários. Cada linha válida exige nome e número (11 dígitos).` | `Adicione os contactos por ordem de prioridade de comunicação` |

**Nota:** A legenda sob a morada (`Campos separados para pesquisas…`) **mantém-se** (não foi pedida alteração).

---

## 2) Gestão de colaboradores — `_page_colaboradores()`

| # | Local | Texto actual | Texto proposto |
|:---:|:---|:---|:---|
| 2.1 | `st.caption` imediato após `### Gestão de colaboradores` | Bloco completo sobre contacto exclusivo, repasse 0,01%–100%, data de inserção da linha… | **Remover** o `st.caption` (não substituir por outro texto, salvo o Diretor pedir legenda curta numa revisão futura). |
| 2.2 | `placeholder` do contacto | `11 dígitos, exclusivo` | `DDD + número (11 dígitos)` |
| 2.3 | `st.subheader` da morada | `Morada (estruturada)` | `Informações da Morada` |
| 2.4 | `st.caption` em «Serviços habilitados e repasse» | `Serviços ativos do catálogo. Cada linha tem data de **inserção da habilitação** (relatórios de desempenho).` | `Lista de serviços que o colaborador está apto a exercer` |
| 2.5 | Rótulo `st.date_input` por linha | `Inserção da linha *` | `Data de Ativação do serviço` |

**Nota:** Regras de unicidade de contacto, repasse e datas **inalteradas** no módulo `colaborador.py`.

---

## 3) Catálogo de serviços — `_page_catalogo()`

| # | Local | Texto actual | Texto proposto |
|:---:|:---|:---|:---|
| 3.1 | `st.caption` introdutório | `**E06:** Sessão, Produto, Coworking, **Pacote** e **Evento** — cadastro no catálogo; itens **Pacote** e **Evento** não aparecem nas habilitações de colaboradores.` | `Controle de todos os serviços prestados e disponíveis para oferta` |
| 3.2 | `st.checkbox` item ativo | `Item ativo (disponível para habilitações e vendas futuras)` | `Serviço Disponível (serviço apto para venda)` |
| 3.3 | Pacote — `st.number_input` duração por linha | `Duração (h) 0=catálogo` | `Duração (h)` — **manter** `min_value=0.0` e a legenda existente `Duração 0 = usar a duração definida no catálogo…` (o significado de `0` continua documentado logo abaixo). |
| 3.4 | Evento — `st.radio` «Âmbito *» — opção 1 | `Interno (membros e colaboradores BeaBa)` | `Interno (membros e colaboradores internos)` |
| 3.5 | Evento — mesma `radio` — opção 2 | `Com convidado (parcerias)` | `Com convidado (parcerias externas)` |

**Coerência UX (recomendado na implementação):** em [`src/modules/catalogo.py`](../../../../src/modules/catalogo.py), mensagem de validação que cite «parcerias» → alinhar a **«parcerias externas»** (apenas string, sem mudança de lógica).

**Nota técnica:** Os valores internos `evt_escopo` (`interno` / `convidado`) derivados de `startswith("Interno")` **mantêm-se** válidos com os novos textos.

---

## Critérios de aceite

- [ ] Todos os textos da tabela acima aplicados em `app.py` (e ajuste opcional de string em `catalogo.py`).  
- [ ] `python -m pytest tests/ -v` **sem regressões**.  
- [ ] Nenhuma alteração a regras de validação além de copy de mensagem de erro, se acordado.

---

## Pedido ao Diretor

Confirmar com **CONFIRMO** ou **PROSSIGA** no chat para a EQUIPE fechar **PC1** (`03`) e aplicar as alterações em código (PC seguintes conforme norma).
