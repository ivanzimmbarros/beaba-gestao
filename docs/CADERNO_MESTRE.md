# Caderno Mestre — BeaBa Gestão (V11.0 · Identidade integrada)

**Projeto:** Ecossistema BeaBa Gestão  
**Referência visual:** [beabamaterno.com](https://beabamaterno.com)  
**Status:** Revalidado — base estética definitiva para homologação técnica  
**Versão do desenho:** V11.0  

---

## 1. Identidade visual e design system (fiel ao site)

O sistema replica a atmosfera **clean, soft e profissional** do website oficial.

### 1.1 Paleta de cores (extraída do site)

| Token | Hex | Uso |
|:---|:---|:---|
| Verde BeaBa (primária) | `#97C9C5` | Logótipo, botões, blocos de destaque |
| Branco de fundo | `#FFFFFF` | Leitura e inputs |
| Cinza de contraste | `#F7F7F7` | Cards e separação de secções |
| Texto principal | `#545454` | Corpo (evitar preto puro) |
| Destaque suave | `#E2F1F0` | Hover e seleções |

### 1.2 Tipografia (hierarquia do site)

- **Títulos (H1–H3):** serifada — *Playfair Display* ou *Lora* (confiança, tradição, cuidado).
- **Corpo e inputs:** sans-serif — *Montserrat* ou *Open Sans* (legibilidade, mobile-first).

### 1.3 Elementos gráficos e distribuição

- **Border radius:** `20px` em botões e cards.
- **Sombras:** muito leves e difusas — `rgba(0, 0, 0, 0.05)`.
- **Espaçamento:** padding generoso; interface com “respiro”, alinhada ao acolhimento da marca.

---

## 2. Arquitetura de navegação (estrutura híbrida)

### 2.1 Menu inicial — dashboard em blocos

A Home não é apenas uma lista: blocos com cores suaves, alinhados ao site.

| Bloco | Cor de fundo | Destino funcional |
|:---:|:---|:---|
| 1 | Verde BeaBa | Gestão de clientes |
| 2 | Cinza suave | Gestão de colaboradoras |
| 3 | Verde BeaBa | Catálogo de serviços |
| 4 | Cinza suave | Painel de vendas |

**Mobile-first:** blocos empilham de forma elegante em viewport vertical.

### 2.2 Navegação de retorno

- **Voltar ao início:** canto superior esquerdo; seta fina + texto em sans-serif.
- **Breadcrumbs:** linha sutil (ex.: `Home > Clientes > Novo cadastro`).

**Regra:** em **100%** das vistas internas, o controlo de retorno deve estar presente.

---

## 3. Regras funcionais (mantidas e blindadas)

1. **Número de contacto (principal):** **11 dígitos** numéricos (PT); **unicidade** na base (coluna técnica `whatsapp`). Na UI o rótulo é **Número de contacto**.
2. **Cadastro de cliente (V11.0+):** **morada estruturada** (rua, número, complemento opcional, código postal PT **XXXX-XXX** validado, concelho, **freguesia obrigatória**, distrito opcional, país); email, sexo e composição familiar obrigatórios conforme fluxo; **filhos** com **nome**, idade em **anos completos** e sexo por filho; se **Feminino** e grávida, **data estimada de parto** obrigatória; **contactos de emergência** opcionais, em lista dinâmica — cada linha preenchida exige **nome + 11 dígitos**; campo **Observações** livre ao final (opcional).
3. **Catálogo:** distinção entre **Sessão**, **Tempo**, **Pacote** e **Produto**.
4. **Financeiro:** gatilho de exceção para percentuais manuais na venda; valores em **centavos** (inteiro).

---

## 4. Critérios de aceitação (selo “validado pelo negócio”)

1. **Mimetismo visual:** cores e tipografia indistinguíveis de um print do site, quando comparados lado a lado.
2. **Mobile-first:** grid responsivo na Home (empilhamento limpo).
3. **Simplicidade:** cadastro de cliente tão suave quanto navegar em “Serviços” no site.
4. **Consistência:** botão de retorno em todas as telas internas, sem exceção.

---

## 5. Decisão do diretor (travamento do design)

Esta revalidação (Verde BeaBa `#97C9C5`, serifas nos títulos, layout clean) substitui propostas anteriores que não refletiam a identidade real da marca (ex.: champagne/ouro).  
**OK do diretor** consolida este documento como referência única para evolução de UI até nova revisão formal.

---

*Documento vivo: alterações de escopo visual ou funcional devem refletir-se aqui e no `CONTROLE_DE_VOO.md`.*
