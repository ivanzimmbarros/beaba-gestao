"""Categorias de gastos operacionais — hierarquia Centro de Custo → Natureza → Tipo de gasto.

Regras: natureza exige centro; tipo exige natureza (e portanto centro).
Imutabilidade: com lançamentos em `financeiro_gasto_lancamentos`, alterações a tipo/natureza
usam desactivação lógica (ativo=0) + novo registo; sem lançamentos, UPDATE in-place.
"""

from __future__ import annotations

import sqlite3

from src.database.connection import get_connection
from src.modules.financeiro_nome_normalizacao import chave_duplicacao_nome

_T_LANCAMENTOS = "financeiro_gasto_lancamentos"

# Duplicado na mesma hierarquia (centro, natureza ou tipo).
MSG_REGISTRO_DUPLICADO = "Registo Duplicado. Operação não pode ser concluída."
# Sentinela para a UI pedir confirmação antes de alterar tipo existente.
MSG_PEDIR_CONFIRMACAO_ALTERACAO = "__FIN_GXC_CONFIRMAR_ALTERACAO__"


def _conn(c: sqlite3.Connection | None = None) -> sqlite3.Connection:
    if c is not None:
        return c
    out = get_connection()
    if out is None:
        raise RuntimeError("Sem ligação à base de dados.")
    return out


def _tabela_existe(cursor: sqlite3.Cursor, nome: str) -> bool:
    r = cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (nome,),
    ).fetchone()
    return r is not None


def _id_centro_por_chave_dup(conn: sqlite3.Connection, nome: str) -> int | None:
    k = chave_duplicacao_nome(nome)
    if not k:
        return None
    for rid, rnome in conn.execute(
        "SELECT id, nome FROM financeiro_centro_custo WHERE ativo = 1"
    ).fetchall():
        if chave_duplicacao_nome(str(rnome)) == k:
            return int(rid)
    return None


def _id_natureza_por_chave_dup(conn: sqlite3.Connection, centro_custo_id: int, nome: str) -> int | None:
    k = chave_duplicacao_nome(nome)
    if not k:
        return None
    for rid, rnome in conn.execute(
        "SELECT id, nome FROM financeiro_natureza WHERE ativo = 1 AND centro_custo_id = ?",
        (int(centro_custo_id),),
    ).fetchall():
        if chave_duplicacao_nome(str(rnome)) == k:
            return int(rid)
    return None


def _id_tipo_por_chave_dup(conn: sqlite3.Connection, natureza_id: int, nome: str) -> int | None:
    k = chave_duplicacao_nome(nome)
    if not k:
        return None
    for rid, rnome in conn.execute(
        "SELECT id, nome FROM financeiro_tipo_gasto WHERE ativo = 1 AND natureza_id = ?",
        (int(natureza_id),),
    ).fetchall():
        if chave_duplicacao_nome(str(rnome)) == k:
            return int(rid)
    return None


def tipo_tem_lancamentos(conn: sqlite3.Connection, tipo_gasto_id: int) -> bool:
    if not _tabela_existe(conn.cursor(), _T_LANCAMENTOS):
        return False
    n = conn.execute(
        f'SELECT COUNT(*) FROM "{_T_LANCAMENTOS}" WHERE tipo_gasto_id = ?',
        (int(tipo_gasto_id),),
    ).fetchone()[0]
    return int(n or 0) > 0


def natureza_tem_lancamentos(conn: sqlite3.Connection, natureza_id: int) -> bool:
    """Verdadeiro se algum tipo activo sob esta natureza tiver lançamentos."""
    if not _tabela_existe(conn.cursor(), _T_LANCAMENTOS):
        return False
    n = conn.execute(
        f"""
        SELECT COUNT(*) FROM "{_T_LANCAMENTOS}" g
        INNER JOIN financeiro_tipo_gasto t ON t.id = g.tipo_gasto_id
        WHERE t.natureza_id = ?
        """,
        (int(natureza_id),),
    ).fetchone()[0]
    return int(n or 0) > 0


def listar_naturezas_ativas_com_rotulo(conn: sqlite3.Connection) -> list[tuple[int, str]]:
    """(id, «Centro — Natureza») para multiselect de filtro."""
    cur = conn.execute(
        """
        SELECT n.id, c.nome || ' — ' || n.nome
        FROM financeiro_natureza n
        INNER JOIN financeiro_centro_custo c ON c.id = n.centro_custo_id AND c.ativo = 1
        WHERE n.ativo = 1
        ORDER BY c.nome COLLATE NOCASE, n.nome COLLATE NOCASE
        """
    )
    return [(int(r[0]), str(r[1])) for r in cur.fetchall()]


