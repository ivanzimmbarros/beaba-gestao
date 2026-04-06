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

### Tabelas — colaboradores e catálogo mínimo
- **`servicos`:** `nome` (UNIQUE), `natureza` (ex.: Sessão), `ativo`; seeds de exemplo até o módulo Catálogo completo.
- **`colaboradores`:** dados pessoais + morada estruturada (espelho da lógica de `clientes`), `data_nascimento`, `whatsapp` **UNIQUE** (contacto exclusivo), `observacoes`.
- **`colaborador_servicos`:** `colaborador_id`, `servico_id`, `percentual_centesimos` (1–10000 = 0,01%–100,00%), `ordem`; `UNIQUE(colaborador_id, servico_id)`.

## 🛠️ PADRÕES DE CÓDIGO
- **Modularidade:** A lógica de banco de dados deve estar separada da interface (Streamlit).
- **Tratamento de Erros:** Todo acesso ao banco deve estar dentro de blocos `try/except/finally`.
