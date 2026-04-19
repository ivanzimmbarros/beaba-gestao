import os
import sqlite3

import streamlit as st


def get_connection():
    """
    Conexão SQLite (WAL, foreign_keys).

    Não aceder a `st.secrets` aqui sem `secrets.toml`: o Streamlit chama `st.error` ao
    falhar o parse mesmo antes de propagar excepção, o que quebra toda a UI local.
    Produção com secrets: usar `BEABA_SQLITE_PATH` ou futura camada explícita.
    """
    db_path = os.environ.get("BEABA_SQLITE_PATH") or "data/beaba_gestao.db"
    db_dir = os.path.dirname(os.path.abspath(db_path))
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    try:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode=WAL")
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


def _ensure_financeiro_lancamentos_extras(cursor) -> None:
    """Colunas para Real/Meta, competência, status e replicação mensal."""
    tabs = {r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "financeiro_gasto_lancamentos" not in tabs:
        return
    _ensure_column(cursor, "financeiro_gasto_lancamentos", "classe_lancamento", "TEXT NOT NULL DEFAULT 'real'")
    _ensure_column(cursor, "financeiro_gasto_lancamentos", "data_competencia", "TEXT")
    _ensure_column(cursor, "financeiro_gasto_lancamentos", "status_lancamento", "TEXT NOT NULL DEFAULT 'agendado'")
    _ensure_column(cursor, "financeiro_gasto_lancamentos", "replica_para_outros_meses", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(cursor, "financeiro_gasto_lancamentos", "numero_meses_planeados", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(cursor, "financeiro_gasto_lancamentos", "data_pagamento", "TEXT")
    _ensure_column(cursor, "financeiro_gasto_lancamentos", "data_criacao_registo", "TEXT")


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


def _migrate_especialidades_if_needed(cursor) -> None:
    """Garante tabela `especialidades`, coluna `servicos.especialidade_id` e backfill «Geral» por natureza."""
    from src.modules.constants import ESPECIALIDADE_PADRAO_NOME, NATUREZAS_CATALOGO_FASE3

    tabs = {r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "especialidades" not in tabs or "servicos" not in tabs:
        return
    if "especialidade_id" not in _table_columns(cursor, "servicos"):
        return
    pad = ESPECIALIDADE_PADRAO_NOME
    for nat in NATUREZAS_CATALOGO_FASE3:
        cursor.execute(
            """
            INSERT OR IGNORE INTO especialidades (natureza, nome, descritivo, ativo, ordem)
            VALUES (?, ?, '', 1, 0)
            """,
            (nat, pad),
        )
    cursor.execute(
        """
        SELECT DISTINCT TRIM(natureza) AS n
        FROM servicos
        WHERE IFNULL(TRIM(natureza), '') != ''
        """
    )
    for (nat,) in cursor.fetchall():
        if not nat:
            continue
        cursor.execute(
            """
            INSERT OR IGNORE INTO especialidades (natureza, nome, descritivo, ativo, ordem)
            VALUES (?, ?, '', 1, 0)
            """,
            (str(nat), pad),
        )
    cursor.execute(
        """
        UPDATE servicos
        SET especialidade_id = (
            SELECT e.id FROM especialidades e
            WHERE e.natureza = servicos.natureza AND e.nome = ?
            LIMIT 1
        )
        WHERE especialidade_id IS NULL
        """,
        (pad,),
    )


def _seed_servicos_exemplo(cursor) -> None:
    """Serviços de exemplo até o módulo Catálogo estar completo."""
    cursor.execute("SELECT COUNT(*) FROM servicos")
    if cursor.fetchone()[0] > 0:
        return
    cursor.execute(
        """
        INSERT OR IGNORE INTO especialidades (natureza, nome, descritivo, ativo, ordem)
        VALUES ('Sessão', 'Geral', '', 1, 0)
        """
    )
    cursor.execute(
        "SELECT id FROM especialidades WHERE natureza = 'Sessão' AND nome = 'Geral' LIMIT 1"
    )
    row_e = cursor.fetchone()
    if not row_e:
        return
    eid = int(row_e[0])
    exemplos = (
        "Massagem de relaxamento",
        "Consulta de psicologia",
        "Yoga pré-natal",
        "Fisioterapia pós-parto",
        "Acompanhamento de amamentação",
    )
    for nome in exemplos:
        cursor.execute(
            "INSERT INTO servicos (nome, natureza, especialidade_id) VALUES (?, 'Sessão', ?)",
            (nome, eid),
        )


def _migrate_e18_if_needed(cursor) -> None:
    """
    E18: ledger, histórico, linhas de pagamento, repasse, novos estados em agendamentos,
    coluna credito_abatido em vendas, view saldo cliente.
    """
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS credito_movimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            tipo_movimento TEXT NOT NULL CHECK (
                tipo_movimento IN (
                    'CREDITO_CANCELAMENTO',
                    'USO_VENDA',
                    'USO_AGENDAMENTO',
                    'AJUSTE_MANUAL',
                    'ESTORNO'
                )
            ),
            valor_centavos INTEGER NOT NULL,
            referencia_tipo TEXT NOT NULL DEFAULT '',
            referencia_id INTEGER,
            observacoes TEXT,
            actor TEXT,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (cliente_id) REFERENCES clientes(id),
            UNIQUE (referencia_tipo, referencia_id, tipo_movimento)
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_credito_mov_cliente ON credito_movimentos(cliente_id)"
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS venda_pagamento_linhas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER NOT NULL,
            ordem INTEGER NOT NULL DEFAULT 0,
            tipo_meio TEXT NOT NULL CHECK (
                tipo_meio IN ('DINHEIRO_MBWAY', 'IBAN', 'CARTAO_CREDITO', 'CREDITO_LOJA')
            ),
            valor_centavos INTEGER NOT NULL CHECK (valor_centavos > 0),
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (venda_id) REFERENCES vendas(id) ON DELETE CASCADE,
            UNIQUE (venda_id, ordem)
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_venda_pagamento_linhas_v ON venda_pagamento_linhas(venda_id)"
    )

    cursor.execute("DROP VIEW IF EXISTS main.vw_cliente_saldo_credito")
    cursor.execute("DROP VIEW IF EXISTS vw_cliente_saldo_credito")
    try:
        cursor.execute(
            """
            CREATE VIEW vw_cliente_saldo_credito AS
            SELECT
                cliente_id,
                COALESCE(SUM(valor_centavos), 0) AS saldo_credito_centavos
            FROM credito_movimentos
            GROUP BY cliente_id
            """
        )
    except sqlite3.OperationalError as exc:
        if "already exists" not in str(exc).lower():
            raise

    _ensure_column(
        cursor,
        "vendas",
        "credito_abatido_centavos",
        "INTEGER NOT NULL DEFAULT 0 CHECK (credito_abatido_centavos >= 0)",
    )

    cursor.execute(
        """
        INSERT OR IGNORE INTO venda_pagamento_linhas (venda_id, ordem, tipo_meio, valor_centavos)
        SELECT
            vp.venda_id,
            vp.ordem,
            CASE vp.meio
                WHEN 'dinheiro' THEN 'DINHEIRO_MBWAY'
                WHEN 'mbway' THEN 'DINHEIRO_MBWAY'
                WHEN 'cartao_credito' THEN 'CARTAO_CREDITO'
                ELSE 'DINHEIRO_MBWAY'
            END,
            vp.valor_centavos
        FROM venda_pagamentos vp
        WHERE vp.valor_centavos > 0
          AND NOT EXISTS (
              SELECT 1 FROM venda_pagamento_linhas x WHERE x.venda_id = vp.venda_id AND x.ordem = vp.ordem
          )
        """
    )

    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='agendamentos'"
    )
    row = cursor.fetchone()
    ag_sql = (row[0] or "") if row else ""
    need_ag_rebuild = bool(ag_sql) and "PRE_AGENDADO" not in ag_sql

    if need_ag_rebuild:
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS _e18_ag_ctx (venda_id INTEGER PRIMARY KEY, ag_id INTEGER NOT NULL)
            """
        )
        cursor.execute("DELETE FROM _e18_ag_ctx")
        cursor.execute(
            """
            INSERT INTO _e18_ag_ctx (venda_id, ag_id)
            SELECT id, agendamento_contexto_id FROM vendas
            WHERE agendamento_contexto_id IS NOT NULL
            """
        )
        cursor.execute(
            "UPDATE vendas SET agendamento_contexto_id = NULL WHERE agendamento_contexto_id IS NOT NULL"
        )

        cursor.execute(
            """
            CREATE TABLE agendamento_colaboradores_e18_bak AS
            SELECT * FROM agendamento_colaboradores
            """
        )
        cursor.execute("DROP TABLE agendamento_colaboradores")
        cursor.execute(
            """
            CREATE TABLE agendamentos_e18_new (
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
                    status IN (
                        'PRE_AGENDADO',
                        'AGENDADO',
                        'CONFIRMADO',
                        'REALIZADO_PENDENTE_PGTO',
                        'CONCLUIDO',
                        'CANCELADO'
                    )
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
            INSERT INTO agendamentos_e18_new (
                id, venda_id, venda_item_id, cliente_id, servico_id, pacote_sessao_id,
                tipo_origem, data_agendamento, hora_inicio, hora_fim, status,
                devolver_ao_buffer, observacoes, data_alteracao, modo_origem, preco_referencia_centavos
            )
            SELECT
                id, venda_id, venda_item_id, cliente_id, servico_id, pacote_sessao_id,
                tipo_origem, data_agendamento, hora_inicio, hora_fim, status,
                devolver_ao_buffer, observacoes, data_alteracao, modo_origem, preco_referencia_centavos
            FROM agendamentos
            """
        )
        cursor.execute("DROP TABLE agendamentos")
        cursor.execute("ALTER TABLE agendamentos_e18_new RENAME TO agendamentos")
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
            INSERT INTO agendamento_colaboradores (id, agendamento_id, colaborador_id, ordem)
            SELECT id, agendamento_id, colaborador_id, ordem FROM agendamento_colaboradores_e18_bak
            """
        )
        cursor.execute("DROP TABLE agendamento_colaboradores_e18_bak")
        cursor.execute(
            """
            UPDATE vendas SET agendamento_contexto_id = (
                SELECT ag_id FROM _e18_ag_ctx WHERE _e18_ag_ctx.venda_id = vendas.id
            )
            WHERE id IN (SELECT venda_id FROM _e18_ag_ctx)
            """
        )
        cursor.execute("DROP TABLE _e18_ag_ctx")
        cursor.execute("PRAGMA foreign_keys=ON")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agendamentos_data ON agendamentos(data_agendamento)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agendamentos_cliente ON agendamentos(cliente_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agendamentos_venda ON agendamentos(venda_id)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_agendamento_colab_ag ON agendamento_colaboradores(agendamento_id)"
        )

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='repasse_linhas'"
    )
    if cursor.fetchone():
        cursor.execute("SELECT COUNT(*) FROM repasse_linhas")
        if int(cursor.fetchone()[0]) == 0:
            cursor.execute("DROP TABLE repasse_linhas")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS repasse_linhas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agendamento_id INTEGER NOT NULL,
            colaborador_id INTEGER NOT NULL,
            base_calculo_centavos INTEGER NOT NULL DEFAULT 0 CHECK (base_calculo_centavos >= 0),
            percentual_bp INTEGER,
            valor_repasse_centavos INTEGER NOT NULL DEFAULT 0 CHECK (valor_repasse_centavos >= 0),
            status_repasse TEXT NOT NULL DEFAULT 'PENDENTE_REPASSE' CHECK (
                status_repasse IN ('PENDENTE_REPASSE', 'REPASSE_PAGO')
            ),
            pago_em TEXT,
            observacoes TEXT,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (agendamento_id) REFERENCES agendamentos(id) ON DELETE CASCADE,
            FOREIGN KEY (colaborador_id) REFERENCES colaboradores(id)
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_repasse_linhas_ag ON repasse_linhas(agendamento_id)"
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS agendamento_historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agendamento_id INTEGER NOT NULL,
            campo TEXT NOT NULL,
            valor_anterior TEXT,
            valor_novo TEXT,
            motivo TEXT,
            actor TEXT,
            criado_em TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (agendamento_id) REFERENCES agendamentos(id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_agendamento_historico_ag ON agendamento_historico(agendamento_id)"
    )


def _migrate_venda_pagamentos_meio_iban_if_needed(cursor) -> None:
    """E21: inclui `iban` no CHECK de `venda_pagamentos` (SQLite não altera CHECK in-place)."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='venda_pagamentos'"
    )
    if cursor.fetchone() is None:
        return
    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='venda_pagamentos'"
    )
    row = cursor.fetchone()
    sql = (row[0] or "") if row else ""
    if "iban" in sql:
        return
    cursor.execute("PRAGMA foreign_keys=OFF")
    cursor.execute(
        """
        CREATE TABLE venda_pagamentos_e21_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER NOT NULL,
            ordem INTEGER NOT NULL,
            meio TEXT NOT NULL CHECK (
                meio IN ('dinheiro', 'cartao_credito', 'mbway', 'iban')
            ),
            valor_centavos INTEGER NOT NULL CHECK (valor_centavos >= 0),
            FOREIGN KEY (venda_id) REFERENCES vendas(id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        """
        INSERT INTO venda_pagamentos_e21_new (id, venda_id, ordem, meio, valor_centavos)
        SELECT id, venda_id, ordem, meio, valor_centavos FROM venda_pagamentos
        """
    )
    cursor.execute("DROP TABLE venda_pagamentos")
    cursor.execute("ALTER TABLE venda_pagamentos_e21_new RENAME TO venda_pagamentos")
    cursor.execute("PRAGMA foreign_keys=ON")


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


def _fin_count_lancamentos_tipo(cursor: sqlite3.Cursor, tipo_id: int) -> int:
    tabs = {r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "financeiro_gasto_lancamentos" not in tabs:
        return 0
    r = cursor.execute(
        "SELECT COUNT(*) FROM financeiro_gasto_lancamentos WHERE tipo_gasto_id = ?",
        (int(tipo_id),),
    ).fetchone()
    return int(r[0] or 0)


def _chave_dup_nome_fin(s: str) -> str:
    """Import tardio: evita ciclo connection ↔ `src.modules` (o __init__ importa cliente)."""
    from src.modules.financeiro_nome_normalizacao import chave_duplicacao_nome

    return chave_duplicacao_nome(s)


def _dedupe_fin_tipos_ci(cursor: sqlite3.Cursor) -> None:
    """Desactiva tipos activos duplicados (mesma natureza + mesmo nome: caixa e acentos)."""
    cursor.execute(
        "SELECT id, nome, natureza_id FROM financeiro_tipo_gasto WHERE ativo = 1"
    )
    groups: dict[tuple[int, str], list[int]] = {}
    for tid, nome, nid in cursor.fetchall():
        k = (int(nid), _chave_dup_nome_fin(str(nome)))
        groups.setdefault(k, []).append(int(tid))
    for _k, ids in groups.items():
        if len(ids) < 2:
            continue
        keeper = sorted(ids, key=lambda tid: (-_fin_count_lancamentos_tipo(cursor, tid), tid))[0]
        for tid in ids:
            if tid != keeper:
                cursor.execute("UPDATE financeiro_tipo_gasto SET ativo = 0 WHERE id = ?", (tid,))


def _dedupe_fin_naturezas_ci(cursor: sqlite3.Cursor) -> None:
    """Reatribui tipos e desactiva naturezas duplicadas (mesmo centro + nome: caixa e acentos)."""
    cursor.execute("SELECT id, nome, centro_custo_id FROM financeiro_natureza WHERE ativo = 1")
    groups: dict[tuple[int, str], list[int]] = {}
    for nid, nome, cid in cursor.fetchall():
        k = (int(cid), _chave_dup_nome_fin(str(nome)))
        groups.setdefault(k, []).append(int(nid))
    for _k, ids in groups.items():
        if len(ids) < 2:
            continue
        ids = sorted(ids)
        keeper = ids[0]
        for rid in ids[1:]:
            cursor.execute(
                """
                UPDATE financeiro_tipo_gasto SET natureza_id = ?
                WHERE natureza_id = ? AND ativo = 1
                """,
                (keeper, rid),
            )
            cursor.execute("UPDATE financeiro_natureza SET ativo = 0 WHERE id = ?", (rid,))


def _dedupe_fin_centros_ci(cursor: sqlite3.Cursor) -> None:
    """Reatribui naturezas e desactiva centros duplicados (mesmo nome: caixa e acentos)."""
    cursor.execute("SELECT id, nome FROM financeiro_centro_custo WHERE ativo = 1")
    groups: dict[str, list[int]] = {}
    for cid, nome in cursor.fetchall():
        k = _chave_dup_nome_fin(str(nome))
        groups.setdefault(k, []).append(int(cid))
    for _k, ids in groups.items():
        if len(ids) < 2:
            continue
        ids = sorted(ids)
        keeper = ids[0]
        for rid in ids[1:]:
            cursor.execute(
                """
                UPDATE financeiro_natureza SET centro_custo_id = ?
                WHERE centro_custo_id = ? AND ativo = 1
                """,
                (keeper, rid),
            )
            cursor.execute("UPDATE financeiro_centro_custo SET ativo = 0 WHERE id = ?", (rid,))


def _ensure_financeiro_case_insensitive_unique_indexes(cursor: sqlite3.Cursor) -> None:
    """
    Índices únicos por LOWER(TRIM(nome)) na BD (maiúsculas + espaços); duplicados com acentos
    diferentes são consolidados na migração e bloqueados na aplicação via chave canónica.
    """
    tabs = {r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "financeiro_centro_custo" not in tabs:
        return
    for name in (
        "uq_fin_cc_nome_ativo",
        "uq_fin_nat_cc_nome_ativo",
        "uq_fin_tipo_nat_nome_ativo",
        "uq_fin_cc_nome_ci_ativo",
        "uq_fin_nat_cc_nome_ci_ativo",
        "uq_fin_tipo_nat_nome_ci_ativo",
    ):
        cursor.execute(f"DROP INDEX IF EXISTS {name}")
    for _ in range(4):
        _dedupe_fin_centros_ci(cursor)
        _dedupe_fin_naturezas_ci(cursor)
        _dedupe_fin_tipos_ci(cursor)
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_fin_cc_nome_ci_ativo "
        "ON financeiro_centro_custo(LOWER(TRIM(nome))) WHERE ativo = 1"
    )
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_fin_nat_cc_nome_ci_ativo "
        "ON financeiro_natureza(centro_custo_id, LOWER(TRIM(nome))) WHERE ativo = 1"
    )
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_fin_tipo_nat_nome_ci_ativo "
        "ON financeiro_tipo_gasto(natureza_id, LOWER(TRIM(nome))) WHERE ativo = 1"
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
        ("nif_ou_documento", "TEXT"),
        ("identificacao_internacional", "INTEGER NOT NULL DEFAULT 0"),
        ("data_nascimento", "TEXT"),
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
        CREATE TABLE IF NOT EXISTS especialidades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            natureza TEXT NOT NULL,
            nome TEXT NOT NULL,
            descritivo TEXT NOT NULL DEFAULT '',
            ativo INTEGER NOT NULL DEFAULT 1,
            ordem INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_especialidades_nat_nome ON especialidades(natureza, nome)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_especialidades_nat_ativo ON especialidades(natureza, ativo)"
    )
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
    _ensure_column(cursor, "servicos", "especialidade_id", "INTEGER")
    _migrate_especialidades_if_needed(cursor)
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
    _ensure_column(cursor, "colaboradores", "nif_ou_documento", "TEXT")
    _ensure_column(cursor, "colaboradores", "identificacao_internacional", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(cursor, "colaboradores", "documento_passaporte_residencia_cc", "TEXT DEFAULT ''")
    _ensure_column(cursor, "colaboradores", "atividade_economica_aberta", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(cursor, "colaboradores", "atividade_economica_codigo", "TEXT DEFAULT ''")
    _ensure_column(cursor, "colaboradores", "atividade_economica_descricao", "TEXT DEFAULT ''")
    _ensure_column(cursor, "colaboradores", "contrato_prestacao_assinado", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(cursor, "colaboradores", "contrato_prestacao_data_assinatura", "TEXT DEFAULT ''")
    _ensure_column(cursor, "colaboradores", "iban_dados_bancarios", "TEXT DEFAULT ''")
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
    _ensure_column(
        cursor,
        "venda_itens",
        "pagamento_parcial",
        "INTEGER NOT NULL DEFAULT 0 CHECK (pagamento_parcial IN (0, 1))",
    )
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
                meio IN ('dinheiro', 'cartao_credito', 'mbway', 'iban')
            ),
            valor_centavos INTEGER NOT NULL CHECK (valor_centavos >= 0),
            FOREIGN KEY (venda_id) REFERENCES vendas(id) ON DELETE CASCADE
        )
        """
    )
    _migrate_venda_pagamentos_meio_iban_if_needed(cursor)
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
                status IN (
                    'PRE_AGENDADO',
                    'AGENDADO',
                    'CONFIRMADO',
                    'REALIZADO_PENDENTE_PGTO',
                    'CONCLUIDO',
                    'CANCELADO'
                )
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
            tipo_atendimento TEXT NOT NULL DEFAULT 'presencial' CHECK (
                tipo_atendimento IN ('presencial', 'virtual')
            ),
            sala_virtual_disponibilizada INTEGER CHECK (
                sala_virtual_disponibilizada IS NULL
                OR sala_virtual_disponibilizada IN (0, 1)
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
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS financeiro_centro_custo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS financeiro_natureza (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            centro_custo_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            FOREIGN KEY (centro_custo_id) REFERENCES financeiro_centro_custo(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS financeiro_tipo_gasto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            natureza_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            FOREIGN KEY (natureza_id) REFERENCES financeiro_natureza(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS financeiro_gasto_lancamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_gasto_id INTEGER NOT NULL,
            observacao TEXT NOT NULL DEFAULT '',
            valor_centavos INTEGER NOT NULL DEFAULT 0 CHECK (valor_centavos >= 0),
            data_registo TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (tipo_gasto_id) REFERENCES financeiro_tipo_gasto(id)
        )
        """
    )
    _ensure_financeiro_case_insensitive_unique_indexes(cursor)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_fin_lanc_tipo ON financeiro_gasto_lancamentos(tipo_gasto_id)"
    )
    _ensure_financeiro_lancamentos_extras(cursor)
    _migrate_agendamentos_e11_if_needed(cursor)
    _ensure_column(
        cursor,
        "vendas",
        "agendamento_contexto_id",
        "INTEGER REFERENCES agendamentos(id) ON DELETE SET NULL",
    )
    _ensure_column(
        cursor,
        "vendas",
        "fatura_solicitada",
        "INTEGER DEFAULT 0",
    )
    _ensure_column(
        cursor,
        "vendas",
        "fatura_emitida",
        "INTEGER DEFAULT 0",
    )
    _ensure_column(
        cursor,
        "vendas",
        "fatura_numero",
        "TEXT",
    )
    _migrate_e18_if_needed(cursor)
    _ensure_column(
        cursor,
        "agendamentos",
        "tipo_atendimento",
        "TEXT NOT NULL DEFAULT 'presencial'",
    )
    _ensure_column(
        cursor,
        "agendamentos",
        "sala_virtual_disponibilizada",
        "INTEGER",
    )
    _ensure_column(
        cursor,
        "agendamentos",
        "data_criacao_registo",
        "TEXT",
    )
    cursor.execute(
        """
        UPDATE agendamentos
        SET data_criacao_registo = COALESCE(
            NULLIF(TRIM(data_criacao_registo), ''),
            REPLACE(REPLACE(IFNULL(data_alteracao, ''), 'T', ' '), 'Z', '')
        )
        WHERE data_criacao_registo IS NULL OR TRIM(data_criacao_registo) = ''
        """
    )
    conn.commit()
    conn.close()
