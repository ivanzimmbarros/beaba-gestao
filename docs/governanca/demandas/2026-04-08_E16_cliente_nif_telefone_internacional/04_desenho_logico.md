# 04 — Desenho lógico — E16 (Cliente: NIF, identificação internacional, telefone dinâmico, nascimento do filho)

**Demanda:** `2026-04-08_E16_cliente_nif_telefone_internacional`  
**Marco:** **E16**  
**Fase:** **B — Desenho lógico**  
**Autor:** EQUIPE (persona **Arquiteto**)  
**Data:** 2026-04-08  
**Base:** [`02_desenho_funcional.md`](02_desenho_funcional.md)  
**Pós-rollback:** código em `src/` reflecte legado (`validar_e_limpar_telefone` = 11 dígitos; sem `nif.py` / `telefone.py` no repo). Este documento fixa o **contrato** antes de nova implementação.

---

## 1. Contexto actual (linha de base)

| Área | Estado actual (pós-rollback) |
|:---|:---|
| **Telefone principal** | Coluna `clientes.whatsapp` (**TEXT UNIQUE NOT NULL**); domínio efectivo **11 dígitos** numéricos (`validators.validar_e_limpar_telefone`). |
| **NIF / documento** | **Ausente** no esquema `clientes`; cadastro não persiste identificação fiscal. |
| **Filhos** | `cliente_filhos`: `nome`, `idade_anos`, `sexo`; **sem** data de nascimento. |
| **Emergência** | `cliente_contatos_emergencia.telefone` — mesma convenção que o legado de telefone (a alinhar na implementação). |

---

## 2. Identificação fiscal — NIF Portugal (módulo 11)

### 2.1 Normalização de entrada

- Remover espaços e separadores comuns; para modo PT, usar **apenas dígitos** (9).
- Rejeitar comprimento ≠ 9 antes do algoritmo.

### 2.2 Regras de formato PT

- **Primeiro dígito** permitido: `1`, `2`, `3`, `5`, `6`, `8`, `9` (conjunto típico NIF contribuinte PT; alinhar a referência oficial BeaBa se houver anexo fiscal).
- **Dígitos 2–9:** numéricos.

### 2.3 Algoritmo dígito de controlo (módulo 11)

Para dígitos \(d_1 \ldots d_9\) (índice 1-based como string humana):

1. \(S = \sum_{i=1}^{8} d_i \times (10 - i)\).
2. \(r = S \bmod 11\).
3. Dígito de controlo esperado \(c\): se \(r < 2\) então \(c = 0\); senão \(c = 11 - r\).
4. Válido se \(d_9 = c\).

**Nota de implementação:** usar inteiros; rejeitar NIF com letras após normalização PT.

### 2.4 Apresentação

- Máscara visual opcional na UI: `999 999 999` (não altera armazenamento: **9 dígitos** em `TEXT`).

---

## 3. Identificação internacional

### 3.1 Modelo conceptual

- Um único campo de **valor** (`nif_ou_documento` / nome final alinhado ao Dev) e um indicador booleano persistido:
  - `identificacao_internacional INTEGER NOT NULL` com `CHECK (identificacao_internacional IN (0, 1))`.
  - `0` = regime **Portugal** (valor = 9 dígitos validados pelo módulo 11).
  - `1` = regime **internacional** (valor = texto livre validado).

### 3.2 Validação regime internacional

- Comprimento **3–40** caracteres **após** `strip`.
- Caracteres permitidos: letras (Unicode), dígitos, espaço, hífen, ponto, barra `/` — regex alinhada ao funcional (ex.: `[\w\s\-./]+` com bandeira Unicode).
- Recusar string vazia ou só espaços.

### 3.3 Invariantes

- Se `identificacao_internacional = 0`: valor normalizado = **exatamente 9 dígitos** e passa `validar_nif_pt`.
- Se `identificacao_internacional = 1`: valor = texto validado; **não** aplicar módulo 11.

### 3.4 Migração de dados

- Clientes existentes **sem** colunas novas: script de migração em `create_tables` / passo dedicado:
  - Acrescentar colunas com **DEFAULT** seguro (ex.: `identificacao_internacional = 0` e placeholder fiscal **inadmissível** para novo registo) **ou** `NULL` permitido **apenas** até backoffice marcar — **recomendação:** `nif_ou_documento TEXT` **NULL** para linhas antigas; UI de cadastro **novo** exige preenchimento; relatório/listagem pode mostrar «Pendente» até E16.1 se o negócio exigir 100% obrigatório retroativo (fora do mínimo E16).

---

## 4. Telefone dinâmico (E.164)

### 4.1 Biblioteca

- **`phonenumbers`** (libphonenumber): parse por **região ISO3166-1 alpha-2** + número **nacional** (sem prefixo `+` na caixa «nacional»).

### 4.2 Parâmetros de entrada (UI → domínio)

- **Tipo de linha:** `movel` | `fixo` (mapeamento a partir de rádio Streamlit «Telemóvel» / «Fixo»).
- **País:** ISO2 + indicativo (lista dinâmica com pesquisa por nome, ISO2 ou prefixo).
- **Número nacional:** apenas dígitos relevantes (strip não-dígitos na normalização).

### 4.3 Regras de validação

