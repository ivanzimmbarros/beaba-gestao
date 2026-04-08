# 99 — Encerramento

**Demanda:** `2026-04-08_E16_cliente_nif_telefone_internacional` · **2026-04-08**

## Entregas (produto)

- **NIF PT** (módulo 11) e **documento internacional** com flag; colunas `nif_ou_documento`, `identificacao_internacional` em `clientes`.
- **Telefone E.164** (`phonenumbers`) no principal (`whatsapp`) e emergências; widgets em **Clientes** (`app.py`) e **Vendas** (`page_vendas.py`); legado 11/9 dígitos suportado na normalização.
- **Filhos:** `cliente_filhos.data_nascimento` opcional; recálculo de idade quando há data.
- **Migração SQLite:** `cliente_contatos_emergencia` sem CHECK de 11 dígitos (tabela recriada se necessário).

## Governança

Pareceres **06** (Arquiteto), **07** (Analista), **09** (QA) no dossier; commits em `develop` (implementação + este encerramento).

Percurso **SUCESSO** até **PC13a** (Git); **PC13b** reflectido no Painel. Próximo pedido: **`@Files` → Analista**.