def listar_tipos_ativos_com_rotulo(conn: sqlite3.Connection) -> list[tuple[int, str]]:
    """(id, «Centro · Natureza · Tipo») para multiselect de filtro."""
    cur = conn.execute(
        """
        SELECT t.id, c.nome || ' · ' || n.nome || ' · ' || t.nome
        FROM financeiro_tipo_gasto t
        INNER JOIN financeiro_natureza n ON n.id = t.natureza_id AND n.ativo = 1
        INNER JOIN financeiro_centro_custo c ON c.id = n.centro_custo_id AND c.ativo = 1
        WHERE t.ativo = 1
        ORDER BY c.nome COLLATE NOCASE, n.nome COLLATE NOCASE, t.nome COLLATE NOCASE
        """
    )
    return [(int(r[0]), str(r[1])) for r in cur.fetchall()]


def listar_naturezas_ativas_so_nome(conn: sqlite3.Connection) -> list[tuple[int, str]]:
    """(id, nome) — só o nome gravado na natureza (filtros sem caminho hierárquico)."""
    cur = conn.execute(
        """
        SELECT id, nome FROM financeiro_natureza
        WHERE ativo = 1
        ORDER BY nome COLLATE NOCASE
        """
    )
    return [(int(r[0]), str(r[1])) for r in cur.fetchall()]


def listar_tipos_gasto_ativos_so_nome(conn: sqlite3.Connection) -> list[tuple[int, str]]:
    """(id, nome) — só o nome gravado no tipo de gasto (filtros sem caminho hierárquico)."""
    cur = conn.execute(
        """
        SELECT id, nome FROM financeiro_tipo_gasto
        WHERE ativo = 1
        ORDER BY nome COLLATE NOCASE
        """
    )
    return [(int(r[0]), str(r[1])) for r in cur.fetchall()]


def listar_centros_custo_ativos(conn: sqlite3.Connection | None = None) -> list[tuple[int, str]]:
    cx = _conn(conn)
    cur = cx.execute(
        "SELECT id, nome FROM financeiro_centro_custo WHERE ativo = 1 ORDER BY nome COLLATE NOCASE"
    )
    return [(int(r[0]), str(r[1])) for r in cur.fetchall()]


def listar_naturezas_por_centro_ativas(
    conn: sqlite3.Connection, centro_custo_id: int
) -> list[tuple[int, str]]:
    cur = conn.execute(
        """
        SELECT id, nome FROM financeiro_natureza
        WHERE ativo = 1 AND centro_custo_id = ?
        ORDER BY nome COLLATE NOCASE
        """,
        (int(centro_custo_id),),
    )
    return [(int(r[0]), str(r[1])) for r in cur.fetchall()]


def listar_tipos_por_natureza_ativos(
    conn: sqlite3.Connection, natureza_id: int
) -> list[tuple[int, str]]:
    cur = conn.execute(
        """
        SELECT id, nome FROM financeiro_tipo_gasto
        WHERE ativo = 1 AND natureza_id = ?
        ORDER BY nome COLLATE NOCASE
        """,
        (int(natureza_id),),
    )
    return [(int(r[0]), str(r[1])) for r in cur.fetchall()]


def obter_tipo_com_caminho(
    conn: sqlite3.Connection, tipo_id: int
) -> dict | None:
    row = conn.execute(
        """
        SELECT
            t.id AS tipo_id,
            t.nome AS tipo_nome,
            t.natureza_id,
            n.nome AS natureza_nome,
            n.centro_custo_id,
            c.nome AS centro_nome
        FROM financeiro_tipo_gasto t
        INNER JOIN financeiro_natureza n ON n.id = t.natureza_id
        INNER JOIN financeiro_centro_custo c ON c.id = n.centro_custo_id
        WHERE t.id = ? AND t.ativo = 1
        """,
        (int(tipo_id),),
    ).fetchone()
    if not row:
        return None
    return {
        "tipo_id": int(row[0]),
        "tipo_nome": str(row[1]),
        "natureza_id": int(row[2]),
        "natureza_nome": str(row[3]),
        "centro_custo_id": int(row[4]),
        "centro_nome": str(row[5]),
    }


