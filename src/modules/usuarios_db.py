"""Gestão de utilizadores da aplicação (perfil SQLite ``usuarios``) — administração."""

from __future__ import annotations

from typing import Any

from src.database.connection import get_connection
from src.modules.audit import log_audit
from src.modules.auth_utils import hash_password

_SENHA_INICIAL_PADRAO = "BemVindo123"
_PERFIS = frozenset({"admin", "usuario"})


def _notify_cloud_sync(*, auth_critical: bool = False) -> None:
    try:
        from scripts.sync_trigger import notify_auth_data_changed, notify_data_changed

        if auth_critical:
            notify_auth_data_changed()
        else:
            notify_data_changed()
    except Exception:
        pass


def _row_to_public(row: tuple[Any, ...]) -> dict[str, Any]:
    uid, nome, mail, perfil, ativo, mcp, dc = row
    return {
        "id": int(uid),
        "nome": str(nome),
        "email": str(mail),
        "perfil": str(perfil),
        "ativo": int(ativo),
        "must_change_password": int(mcp),
        "data_cadastro": str(dc) if dc is not None else "",
    }


def listar_usuarios() -> list[dict[str, Any]]:
    """Lista todos os utilizadores (sem ``senha_hash``)."""
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cols = {r[1] for r in cur.execute("PRAGMA table_info(usuarios)").fetchall()}
        if not cols:
            return []
        sel = (
            "SELECT id, nome, email, perfil, ativo, must_change_password, data_cadastro FROM usuarios "
            "ORDER BY id ASC"
        )
        cur.execute(sel)
        return [_row_to_public(r) for r in cur.fetchall()]
    finally:
        conn.close()


def _resolver_user_id_por_email(email: str) -> int | None:
    conn = get_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM usuarios WHERE LOWER(TRIM(email)) = LOWER(TRIM(?)) LIMIT 1",
            ((email or "").strip(),),
        )
        row = cur.fetchone()
        return int(row[0]) if row else None
    finally:
        conn.close()


def _contar_admins_ativos(cursor) -> int:
    r = cursor.execute(
        "SELECT COUNT(*) FROM usuarios WHERE LOWER(TRIM(perfil)) = 'admin' AND ativo = 1"
    ).fetchone()
    return int(r[0] or 0) if r else 0


def criar_usuario(nome: str, email: str, perfil: str, logged_user_email: str) -> int:
    """Cria utilizador com senha inicial ``BemVindo123``, ``must_change_password=1``.

    Raises:
        ValueError: e-mail ou perfil inválidos, perfil inconsistente ou e-mail já existente.
    """
    mail = (email or "").strip().lower()
    nome_n = (nome or "").strip()
    perf = (perfil or "").strip().lower()
    if not mail or not nome_n:
        raise ValueError("Nome e e-mail são obrigatórios.")
    if perf not in _PERFIS:
        raise ValueError("Perfil inválido (use admin ou usuario).")

    actor = (logged_user_email or "").strip() or "sistema"

    conn = get_connection()
    if not conn:
        raise ValueError("Não foi possível ligar à base de dados.")

    try:
        cur = conn.cursor()
        cols_table = {r[1] for r in cur.execute("PRAGMA table_info(usuarios)").fetchall()}
        if "must_change_password" not in cols_table:
            raise ValueError("Esquema ``usuarios`` desactualizado.")
        cur.execute(
            "SELECT 1 FROM usuarios WHERE LOWER(TRIM(email)) = LOWER(TRIM(?))",
            (mail,),
        )
        if cur.fetchone():
            raise ValueError("Este e-mail já está cadastrado.")

        cur.execute(
            """
            INSERT INTO usuarios (nome, email, senha_hash, perfil, ativo, must_change_password, data_cadastro)
            VALUES (?, ?, ?, ?, 1, 1, datetime('now'))
            """,
            (nome_n, mail, hash_password(_SENHA_INICIAL_PADRAO), perf),
        )
        new_id = int(cur.lastrowid)
        conn.commit()
        log_audit(
            ator_email=actor,
            acao="CREATE",
            modulo="usuarios",
            registro_id=str(new_id),
            dados_novos={"nome": nome_n, "email": mail, "perfil": perf, "ativo": 1},
        )
        _notify_cloud_sync(auth_critical=True)
        return new_id
    except ValueError:
        raise
    except Exception as exc:
        conn.rollback()
        raise ValueError(f"Não foi possível criar o utilizador: {exc!s}") from exc
    finally:
        conn.close()


def senha_padrao_inicial() -> str:
    """Senha de primeiro acesso (texto auxiliar para administração)."""
    return _SENHA_INICIAL_PADRAO


def atualizar_perfil(usuario_id: int, novo_perfil: str, logged_user_email: str) -> bool:
    perf = (novo_perfil or "").strip().lower()
    if perf not in _PERFIS:
        return False
    actor = (logged_user_email or "").strip() or "sistema"
    uid = int(usuario_id)
    actor_id = _resolver_user_id_por_email(actor)

    conn = get_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT perfil FROM usuarios WHERE id = ?",
            (uid,),
        )
        row = cur.fetchone()
        if not row:
            return False
        old_p = str(row[0]).strip().lower()
        if old_p == perf:
            return True
        # Não degradar o próprio utilizador ligado para não perder acesso de administração nesta sessão.
        if actor_id is not None and uid == actor_id and old_p == "admin" and perf != "admin":
            return False
        if old_p == "admin" and perf != "admin" and _contar_admins_ativos(cur) <= 1:
            return False

        cur.execute(
            "UPDATE usuarios SET perfil = ? WHERE id = ?",
            (perf, uid),
        )
        if cur.rowcount != 1:
            conn.rollback()
            return False
        conn.commit()
        log_audit(
            ator_email=actor,
            acao="UPDATE",
            modulo="usuarios",
            registro_id=str(uid),
            dados_antigos={"perfil": old_p},
            dados_novos={"perfil": perf},
        )
        _notify_cloud_sync()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def alternar_status_ativo(usuario_id: int, novo_status: int, logged_user_email: str) -> bool:
    """Define ``ativo`` (0=inactivo, 1=activo)."""
    if novo_status not in (0, 1):
        return False
    actor = (logged_user_email or "").strip() or "sistema"
    uid = int(usuario_id)
    actor_id = _resolver_user_id_por_email(actor)

    conn = get_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT perfil, ativo FROM usuarios WHERE id = ?", (uid,))
        row = cur.fetchone()
        if not row:
            return False
        perf = str(row[0]).strip().lower()
        old_ativo = int(row[1])
        if old_ativo == novo_status:
            return True

        # Nunca desativar a própria sessão pelo painel (evita autobloqueio).
        if actor_id is not None and uid == actor_id and novo_status == 0:
            return False

        # Último admin não pode ficar inactivo (manter sempre um portão aberto ao painel admin).
        if perf == "admin" and novo_status == 0 and _contar_admins_ativos(cur) <= 1:
            return False

        cur.execute(
            "UPDATE usuarios SET ativo = ? WHERE id = ?",
            (int(novo_status), uid),
        )
        if cur.rowcount != 1:
            conn.rollback()
            return False
        conn.commit()
        log_audit(
            ator_email=actor,
            acao="UPDATE",
            modulo="usuarios",
            registro_id=str(uid),
            dados_antigos={"ativo": old_ativo},
            dados_novos={"ativo": int(novo_status)},
        )
        _notify_cloud_sync()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()
