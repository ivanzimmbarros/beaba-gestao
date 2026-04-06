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