def _obter_ou_criar_centro_ativo(conn: sqlite3.Connection, nome: str) -> tuple[int, bool]:
    """Devolve (id, criado)."""
    nome = nome.strip()
    if not nome:
        raise ValueError("Nome do centro de custo vazio.")
    cid = _id_centro_por_chave_dup(conn, nome)
    if cid is not None:
        return cid, False
    cur = conn.execute(
        "INSERT INTO financeiro_centro_custo (nome, ativo) VALUES (?, 1)",
        (nome,),
    )
    return int(cur.lastrowid), True


def _obter_ou_criar_natureza_ativa(conn: sqlite3.Connection, centro_id: int, nome: str) -> tuple[int, bool]:
    nome = nome.strip()
    if not nome:
        raise ValueError("Nome da natureza vazio.")
    nid = _id_natureza_por_chave_dup(conn, int(centro_id), nome)
    if nid is not None:
        return nid, False
    cur = conn.execute(
        "INSERT INTO financeiro_natureza (centro_custo_id, nome, ativo) VALUES (?, ?, 1)",
        (int(centro_id), nome),
    )
    return int(cur.lastrowid), True


def _validar_natureza_pertenece_centro(conn: sqlite3.Connection, natureza_id: int, centro_id: int) -> bool:
    r = conn.execute(
        """
        SELECT 1 FROM financeiro_natureza
        WHERE id = ? AND centro_custo_id = ? AND ativo = 1
        """,
        (int(natureza_id), int(centro_id)),
    ).fetchone()
    return r is not None


def listar_linhas_tabela_tipos(
    conn: sqlite3.Connection,
    *,
    filtro_centro_ids: list[int] | None = None,
    filtro_natureza_ids: list[int] | None = None,
    filtro_tipo_ids: list[int] | None = None,
) -> list[dict]:
    """
    Uma linha por tipo de gasto activo; nomes de centro e natureza para exibição.
    Filtros: listas vazias ou None => não filtra nessa dimensão.
    """
    filtro_centro_ids = filtro_centro_ids or []
    filtro_natureza_ids = filtro_natureza_ids or []
    filtro_tipo_ids = filtro_tipo_ids or []
    sql = """
        SELECT t.id, c.nome, n.nome, t.nome
        FROM financeiro_tipo_gasto t
        INNER JOIN financeiro_natureza n ON n.id = t.natureza_id AND n.ativo = 1
        INNER JOIN financeiro_centro_custo c ON c.id = n.centro_custo_id AND c.ativo = 1
        WHERE t.ativo = 1
    """
    params: list = []
    if filtro_centro_ids:
        sql += " AND c.id IN (" + ",".join("?" for _ in filtro_centro_ids) + ")"
        params.extend(int(x) for x in filtro_centro_ids)
    if filtro_natureza_ids:
        sql += " AND n.id IN (" + ",".join("?" for _ in filtro_natureza_ids) + ")"
        params.extend(int(x) for x in filtro_natureza_ids)
    if filtro_tipo_ids:
        sql += " AND t.id IN (" + ",".join("?" for _ in filtro_tipo_ids) + ")"
        params.extend(int(x) for x in filtro_tipo_ids)
    sql += " ORDER BY c.nome COLLATE NOCASE, n.nome COLLATE NOCASE, t.nome COLLATE NOCASE"
    cur = conn.execute(sql, params)
    return [
        {
            "tipo_id": int(r[0]),
            "centro_nome": str(r[1]),
            "natureza_nome": str(r[2]),
            "tipo_nome": str(r[3]),
        }
        for r in cur.fetchall()
    ]


def salvar_linha1_apenas_centro_custo(conn: sqlite3.Connection, nome_centro: str) -> tuple[bool, str]:
    """Linha 1 só com texto «Centro de Custo»: insere se o nome ainda não existir (activo)."""
    nome = (nome_centro or "").strip()
    if not nome:
        return False, "Indique o nome do Centro de Custo na linha 1."
    if _id_centro_por_chave_dup(conn, nome) is not None:
        return False, MSG_REGISTRO_DUPLICADO
    try:
        conn.execute(
            "INSERT INTO financeiro_centro_custo (nome, ativo) VALUES (?, 1)",
            (nome,),
        )
        return True, "Centro de Custo criado com sucesso."
    except sqlite3.IntegrityError as e:
        return False, f"Dados em conflito: {e}"