- `parse(nacional, iso2)` com região default = ISO2 seleccionado.
- `is_valid_number` obrigatório.
- **Telemóvel:** tipo deve ser `MOBILE` ou `FIXED_LINE_OR_MOBILE`; rejeitar se for só fixo.
- **Fixo:** rejeitar se tipo for claramente **só** `MOBILE` (mensagem a orientar troca de tipo).

### 4.4 Saída e persistência

- Formato único na BD: **E.164** (ex.: `+351912345678`).
- Coluna existente **`clientes.whatsapp`**: manter **nome físico** por compatibilidade; semântica passa a «contacto principal E.164» (documentar em comentário de código + PAINEL/MODELO na Fase D se necessário).
- **UNIQUE:** manter unicidade sobre o **E.164** canónico (duplicados = mesmo erro de negócio que hoje).

### 4.5 Compatibilidade legado (11 dígitos)

- Função de transição **`normalizar_telefone_legado_ou_e164(valor: str)`**:
  - Se entrada já começa por `+` e `phonenumbers` valida → usar E.164 resultante.
  - Senão, se após `\D` há **11 dígitos** e política BeaBa = **BR** → interpretar como nacional BR com região `BR` (alinhado a testes/sujeira histórica).
  - Senão, regras adicionais mínimas documentadas no código (ex.: 9 dígitos PT sem `+` com região `PT`) **apenas** onde o produto precisar de importação de dados antigos.
- **Cadastro novo:** só fluxo **dinâmico** (país + nacional + tipo); não depender do atalho de 11 dígitos excepto migração/testes.

### 4.6 Contactos de emergência

- Mesma normalização **E.164** ao gravar em `cliente_contatos_emergencia.telefone`.
- UI: reutilizar grupo de widgets com **prefixo de chaves** distinto (`session_state`) por linha (ex.: `emerg_{ordem}_`).

### 4.7 Módulos e UI (pacotes)

| Artefacto | Responsabilidade |
|:---|:---|
| `country_dial_codes.py` | Lista `(iso2, dial, nome)`; função de filtro por texto; rótulos para `selectbox`. |
| `telefone.py` | `normalizar_telefone_e164`, `normalizar_telefone_legado_ou_e164`. |
| `telefone_widgets.py` | `render_grupo_telefone(st, prefix=..., label=...)`; `ler_e164_de_widgets(prefix)`. |

---

## 5. Filhos — data de nascimento opcional

### 5.1 Esquema

- Nova coluna: **`cliente_filhos.data_nascimento TEXT NULL`** — formato **`YYYY-MM-DD`** quando preenchida.

### 5.2 Validação

- Se **NULL** ou string vazia: válido (opcional).
- Se preenchida: `parse_data_iso` (já existente em `validators`) — data **não futura**; opcionalmente rejeitar data &lt; hoje − 120 anos.

### 5.3 Coerência com `idade_anos`

- **Se só `data_nascimento`:** na gravação, calcular `idade_anos = floor(anos entre data_nascimento e hoje)` e persistir ambos (idade derivada).
- **Se só `idade_anos`:** comportamento actual; `data_nascimento` permanece NULL.
- **Se ambos:** **priorizar data**: recalcular `idade_anos` a partir da data e **substituir** o valor de idade enviado pela UI (ou exigir match ±1 ano — **escolha:** priorizar data para evitar bloqueio de UX; registar em comentário).

### 5.4 API Python (`cliente` module)

- Expandir tipo de filho para tupla **3 ou 4** elementos: `(nome, idade_anos, sexo)` ou `(nome, idade_anos, sexo, data_nasc_iso_opcional)`.
- Inserção `INSERT` inclui `data_nascimento` quando não NULL.

---

## 6. Fluxo de cadastro / edição (orquestração)

1. Ler UI: flag internacional, texto identificação, grupo telefone principal, filhos (+ datas opcionais), emergências.
2. `normalizar_nif_armazenamento(texto, documento_identificacao_internacional=flag)` → `(ok, msg, valor_persistido)`.
3. Telefone principal: `ler_e164_de_widgets` ou equivalente → `(ok, e164, msg)`.
4. Para cada emergência: normalizar para E.164 (mesma API).
5. Filhos: para cada linha, aplicar regra §5; falha rápida com mensagem PT.
6. Transacção única: `INSERT`/`UPDATE` cliente, filhos, emergências (padrão actual mantido).

---

## 7. Testes (âncoras para CADERNO / pytest)

- NIF PT: casos válidos / inválidos (dígito errado, primeiro dígito proibido, &lt;9 / &gt;9 dígitos).
- Internacional: limite 3–40, caracteres proibidos, trim.
- Telefone: pelo menos um país PT (movel/fixe), rejeição de tipo errado, E.164 estável.
- Legado: 11 dígitos → `+55…` (se política mantida).
- Filho: só data → idade derivada; data futura → erro.
- UNIQUE: dois clientes mesmo E.164 → segundo cadastro falha.

---

## 8. Critérios para fecho da Fase B (PC3)

- [ ] **Analista** produz [`05_validacao_analista_desenho_logico.md`](05_validacao_analista_desenho_logico.md) com concordância ou ajustes.
- [ ] **Commit + push** `develop` com `01`–`05` conforme fluxo.
- [ ] **PC4:** actualização do **Painel** operacional (linha E16 / fase).

---

## 9. O que fica **fora** do E16 (explícito)

- Renomear coluna `whatsapp` na BD (custo de migração); apenas semântica e documentação.
- Validação fiscal de **outros** países além do modo «texto internacional».
- SMS/WhatsApp Business API.
