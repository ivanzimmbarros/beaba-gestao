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


def _migrate_agendamentos_e11_if_needed(cursor) -> None:
    """
    E11: `modo_origem` + `venda_id`/`venda_item_id` NULL em pré-venda.
    SQLite não remove NOT NULL com ALTER; recria tabela e repõe colaboradores.
    """
    if "agendamentos" not in {r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}:
        return
    cols = _table_columns(cursor, "agendamentos")
    if "modo_origem" in cols:
        return
    cursor.execute("PRAGMA foreign_keys=OFF")
    cursor.execute(
        """
        CREATE TABLE agendamento_colaboradores_e11_bak AS
        SELECT agendamento_id, colaborador_id, ordem FROM agendamento_colaboradores
        """
    )
    cursor.execute("DROP TABLE agendamento_colaboradores")
    cursor.execute("ALTER TABLE agendamentos RENAME TO agendamentos_e11_old")
    cursor.execute(
        """
        CREATE TABLE agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER,
            venda_item_id INTEGER,
            cliente_id INTEGER NOT NULL,
            servico_id INTEGER NOT NULL,
            pacote_sessao_id INTEGER,
            tipo_origem TEXT NOT NULL CHECK (
                tipo_origem IN ('sessao_avulsa', 'pacote', 'coworking', 'evento')
            ),
            data_agendamento TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fim TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN ('AGENDADO', 'CONFIRMADO', 'CONCLUIDO', 'CANCELADO')
            ),
            devolver_ao_buffer INTEGER NOT NULL DEFAULT 0 CHECK (devolver_ao_buffer IN (0, 1)),
            observacoes TEXT DEFAULT '',
            data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modo_origem TEXT NOT NULL DEFAULT 'credito_venda' CHECK (
                modo_origem IN ('credito_venda', 'pre_venda')
            ),
            preco_referencia_centavos INTEGER CHECK (
                preco_referencia_centavos IS NULL OR preco_referencia_centavos >= 0
            ),
            CHECK (
                (modo_origem = 'pre_venda' AND venda_id IS NULL AND venda_item_id IS NULL)
                OR (
                    modo_origem = 'credito_venda'
                    AND venda_id IS NOT NULL
                    AND venda_item_id IS NOT NULL
                )
            ),
            FOREIGN KEY (venda_id) REFERENCES vendas(id) ON DELETE CASCADE,
            FOREIGN KEY (venda_item_id) REFERENCES venda_itens(id) ON DELETE CASCADE,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id),
            FOREIGN KEY (servico_id) REFERENCES servicos(id),
            FOREIGN KEY (pacote_sessao_id) REFERENCES servico_pacote_sessoes(id)
        )
        """
    )
    cursor.execute(
        """
        INSERT INTO agendamentos (
            id, venda_id, venda_item_id, cliente_id, servico_id, pacote_sessao_id,
            tipo_origem, data_agendamento, hora_inicio, hora_fim, status,
            devolver_ao_buffer, observacoes, data_alteracao, modo_origem,
            preco_referencia_centavos
        )
        SELECT
            id, venda_id, venda_item_id, cliente_id, servico_id, pacote_sessao_id,
            tipo_origem, data_agendamento, hora_inicio, hora_fim, status,
            devolver_ao_buffer, observacoes, data_alteracao, 'credito_venda',
            NULL
        FROM agendamentos_e11_old
        """
    )
    cursor.execute("DROP TABLE agendamentos_e11_old")
    cursor.execute(
        """
        CREATE TABLE agendamento_colaboradores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agendamento_id INTEGER NOT NULL,
            colaborador_id INTEGER NOT NULL,
            ordem INTEGER NOT NULL,
            FOREIGN KEY (agendamento_id) REFERENCES agendamentos(id) ON DELETE CASCADE,
            FOREIGN KEY (colaborador_id) REFERENCES colaboradores(id)
        )
        """
    )
    cursor.execute(
        """
        INSERT INTO agendamento_colaboradores (agendamento_id, colaborador_id, ordem)
        SELECT agendamento_id, colaborador_id, ordem FROM agendamento_colaboradores_e11_bak
        """
    )
    cursor.execute("DROP TABLE agendamento_colaboradores_e11_bak")
    cursor.execute("PRAGMA foreign_keys=ON")


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


