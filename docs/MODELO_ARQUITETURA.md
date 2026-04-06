# 🏗️ MODELO DE ARQUITETURA - BEABA GESTÃO (V8.0)

## 📁 ESTRUTURA DE PASTAS OBRIGATÓRIA
- `/src`: Código-fonte da aplicação (Lógica, UI, Utils).
  - `/src/app.py`: Shell Streamlit (tema V11, navegação e páginas).
  - `/src/ui`: Tokens visuais, estilos compartilhados e páginas Streamlit extensas (ex.: `page_vendas.py`, `page_dashboards.py`).
  - `/src/modules`: Domínio (ex.: `cliente`, `colaborador`, `validators`, `constants`).
  - `/src/database`: Conexão e esquema.
- `/data`: Scripts de migração, Schema SQL e Banco de Dados (SQLite).
- `/tests`: Scripts de teste unitário e de integração para o QA.
- `/docs`: Documentação técnica, Caderno Mestre e Diagramas.

## 🛢️ PADRÕES DE BANCO DE DADOS (SQL)
1. **Nomenclatura:** Tabelas em `snake_case` e no plural (ex: `clientes`, `venda_itens`).
2. **Integridade:** 
   - Número principal do cliente (`clientes.whatsapp`): **11 dígitos**, `UNIQUE` (validação também na aplicação).
   - Telefones em `cliente_contatos_emergencia.telefone`: **11 dígitos** (`CHECK` na tabela).
3. **Tipagem:** Valores financeiros devem ser `INTEGER` (Centavos) para evitar erros de ponto flutuante.

### Tabelas — núcleo de clientes (V11.0+)
- **`clientes`:** `nome`, `whatsapp` (contacto principal, 11 dígitos, UNIQUE), `email`, `sexo`, `tem_filhos`, `gravida`, `data_parto_prevista`, `observacoes`; morada normalizada em `endereco_rua`, `endereco_numero`, `endereco_complemento`, `codigo_postal`, `concelho`, `freguesia`, `distrito`, `pais`. Coluna `morada` legada mantida (vazia em novos cadastros).
- **`cliente_filhos`:** `cliente_id`, `ordem`, `nome`, `idade_anos`, `sexo` (um registo por filho).
- **`cliente_contatos_emergencia`:** `cliente_id`, `ordem`, `nome`, `telefone` (opcional no negócio; 0..N registos).

### Tabelas — colaboradores e catálogo (E06 — Fases 1 a 3)
- **`servicos`:** `nome` (UNIQUE), `natureza` (`Sessão` | `Produto` | `Coworking` | `Pacote` | `Evento`), `ativo`, `descritivo`. Colunas de detalhe por natureza (nullable quando não aplicável):
  - Sessão: `sessao_duracao_horas` (REAL), `sessao_valor_centavos`.
  - Produto: `produto_tipo`, `produto_descricao`, `produto_valor_centavos`, `produto_origem` (`proprio` | `repasse`), `produto_repasse_pct_centesimos`, `produto_repasse_valor_centavos`.
  - Coworking: `cowork_sala_nome`, `cowork_cobranca` (`hora` | `dia`), `cowork_valor_centavos`.
  - Pacote: `pacote_valor_venda_centavos`, `pacote_repasse_ref_pct_centesimos` (1–10000; valor **editável** na UI, com sugestão automática via médias de repasse dos colaboradores habilitados nas sessões componentes).
  - Evento: `evento_data` (TEXT ISO), `evento_local`, `evento_observacoes`, `evento_escopo` (`interno` | `convidado`), `evento_preco_crianca_centavos`, `evento_preco_adulto_centavos`, `evento_desconto_filho_adicional_centavos`.
- **`servico_pacote_sessoes`:** `pacote_servico_id` → `servicos`, `sessao_servico_id` → `servicos` (natureza Sessão), `quantidade` (≥1), `duracao_horas` (NULL = usar `servicos.sessao_duracao_horas` da sessão referenciada), `ordem`.
- **`servico_pacote_produtos`:** `pacote_servico_id`, `produto_servico_id` (natureza Produto), `quantidade` (≥1); opcional (0 ou 1 linha por pacote na UI atual).
- **`servico_evento_participantes`:** `evento_servico_id` → `servicos` (natureza Evento), `tipo` (`colaborador` | `parceiro`), `colaborador_id` (NULL se parceiro), `parceiro_nome` (vazio se colaborador), `repasse_pct_centesimos` XOR `repasse_valor_centavos`, `ordem`.
  Seeds de exemplo (só nome/natureza) podem mostrar detalhe incompleto até edição no Catálogo.
- **`colaboradores`:** dados pessoais + morada estruturada (espelho da lógica de `clientes`), `data_nascimento`, `whatsapp` **UNIQUE** (contacto exclusivo), `observacoes`.
- **`colaborador_servicos`:** `colaborador_id`, `servico_id`, `percentual_centesimos` (1–10000 = 0,01%–100,00%), `ordem`, `data_insercao_linha` (TEXT `YYYY-MM-DD` — data de **inserção da linha** de habilitação, não do cadastro do colaborador); `UNIQUE(colaborador_id, servico_id)`.

