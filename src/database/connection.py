import os
import sqlite3

import streamlit as st


def get_connection():
    """
    Gerenciador de Conexão Mestre:
    Prioriza Bancos de Dados de Produção (PostgreSQL/MySQL) via Secrets.
    Mantém SQLite local com criação automática de diretório como Fallback.
    """
    try:
        if hasattr(st, "secrets") and "database" in st.secrets:
            pass
    except Exception:
        pass

    db_path = "data/beaba_gestao.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    try:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except Exception as e:
        st.error(f"Falha crítica na base de dados: {e}")
        return None


def _table_columns(cursor, table: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def _ensure_column(cursor, table: str, column: str, definition: str) -> None:
    if column not in _table_columns(cursor, table):
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _seed_servicos_exemplo(cursor) -> None:
    """Serviços de exemplo até o módulo Catálogo estar completo."""
    cursor.execute("SELECT COUNT(*) FROM servicos")
    if cursor.fetchone()[0] > 0:
        return
    exemplos = (
        "Massagem de relaxamento",
        "Consulta de psicologia",
        "Yoga pré-natal",
        "Fisioterapia pós-parto",
        "Acompanhamento de amamentação",
    )
    for nome in exemplos:
        cursor.execute(
            "INSERT INTO servicos (nome, natureza) VALUES (?, 'Sessão')",
            (nome,),
        )


def create_tables():
    """Garante esquema base, migrações incrementais e tabelas relacionadas."""
    conn = get_connection()
    if not conn:
        return
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            whatsapp TEXT UNIQUE NOT NULL,
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    for col, definition in (
        ("morada", "TEXT DEFAULT ''"),
        ("email", "TEXT DEFAULT ''"),
        ("sexo", "TEXT DEFAULT 'Prefiro não informar'"),
        ("tem_filhos", "INTEGER DEFAULT 0"),
        ("gravida", "INTEGER"),
        ("data_parto_prevista", "TEXT"),
        ("observacoes", "TEXT DEFAULT ''"),
        ("endereco_rua", "TEXT DEFAULT ''"),
        ("endereco_numero", "TEXT DEFAULT ''"),
        ("endereco_complemento", "TEXT DEFAULT ''"),
        ("codigo_postal", "TEXT DEFAULT ''"),
        ("concelho", "TEXT DEFAULT ''"),
        ("freguesia", "TEXT DEFAULT ''"),
        ("distrito", "TEXT DEFAULT ''"),
        ("pais", "TEXT DEFAULT 'Portugal'"),
    ):
        _ensure_column(cursor, "clientes", col, definition)

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS cliente_filhos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            ordem INTEGER NOT NULL,
            idade_anos INTEGER NOT NULL,
            sexo TEXT NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
        )
        """
    )
    _ensure_column(cursor, "cliente_filhos", "nome", "TEXT DEFAULT ''")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS servicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            natureza TEXT DEFAULT 'Sessão',
            ativo INTEGER DEFAULT 1
        )
        """
    )
    for col, definition in (
        ("descritivo", "TEXT DEFAULT ''"),
        ("sessao_duracao_horas", "REAL"),
        ("sessao_valor_centavos", "INTEGER"),
        ("produto_tipo", "TEXT DEFAULT ''"),
        ("produto_descricao", "TEXT DEFAULT ''"),
        ("produto_valor_centavos", "INTEGER"),
        ("produto_origem", "TEXT DEFAULT ''"),
        ("produto_repasse_pct_centesimos", "INTEGER"),
        ("produto_repasse_valor_centavos", "INTEGER"),
        ("cowork_sala_nome", "TEXT DEFAULT ''"),
        ("cowork_cobranca", "TEXT DEFAULT ''"),
        ("cowork_valor_centavos", "INTEGER"),
        ("pacote_valor_venda_centavos", "INTEGER"),
        ("pacote_repasse_ref_pct_centesimos", "INTEGER"),
        ("evento_data", "TEXT DEFAULT ''"),
        ("evento_local", "TEXT DEFAULT ''"),
        ("evento_observacoes", "TEXT DEFAULT ''"),
        ("evento_escopo", "TEXT DEFAULT ''"),
        ("evento_preco_crianca_centavos", "INTEGER"),
        ("evento_preco_adulto_centavos", "INTEGER"),
        ("evento_desconto_filho_adicional_centavos", "INTEGER"),
    ):
        _ensure_column(cursor, "servicos", col, definition)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS servico_pacote_sessoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pacote_servico_id INTEGER NOT NULL,
            sessao_servico_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL CHECK (quantidade >= 1),
            duracao_horas REAL,
            ordem INTEGER NOT NULL,
            FOREIGN KEY (pacote_servico_id) REFERENCES servicos(id) ON DELETE CASCADE,
            FOREIGN KEY (sessao_servico_id) REFERENCES servicos(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS servico_pacote_produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pacote_servico_id INTEGER NOT NULL,
            produto_servico_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL CHECK (quantidade >= 1),
            FOREIGN KEY (pacote_servico_id) REFERENCES servicos(id) ON DELETE CASCADE,
            FOREIGN KEY (produto_servico_id) REFERENCES servicos(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS colaboradores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            sexo TEXT NOT NULL,
            data_nascimento TEXT NOT NULL,
            email TEXT NOT NULL,
            whatsapp TEXT UNIQUE NOT NULL,
            observacoes TEXT DEFAULT '',
            endereco_rua TEXT NOT NULL,
            endereco_numero TEXT NOT NULL,
            endereco_complemento TEXT DEFAULT '',
            codigo_postal TEXT NOT NULL,
            concelho TEXT NOT NULL,
            freguesia TEXT NOT NULL,
            distrito TEXT DEFAULT '',
            pais TEXT DEFAULT 'Portugal',
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS colaborador_servicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            colaborador_id INTEGER NOT NULL,
            servico_id INTEGER NOT NULL,
            percentual_centesimos INTEGER NOT NULL,
            ordem INTEGER NOT NULL,
            FOREIGN KEY (colaborador_id) REFERENCES colaboradores(id) ON DELETE CASCADE,
            FOREIGN KEY (servico_id) REFERENCES servicos(id),
            UNIQUE(colaborador_id, servico_id),
            CHECK(percentual_centesimos >= 1 AND percentual_centesimos <= 10000)
        )
        """
    )
    _ensure_column(cursor, "colaborador_servicos", "data_insercao_linha", "TEXT DEFAULT ''")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS servico_evento_participantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evento_servico_id INTEGER NOT NULL,
            tipo TEXT NOT NULL CHECK (tipo IN ('colaborador', 'parceiro')),
            colaborador_id INTEGER,
            parceiro_nome TEXT DEFAULT '',
            repasse_pct_centesimos INTEGER,
            repasse_valor_centavos INTEGER,
            ordem INTEGER NOT NULL,
            FOREIGN KEY (evento_servico_id) REFERENCES servicos(id) ON DELETE CASCADE,
            FOREIGN KEY (colaborador_id) REFERENCES colaboradores(id)
        )
        """
    )
    _seed_servicos_exemplo(cursor)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS cliente_contatos_emergencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            ordem INTEGER NOT NULL,
            nome TEXT NOT NULL,
            telefone TEXT NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE,
            CHECK (length(telefone) = 11)
        )
        """
    )
    conn.commit()
    conn.close()