def salvar_linha1_tres_textos(conn: sqlite3.Connection, cc: str, nat: str, tipo: str) -> tuple[bool, str]:
    """Linha 1: cria centro, natureza e tipo numa única cadeia; rejeita qualquer duplicado na hierarquia."""
    cc, nat, tipo = cc.strip(), nat.strip(), tipo.strip()
    if not cc or not nat or not tipo:
        return False, "Preencha Centro de Custo, Natureza e Tipo de Gasto na linha 1."
    try:
        if _id_centro_por_chave_dup(conn, cc) is not None:
            return False, MSG_REGISTRO_DUPLICADO
        cur = conn.execute(
            "INSERT INTO financeiro_centro_custo (nome, ativo) VALUES (?, 1)",
            (cc,),
        )
        cid = int(cur.lastrowid)
        if _id_natureza_por_chave_dup(conn, cid, nat) is not None:
            return False, MSG_REGISTRO_DUPLICADO
        cur = conn.execute(
            "INSERT INTO financeiro_natureza (centro_custo_id, nome, ativo) VALUES (?, ?, 1)",
            (cid, nat),
        )
        nid = int(cur.lastrowid)
        if _id_tipo_por_chave_dup(conn, nid, tipo) is not None:
            return False, MSG_REGISTRO_DUPLICADO
        conn.execute(
            "INSERT INTO financeiro_tipo_gasto (natureza_id, nome, ativo) VALUES (?, ?, 1)",
            (nid, tipo),
        )
        return True, "Tipo de Gasto criado com sucesso."
    except sqlite3.IntegrityError as e:
        return False, f"Dados em conflito com regras da base: {e}"


def salvar_linha2_centro_e_natureza_texto(
    conn: sqlite3.Connection, centro_custo_id: int, natureza_nome: str
) -> tuple[bool, str]:
    natureza_nome = natureza_nome.strip()
    if not natureza_nome:
        return False, "Indique o nome da Natureza na linha 2."
    row = conn.execute(
        "SELECT id FROM financeiro_centro_custo WHERE id = ? AND ativo = 1",
        (int(centro_custo_id),),
    ).fetchone()
    if not row:
        return False, "Centro de Custo seleccionado inválido."
    if _id_natureza_por_chave_dup(conn, int(centro_custo_id), natureza_nome) is not None:
        return False, MSG_REGISTRO_DUPLICADO
    try:
        conn.execute(
            "INSERT INTO financeiro_natureza (centro_custo_id, nome, ativo) VALUES (?, ?, 1)",
            (int(centro_custo_id), natureza_nome),
        )
        return True, "Natureza de Gasto criada com sucesso."
    except sqlite3.IntegrityError as e:
        return False, f"Dados em conflito: {e}"


def salvar_linha3_centro_natureza_e_tipo_texto(
    conn: sqlite3.Connection,
    centro_custo_id: int,
    natureza_id: int,
    tipo_nome: str,
) -> tuple[bool, str]:
    tipo_nome = tipo_nome.strip()
    if not tipo_nome:
        return False, "Indique o nome do Tipo de Gasto na linha 3."
    if not _validar_natureza_pertenece_centro(conn, natureza_id, centro_custo_id):
        return False, "A Natureza seleccionada não pertence ao Centro de Custo indicado."
    if _id_tipo_por_chave_dup(conn, int(natureza_id), tipo_nome) is not None:
        return False, MSG_REGISTRO_DUPLICADO
    try:
        conn.execute(
            "INSERT INTO financeiro_tipo_gasto (natureza_id, nome, ativo) VALUES (?, ?, 1)",
            (int(natureza_id), tipo_nome),
        )
        return True, "Tipo de Gasto criado com sucesso."
    except sqlite3.IntegrityError as e:
        return False, f"Dados em conflito: {e}"