### Tabelas — vendas (E07 — Painel de Vendas)
- **`vendas`:** `cliente_id`, `data_registo`, `estado_pagamento` (`integral` | `pendente` | `parcial` | `parcelado`), totais em centavos: `subtotal_bruto_centavos`, `subtotal_apos_descontos_linha_centavos`, `desconto_global_tipo` (`percent` \| `fixed` \| NULL), `desconto_global_valor` (basis points 1–10000 se %; centavos se fixo), `desconto_global_centavos_aplicado`, `total_final_centavos`, `observacoes`.
- **`venda_itens`:** `venda_id`, `servico_id`, `ordem`, `quantidade` (≥1), snapshots (`preco_unitario_centavos`, `nome_snapshot`, `descricao_snapshot`, `unidade_medida_snapshot`), `is_bonus` (0/1 — bónus ligado a `servico_id`; preço unitário 0), `evento_preco_tipo` (`adulto` \| `crianca` \| NULL), desconto de linha (`desconto_linha_tipo` `none`\|`percent`\|`fixed`, `desconto_linha_valor`, `desconto_linha_centavos`, `subtotal_bruto_centavos`, `total_linha_centavos`), **`colaborador_id`** (INTEGER NULL — opcional na UI de venda; filtros e dashboards).
- **`venda_pagamentos`:** `venda_id`, `ordem`, `meio` (`dinheiro` \| `cartao_credito` \| `mbway`), `valor_centavos` — **split** de meios no momento do registo (soma = valor pago já liquidado).
- **`venda_recebimentos_previstos`:** `venda_id`, `ordem`, `data_prevista` (TEXT ISO), `valor_centavos` — complementos (pendente/parcial) ou parcelas futuras (parcelado); soma com `venda_pagamentos` deve reconciliar com `total_final_centavos`.
- **Índices (E08):** `idx_vendas_data_registo`, `idx_venda_itens_servico`, `idx_venda_itens_colaborador` — desempenho de relatórios.

### Agendamentos (E09)
- **`agendamentos`:** ocorrência na agenda — `venda_id`, `venda_item_id`, `cliente_id`, `servico_id` (sessão/coworking/evento concreto da ocorrência; em pacote = `sessao_servico_id` da linha de composição), `pacote_sessao_id` (NULL se avulso/coworking/evento em linha única), `tipo_origem` (`sessao_avulsa` \| `pacote` \| `coworking` \| `evento`), `data_agendamento` (TEXT `YYYY-MM-DD`), `hora_inicio` / `hora_fim` (TEXT `HH:MM`, validação `fim > início` no domínio), `status` (`AGENDADO` \| `CONFIRMADO` \| `CONCLUIDO` \| `CANCELADO`), `devolver_ao_buffer` (0/1 — preenchido no cancelamento: devolve crédito ao buffer ou consome para efeitos de saldo), `observacoes`, `data_alteracao`.
- **`agendamento_colaboradores`:** `agendamento_id`, `colaborador_id`, `ordem` (N colaboradores por ocorrência).
- **Saldo de crédito (sem tabela extra):** por `(venda_item_id, pacote_sessao_id)` — direitos = quantidade da linha (ou `quantidade_pacote_sessão × quantidade_linha_venda` para pacote); consumo = ocorrências em `AGENDADO`/`CONFIRMADO`/`CONCLUIDO` ou `CANCELADO` com `devolver_ao_buffer = 0`. **Produto** não gera créditos agendáveis.
- **UI / tema:** `page_agendamentos.py`; tokens `AGENDA_STATUS_STYLES` e `AGENDA_TIPO_ORIGEM_ICONS` em `theme.py`.

### Analytics / Dashboards (E08)
- **Módulo `relatorios.py`:** agregações sobre `venda_itens` ⋈ `vendas` ⋈ `clientes` ⋈ `servicos` ⋈ `colaboradores` (LEFT); filtros: período (`date(data_registo)`), clientes, serviços, colaboradores (linha), checkbox natureza **Produto**.
- **Métricas Fase A (“lucro”):** sem custos na base — **receita em linhas** = `SUM(total_linha_centavos)` (após desconto de linha); **receita em cabeçalhos** = soma de `total_final_centavos` por `venda_id` distinto no conjunto filtrado (inclui desconto global). Na UI, «margem / lucro» na Fase A alinha-se à **receita (linhas)** com nota explícita; **Fase B** poderá introduzir custos ou reparte analítica.
- **Pareto:** percentagem cumulativa calculada **só sobre as categorias exibidas** (Top N barras), não sobre universo completo.
- **UI:** `page_dashboards.py`; gráficos **Plotly**; paleta `ANALYTICS_COLORS` em `theme.py` (tons suaves).

## 🛠️ PADRÕES DE CÓDIGO
- **Modularidade:** A lógica de banco de dados deve estar separada da interface (Streamlit).
- **Tratamento de Erros:** Todo acesso ao banco deve estar dentro de blocos `try/except/finally`.
