# 🏗️ MODELO DE ARQUITETURA - BEABA GESTÃO (V8.0)

## 📁 ESTRUTURA DE PASTAS OBRIGATÓRIA
- `/src`: Código-fonte da aplicação (Lógica, UI, Utils).
  - `/src/app.py`: Shell Streamlit (tema V11, navegação e páginas).
  - `/src/ui`: Tokens visuais e estilos compartilhados (mimetismo com o site).
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

## 🛠️ PADRÕES DE CÓDIGO
- **Modularidade:** A lógica de banco de dados deve estar separada da interface (Streamlit).
- **Tratamento de Erros:** Todo acesso ao banco deve estar dentro de blocos `try/except/finally`.