def atualizar_tipo_a_partir_formulario(
    conn: sqlite3.Connection,
    tipo_id: int,
    centro_custo_id: int,
    natureza_id: int,
    novo_nome_tipo: str,
) -> tuple[bool, str]:
    """
    Actualiza tipo existente (selecção na tabela). Valida natureza ⊂ centro.
    Desactivação + insert se `tipo_tem_lancamentos`; caso contrário UPDATE in-place.
    Também desactiva+novo se mudar natureza_id (cadeia) com lançamentos, ou UPDATE FK se não houver.
    """
    novo_nome_tipo = novo_nome_tipo.strip()
    if not novo_nome_tipo:
        return False, "O nome do Tipo de Gasto não pode ficar vazio."
    if not _validar_natureza_pertenece_centro(conn, natureza_id, centro_custo_id):
        return False, "A Natureza seleccionada não pertence ao Centro de Custo indicado."

    path = obter_tipo_com_caminho(conn, tipo_id)
    if not path:
        return False, "Tipo de gasto não encontrado ou inactivo."

    same_nat = int(path["natureza_id"]) == int(natureza_id)
    same_nome = chave_duplicacao_nome(path["tipo_nome"]) == chave_duplicacao_nome(novo_nome_tipo)
    if same_nat and same_nome:
        return True, "Nenhuma alteração a gravar."

    tem = tipo_tem_lancamentos(conn, tipo_id)

    if same_nat:
        if tem:
            oid = _id_tipo_por_chave_dup(conn, int(natureza_id), novo_nome_tipo)
            if oid is not None and oid != int(tipo_id):
                return False, MSG_REGISTRO_DUPLICADO
            conn.execute("UPDATE financeiro_tipo_gasto SET ativo = 0 WHERE id = ?", (int(tipo_id),))
            conn.execute(
                """
                INSERT INTO financeiro_tipo_gasto (natureza_id, nome, ativo)
                VALUES (?, ?, 1)
                """,
                (int(natureza_id), novo_nome_tipo),
            )
        else:
            oid = _id_tipo_por_chave_dup(conn, int(natureza_id), novo_nome_tipo)
            if oid is not None and oid != int(tipo_id):
                return False, MSG_REGISTRO_DUPLICADO
            conn.execute(
                "UPDATE financeiro_tipo_gasto SET nome = ? WHERE id = ?",
                (novo_nome_tipo, int(tipo_id)),
            )
        return True, "Dados alterados com sucesso."

    # Mudou natureza (relocalização)
    if tem:
        oid = _id_tipo_por_chave_dup(conn, int(natureza_id), novo_nome_tipo)
        if oid is not None and oid != int(tipo_id):
            return False, MSG_REGISTRO_DUPLICADO
        conn.execute("UPDATE financeiro_tipo_gasto SET ativo = 0 WHERE id = ?", (int(tipo_id),))
        conn.execute(
            """
            INSERT INTO financeiro_tipo_gasto (natureza_id, nome, ativo)
            VALUES (?, ?, 1)
            """,
            (int(natureza_id), novo_nome_tipo),
        )
        return True, "Dados alterados com sucesso."

    oid = _id_tipo_por_chave_dup(conn, int(natureza_id), novo_nome_tipo)
    if oid is not None and oid != int(tipo_id):
        return False, MSG_REGISTRO_DUPLICADO
    conn.execute(
        "UPDATE financeiro_tipo_gasto SET natureza_id = ?, nome = ? WHERE id = ?",
        (int(natureza_id), novo_nome_tipo, int(tipo_id)),
    )
    return True, "Dados alterados com sucesso."


def actualizar_nome_natureza_se_sem_lancamentos(
    conn: sqlite3.Connection, natureza_id: int, novo_nome: str
) -> tuple[bool, str]:
    """Reservado para evoluções (edição directa de natureza); hoje só in-place sem lançamentos."""
    novo_nome = novo_nome.strip()
    if not novo_nome:
        return False, "Nome da natureza vazio."
    if natureza_tem_lancamentos(conn, natureza_id):
        return (
            False,
            "Esta Natureza tem lançamentos vinculados — não é permitido renomear in-place.",
        )
    row = conn.execute(
        "SELECT id, centro_custo_id FROM financeiro_natureza WHERE id = ? AND ativo = 1",
        (int(natureza_id),),
    ).fetchone()
    if not row:
        return False, "Natureza não encontrada."
    cid = int(row[1])
    kn = chave_duplicacao_nome(novo_nome)
    for oid, onome in conn.execute(
        """
        SELECT id, nome FROM financeiro_natureza
        WHERE ativo = 1 AND centro_custo_id = ? AND id != ?
        """,
        (cid, int(natureza_id)),
    ).fetchall():
        if chave_duplicacao_nome(str(onome)) == kn:
            return False, "Já existe outra Natureza activa com este nome neste Centro de Custo."
    conn.execute(
        "UPDATE financeiro_natureza SET nome = ? WHERE id = ?",
        (novo_nome, int(natureza_id)),
    )
    return True, ""


