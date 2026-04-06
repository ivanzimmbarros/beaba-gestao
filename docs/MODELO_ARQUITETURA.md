# 🏗️ MODELO DE ARQUITETURA - BEABA GESTÃO (V8.0)

## 📁 ESTRUTURA DE PASTAS OBRIGATÓRIA
- `/src`: Código-fonte da aplicação (Lógica, UI, Utils).
  - `/src/app.py`: Shell Streamlit (tema V11, navegação e páginas).
  - `/src/ui`: Tokens visuais e estilos compartilhados (mimetismo com o site).
  - `/src/modules`: Domínio (ex.: clientes).
  - `/src/database`: Conexão e esquema.
- `/data`: Scripts de migração, Schema SQL e Banco de Dados (SQLite).
- `/tests`: Scripts de teste unitário e de integração para o QA.
- `/docs`: Documentação técnica, Caderno Mestre e Diagramas.

## 🛢️ PADRÕES DE BANCO DE DADOS (SQL)
1. **Nomenclatura:** Tabelas em `snake_case` e no plural (ex: `clientes`, `venda_itens`).
2. **Integridade:** 
   - Todo WhatsApp deve ter `CHECK (length(whatsapp) = 11)`.
   - Todo WhatsApp deve ser `UNIQUE`.
3. **Tipagem:** Valores financeiros devem ser `INTEGER` (Centavos) para evitar erros de ponto flutuante.

## 🛠️ PADRÕES DE CÓDIGO
- **Modularidade:** A lógica de banco de dados deve estar separada da interface (Streamlit).
- **Tratamento de Erros:** Todo acesso ao banco deve estar dentro de blocos `try/except/finally`.