def _migrate_cliente_contatos_emergencia_e16_if_needed(cursor) -> None:
    """E16: remove CHECK length(telefone)=11 para permitir E.164."""
    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='cliente_contatos_emergencia'"
    )
    row = cursor.fetchone()
    if not row or not row[0] or "length(telefone) = 11" not in row[0]:
        return
    cursor.execute("PRAGMA foreign_keys=OFF")
    cursor.execute(
        """
        CREATE TABLE cliente_contatos_emergencia_e16 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            ordem INTEGER NOT NULL,
            nome TEXT NOT NULL,
            telefone TEXT NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        """
        INSERT INTO cliente_contatos_emergencia_e16 (id, cliente_id, ordem, nome, telefone)
        SELECT id, cliente_id, ordem, nome, telefone FROM cliente_contatos_emergencia
        """
    )
    cursor.execute("DROP TABLE cliente_contatos_emergencia")
    cursor.execute("ALTER TABLE cliente_contatos_emergencia_e16 RENAME TO cliente_contatos_emergencia")
    cursor.execute("PRAGMA foreign_keys=ON")


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
        ("nif_ou_documento", "TEXT"),
        ("identificacao_internacional", "INTEGER NOT NULL DEFAULT 0"),
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
    _ensure_column(cursor, "cliente_filhos", "data_nascimento", "TEXT")
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
            FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
        )
        """
    )
    _migrate_cliente_contatos_emergencia_e16_if_needed(cursor)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            data_registo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            estado_pagamento TEXT NOT NULL CHECK (
                estado_pagamento IN ('integral', 'pendente', 'parcial', 'parcelado')
            ),
            subtotal_bruto_centavos INTEGER NOT NULL DEFAULT 0,
            subtotal_apos_descontos_linha_centavos INTEGER NOT NULL DEFAULT 0,
            desconto_global_tipo TEXT CHECK (
                desconto_global_tipo IS NULL
                OR desconto_global_tipo IN ('percent', 'fixed')
            ),
            desconto_global_valor INTEGER,
            desconto_global_centavos_aplicado INTEGER NOT NULL DEFAULT 0,
            total_final_centavos INTEGER NOT NULL,
            observacoes TEXT DEFAULT '',
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS venda_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER NOT NULL,
            servico_id INTEGER NOT NULL,
            ordem INTEGER NOT NULL,
            quantidade INTEGER NOT NULL CHECK (quantidade >= 1),
            preco_unitario_centavos INTEGER NOT NULL CHECK (preco_unitario_centavos >= 0),
            nome_snapshot TEXT NOT NULL,
            descricao_snapshot TEXT NOT NULL DEFAULT '',
            unidade_medida_snapshot TEXT NOT NULL DEFAULT '',
            is_bonus INTEGER NOT NULL DEFAULT 0 CHECK (is_bonus IN (0, 1)),
            evento_preco_tipo TEXT CHECK (
                evento_preco_tipo IS NULL
                OR evento_preco_tipo IN ('adulto', 'crianca')
            ),
            desconto_linha_tipo TEXT CHECK (
                desconto_linha_tipo IS NULL
                OR desconto_linha_tipo IN ('none', 'percent', 'fixed')
            ),
            desconto_linha_valor INTEGER,
            subtotal_bruto_centavos INTEGER NOT NULL,
            desconto_linha_centavos INTEGER NOT NULL DEFAULT 0,
            total_linha_centavos INTEGER NOT NULL,
            FOREIGN KEY (venda_id) REFERENCES vendas(id) ON DELETE CASCADE,
            FOREIGN KEY (servico_id) REFERENCES servicos(id)
        )
        """
    )
    _ensure_column(cursor, "venda_itens", "colaborador_id", "INTEGER")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_vendas_data_registo ON vendas(data_registo)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_venda_itens_servico ON venda_itens(servico_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_venda_itens_colaborador ON venda_itens(colaborador_id)"
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS venda_pagamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER NOT NULL,
            ordem INTEGER NOT NULL,
            meio TEXT NOT NULL CHECK (
                meio IN ('dinheiro', 'cartao_credito', 'mbway')
            ),
            valor_centavos INTEGER NOT NULL CHECK (valor_centavos >= 0),
            FOREIGN KEY (venda_id) REFERENCES vendas(id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS venda_recebimentos_previstos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER NOT NULL,
            ordem INTEGER NOT NULL,
            data_prevista TEXT NOT NULL,
            valor_centavos INTEGER NOT NULL CHECK (valor_centavos >= 0),
            FOREIGN KEY (venda_id) REFERENCES vendas(id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER,
            venda_item_id INTEGER,
            cliente_id INTEGER NOT NULL,
            servico_id INTEGER NOT NULL,
            pacote_sessao_id INTEGER,
            tipo_origem TEXT NOT NULL CHECK (
                tipo_origem IN ('sessao_avulsa', 'pacote', 'coworking', 'evento')
            ),
            data_agendamento TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fim TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN ('AGENDADO', 'CONFIRMADO', 'CONCLUIDO', 'CANCELADO')
            ),
            devolver_ao_buffer INTEGER NOT NULL DEFAULT 0 CHECK (devolver_ao_buffer IN (0, 1)),
            observacoes TEXT DEFAULT '',
            data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modo_origem TEXT NOT NULL DEFAULT 'credito_venda' CHECK (
                modo_origem IN ('credito_venda', 'pre_venda')
            ),
            preco_referencia_centavos INTEGER CHECK (
                preco_referencia_centavos IS NULL OR preco_referencia_centavos >= 0
            ),
            CHECK (
                (modo_origem = 'pre_venda' AND venda_id IS NULL AND venda_item_id IS NULL)
                OR (
                    modo_origem = 'credito_venda'
                    AND venda_id IS NOT NULL
                    AND venda_item_id IS NOT NULL
                )
            ),
            FOREIGN KEY (venda_id) REFERENCES vendas(id) ON DELETE CASCADE,
            FOREIGN KEY (venda_item_id) REFERENCES venda_itens(id) ON DELETE CASCADE,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id),
            FOREIGN KEY (servico_id) REFERENCES servicos(id),
            FOREIGN KEY (pacote_sessao_id) REFERENCES servico_pacote_sessoes(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS agendamento_colaboradores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agendamento_id INTEGER NOT NULL,
            colaborador_id INTEGER NOT NULL,
            ordem INTEGER NOT NULL,
            FOREIGN KEY (agendamento_id) REFERENCES agendamentos(id) ON DELETE CASCADE,
            FOREIGN KEY (colaborador_id) REFERENCES colaboradores(id)
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_agendamentos_data ON agendamentos(data_agendamento)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_agendamentos_cliente ON agendamentos(cliente_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_agendamentos_venda ON agendamentos(venda_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_agendamento_colab_ag ON agendamento_colaboradores(agendamento_id)"
    )
    _migrate_agendamentos_e11_if_needed(cursor)
    _ensure_column(
        cursor,
        "vendas",
        "agendamento_contexto_id",
        "INTEGER REFERENCES agendamentos(id) ON DELETE SET NULL",
    )
    conn.commit()
    conn.close()