def actualizar_nome_centro_custo(conn: sqlite3.Connection, centro_id: int, novo_nome: str) -> tuple[bool, str]:
    """Centro: sempre UPDATE in-place (regra do Diretor)."""
    novo_nome = novo_nome.strip()
    if not novo_nome:
        return False, "Nome do centro de custo vazio."
    row = conn.execute(
        "SELECT id FROM financeiro_centro_custo WHERE id = ? AND ativo = 1",
        (int(centro_id),),
    ).fetchone()
    if not row:
        return False, "Centro de custo não encontrado."
    oid = _id_centro_por_chave_dup(conn, novo_nome)
    if oid is not None and oid != int(centro_id):
        return False, "Já existe outro Centro de Custo activo com este nome."
    conn.execute(
        "UPDATE financeiro_centro_custo SET nome = ? WHERE id = ?",
        (novo_nome, int(centro_id)),
    )
    return True, ""


def resolver_salvar_formulario(
    conn: sqlite3.Connection,
    *,
    linha1_cc: str,
    linha1_natureza: str,
    linha1_tipo: str,
    linha2_centro_id: int | None,
    linha2_natureza_texto: str,
    linha3_centro_id: int | None,
    linha3_natureza_id: int | None,
    linha3_tipo_texto: str,
    editando_tipo_id: int | None,
    confirmar_alteracao: bool = False,
) -> tuple[bool, str]:
    """
    Prioridade: linha 3 (combinação: insere tipo novo ou altera tipo existente) >
    linha 2 > linha 1 só centro > linha 1 legada (três textos).

    Alterações a tipo existente exigem `confirmar_alteracao=True` após confirmação na UI;
    até lá devolve `MSG_PEDIR_CONFIRMACAO_ALTERACAO`.
    """
    if linha3_centro_id is not None and linha3_natureza_id is not None and linha3_tipo_texto.strip():
        return _resolver_linha3_centro_natureza_tipo(
            conn,
            linha1_cc=linha1_cc,
            linha1_natureza=linha1_natureza,
            linha3_centro_id=int(linha3_centro_id),
            linha3_natureza_id=int(linha3_natureza_id),
            linha3_tipo_texto=linha3_tipo_texto,
            editando_tipo_id=editando_tipo_id,
            confirmar_alteracao=confirmar_alteracao,
        )

    if linha2_centro_id is not None and linha2_natureza_texto.strip():
        return salvar_linha2_centro_e_natureza_texto(conn, int(linha2_centro_id), linha2_natureza_texto)

    only_l1_centro = (
        bool(linha1_cc.strip())
        and not (linha1_natureza or "").strip()
        and not (linha1_tipo or "").strip()
    )
    if only_l1_centro:
        return salvar_linha1_apenas_centro_custo(conn, linha1_cc)

    t1 = linha1_cc.strip() and linha1_natureza.strip() and linha1_tipo.strip()
    if t1:
        return salvar_linha1_tres_textos(conn, linha1_cc, linha1_natureza, linha1_tipo)

    return (
        False,
        "Preencha a linha 1 (nome do centro), ou a linha 2 (centro + natureza), ou a linha 3 (centro + natureza + tipo).",
    )


def _ha_mudanca_tipo_formulario(
    conn: sqlite3.Connection,
    tipo_id: int,
    centro_custo_id: int,
    natureza_id: int,
    tipo_nome: str,
    linha1_cc: str,
    linha1_natureza: str,
) -> bool:
    """Verdadeiro se centro, natureza, tipo ou textos da linha 1 divergem do registo actual."""
    path = obter_tipo_com_caminho(conn, int(tipo_id))
    if not path:
        return True
    if int(path["centro_custo_id"]) != int(centro_custo_id):
        return True
    if int(path["natureza_id"]) != int(natureza_id):
        return True
    if chave_duplicacao_nome(path["tipo_nome"]) != chave_duplicacao_nome(tipo_nome):
        return True
    cc1 = (linha1_cc or "").strip()
    na1 = (linha1_natureza or "").strip()
    if cc1 and chave_duplicacao_nome(cc1) != chave_duplicacao_nome(str(path["centro_nome"])):
        return True
    if na1 and chave_duplicacao_nome(na1) != chave_duplicacao_nome(str(path["natureza_nome"])):
        return True
    return False


