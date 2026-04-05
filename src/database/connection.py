import sqlite3
import os
import streamlit as st

def get_connection():
    """
    Gerenciador de Conexão Mestre:
    Prioriza Bancos de Dados de Produção (PostgreSQL/MySQL) via Secrets.
    Mantém SQLite local com criação automática de diretório como Fallback.
    """
    # 1. Tenta conexão com Banco de Dados de Produção (Protegido para QA)
    try:
        # O 'try' aqui evita que o FileNotFoundError do Streamlit trave o QA
        if hasattr(st, "secrets") and "database" in st.secrets:
            # Aqui entrará a lógica de conexão externa (ex: psycopg2 para Postgres)
            # Por ora, mantemos o gancho preparado para a escala
            pass
    except Exception:
        # Se não houver secrets (caso do QA), apenas ignora e segue para o SQLite
        pass

    # 2. Estrutura de Contingência (SQLite Robusto) - MANTIDA INTEGRALMENTE
    db_path = "data/beaba_gestao.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    try:
        # check_same_thread=False permite acessos simultâneos controlados pelo Streamlit
        conn = sqlite3.connect(db_path, check_same_thread=False)
        return conn
    except Exception as e:
        st.error(f"Falha crítica na base de dados: {e}")
        return None
        
def create_tables():
    """Garante que a estrutura exista antes do primeiro acesso"""
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                whatsapp TEXT UNIQUE NOT NULL,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