def _resolver_linha3_centro_natureza_tipo(
    conn: sqlite3.Connection,
    *,
    linha1_cc: str,
    linha1_natureza: str,
    linha3_centro_id: int,
    linha3_natureza_id: int,
    linha3_tipo_texto: str,
    editando_tipo_id: int | None,
    confirmar_alteracao: bool,
) -> tuple[bool, str]:
    tnom = linha3_tipo_texto.strip()
    if not _validar_natureza_pertenece_centro(conn, int(linha3_natureza_id), int(linha3_centro_id)):
        return False, "A Natureza seleccionada não pertence ao Centro de Custo indicado."
    existing_id = _id_tipo_por_chave_dup(conn, int(linha3_natureza_id), tnom)

    if existing_id is not None:
        if editando_tipo_id is not None and int(editando_tipo_id) == existing_id:
            if not _ha_mudanca_tipo_formulario(
                conn,
                existing_id,
                int(linha3_centro_id),
                int(linha3_natureza_id),
                tnom,
                linha1_cc,
                linha1_natureza,
            ):
                return True, "Nenhuma alteração a gravar."
            if not confirmar_alteracao:
                return False, MSG_PEDIR_CONFIRMACAO_ALTERACAO
            ok_s, msg_s = sincronizar_nomes_superiores_apos_edicao_por_texto_linha1(
                conn,
                tipo_id=int(editando_tipo_id),
                novo_cc=linha1_cc,
                novo_nat=linha1_natureza,
            )
            if not ok_s:
                return False, msg_s
            return atualizar_tipo_a_partir_formulario(
                conn,
                int(editando_tipo_id),
                int(linha3_centro_id),
                int(linha3_natureza_id),
                tnom,
            )
        return False, MSG_REGISTRO_DUPLICADO

    if editando_tipo_id is not None:
        if not obter_tipo_com_caminho(conn, int(editando_tipo_id)):
            return False, "Tipo de gasto não encontrado ou inactivo."
        if not _ha_mudanca_tipo_formulario(
            conn,
            int(editando_tipo_id),
            int(linha3_centro_id),
            int(linha3_natureza_id),
            tnom,
            linha1_cc,
            linha1_natureza,
        ):
            return True, "Nenhuma alteração a gravar."
        if not confirmar_alteracao:
            return False, MSG_PEDIR_CONFIRMACAO_ALTERACAO
        ok_s, msg_s = sincronizar_nomes_superiores_apos_edicao_por_texto_linha1(
            conn,
            tipo_id=int(editando_tipo_id),
            novo_cc=linha1_cc,
            novo_nat=linha1_natureza,
        )
        if not ok_s:
            return False, msg_s
        return atualizar_tipo_a_partir_formulario(
            conn,
            int(editando_tipo_id),
            int(linha3_centro_id),
            int(linha3_natureza_id),
            tnom,
        )
    return salvar_linha3_centro_natureza_e_tipo_texto(
        conn, int(linha3_centro_id), int(linha3_natureza_id), tnom
    )


def sincronizar_nomes_superiores_apos_edicao_por_texto_linha1(
    conn: sqlite3.Connection,
    *,
    tipo_id: int,
    novo_cc: str,
    novo_nat: str,
) -> tuple[bool, str]:
    """
    Se o utilizador editou os textos da linha 1 (centro/natureza) com uma linha da tabela
    seleccionada, reflecte renomeações permitidas: centro e natureza in-place; natureza
    com lançamentos bloqueia rename in-place (mensagem).
    """
    path = obter_tipo_com_caminho(conn, tipo_id)
    if not path:
        return False, "Tipo de gasto não encontrado para sincronizar nomes."
    novo_cc = novo_cc.strip()
    novo_nat = novo_nat.strip()
    errs: list[str] = []
    if novo_cc and novo_cc != path["centro_nome"]:
        ok, msg = actualizar_nome_centro_custo(conn, path["centro_custo_id"], novo_cc)
        if not ok:
            errs.append(msg)
    if (novo_nat or "").strip() and (novo_nat or "").strip() != path["natureza_nome"]:
        ok, msg = actualizar_nome_natureza_se_sem_lancamentos(conn, path["natureza_id"], novo_nat.strip())
        if not ok:
            errs.append(msg)
    if errs:
        return False, " ".join(errs)
    return True, ""
