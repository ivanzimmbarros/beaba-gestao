"""Operações SQLite para credenciais e tokens MFA."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from src.database.connection import get_connection
from src.modules.auth_utils import hash_password, verify_password

_MFA_TTL_MIN = 10


def get_usuario_por_id(user_id: int) -> dict[str, Any] | None:
    """Snapshot de utilizador activo por ``id`` (pós‑MFA)."""
    conn = get_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cols = {r[1] for r in cursor.execute("PRAGMA table_info(usuarios)").fetchall()}
        has_mcp = "must_change_password" in cols
        sel = (
            "SELECT id, nome, email, perfil, ativo, must_change_password FROM usuarios WHERE id = ?"
            if has_mcp
            else "SELECT id, nome, email, perfil, ativo FROM usuarios WHERE id = ?"
        )
        cursor.execute(sel, (int(user_id),))
        row = cursor.fetchone()
        if not row:
            return None
        if has_mcp:
            uid, nome, mail, perfil, ativo, mcp = row
            must_ch = int(mcp)
        else:
            uid, nome, mail, perfil, ativo = row
            must_ch = 0
        if not int(ativo):
            return None
        return {
            "id": int(uid),
            "nome": str(nome),
            "email": str(mail),
            "perfil": str(perfil),
            "must_change_password": bool(must_ch),
        }
    finally:
        conn.close()


def try_login_credentials(
    email: str,
    password: str,
) -> tuple[dict[str, Any] | None, str | None]:
    """Valida utilizador por e-mail/senha. Retorna dados do utilizador ou ``(None, mensagem erro)``.

    Mensagens são genéricas para não revelar se o e-mail existe.
    """
    conn = get_connection()
    if not conn:
        return None, "Não foi possível ligar à base de dados. Tente novamente."

    conn.row_factory = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, nome, email, senha_hash, perfil, ativo
            FROM usuarios
            WHERE LOWER(TRIM(email)) = LOWER(TRIM(?))
            """,
            (email.strip(),),
        )
        row = cursor.fetchone()
        if not row:
            return None, "E-mail ou senha incorretos."
        uid, nome, mail, pwd_hash, perfil, ativo = row
        if not int(ativo):
            return None, "Este utilizador está inactivo."
        if not verify_password(password, pwd_hash):
            return None, "E-mail ou senha incorretos."
        data: dict[str, Any] = {
            "id": int(uid),
            "nome": str(nome),
            "email": str(mail),
            "perfil": str(perfil),
        }
        return data, None
    finally:
        conn.close()


def update_password_clear_must_change(
    user_id: int,
    new_password: str,
    *,
    current_password: str | None = None,
) -> str | None:
    """Define nova senha e ``must_change_password=0``. ``current_password`` obrigatório se ainda há troca pendente.

    Devolve mensagem de erro ou ``None`` se OK.
    """
    pwd = new_password.strip()
    if len(pwd) < 8:
        return "A nova senha deve ter pelo menos 8 caracteres."
    conn = get_connection()
    if not conn:
        return "Não foi possível ligar à base de dados."
    try:
        cursor = conn.cursor()
        cols = {r[1] for r in cursor.execute("PRAGMA table_info(usuarios)").fetchall()}
        if "must_change_password" in cols:
            cursor.execute(
                "SELECT senha_hash, must_change_password FROM usuarios WHERE id = ? AND ativo = 1",
                (int(user_id),),
            )
        else:
            cursor.execute(
                "SELECT senha_hash FROM usuarios WHERE id = ? AND ativo = 1",
                (int(user_id),),
            )
        row = cursor.fetchone()
        if not row:
            return "Utilizador não encontrado."
        pwd_hash = row[0]
        mcp = int(row[1]) if len(row) > 1 and row[1] is not None else 0
        if int(mcp) == 1:
            if current_password is None or not str(current_password).strip():
                return "Indique a senha actual para confirmar a troca."
            if not verify_password(str(current_password).strip(), str(pwd_hash)):
                return "Senha actual incorrecta."
        if verify_password(pwd, str(pwd_hash)):
            return "A nova senha deve ser diferente da senha actual."
        new_h = hash_password(pwd)
        cursor.execute(
            """
            UPDATE usuarios
            SET senha_hash = ?, must_change_password = 0
            WHERE id = ?
            """,
            (new_h, int(user_id)),
        )
        conn.commit()
        return None
    except Exception:
        conn.rollback()
        return "Não foi possível actualizar a senha. Tente novamente."
    finally:
        conn.close()


def create_usuario(
    nome: str,
    email: str,
    password_plain: str,
    perfil: str,
) -> str | None:
    """Cria utilizador; no primeiro login será obrigatório alterar a senha (``must_change_password=1``).

    ``perfil``: ``admin`` ou ``colaborador``. Devolve mensagem de erro ou ``None`` se OK.
    """
    perfil_n = (perfil or "").strip().lower()
    if perfil_n not in ("admin", "colaborador"):
        return "Perfil inválido."
    mail = (email or "").strip()
    nome_n = (nome or "").strip()
    if not mail or not nome_n:
        return "Nome e e-mail são obrigatórios."
    pwd = (password_plain or "").strip()
    if len(pwd) < 1:
        return "Senha inicial em falta."
    conn = get_connection()
    if not conn:
        return "Não foi possível ligar à base de dados."
    try:
        cursor = conn.cursor()
        cols = {r[1] for r in cursor.execute("PRAGMA table_info(usuarios)").fetchall()}
        if "must_change_password" not in cols:
            return "Esquema de utilizadores desactualizado (must_change_password em falta)."
        cursor.execute(
            """
            INSERT INTO usuarios (nome, email, senha_hash, perfil, ativo, must_change_password, data_cadastro)
            VALUES (?, ?, ?, ?, 1, 1, datetime('now'))
            """,
            (nome_n, mail.lower(), hash_password(pwd), perfil_n),
        )
        conn.commit()
        return None
    except Exception:
        conn.rollback()
        return "Não foi possível criar o utilizador (e-mail duplicado?)."
    finally:
        conn.close()


def _invalidate_unused_mfa(cursor, user_id: int) -> None:
    cursor.execute(
        "UPDATE mfa_tokens SET usado = 1 WHERE user_id = ? AND usado = 0",
        (user_id,),
    )


def discard_pending_mfa_tokens(user_id: int) -> None:
    """Marca como usados todos os MFA pendentes do utilizador (ex.: SMTP falhou após gravar código)."""
    conn = get_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        _invalidate_unused_mfa(cursor, user_id)
        conn.commit()
    finally:
        conn.close()


def issue_mfa_token(user_id: int, code_plain: str) -> str | None:
    """Grava novo token MFA; invalida pendências antigas para o mesmo ``user_id``.

    Devolve mensagem de erro humana ou ``None`` se OK.
    """
    conn = get_connection()
    if not conn:
        return "Não foi possível ligar à base de dados."

    exp = datetime.now(timezone.utc) + timedelta(minutes=_MFA_TTL_MIN)
    expires_sql = exp.strftime("%Y-%m-%d %H:%M:%S")
    try:
        cursor = conn.cursor()
        _invalidate_unused_mfa(cursor, user_id)
        cursor.execute(
            """
            INSERT INTO mfa_tokens (user_id, token, expira_em, usado)
            VALUES (?, ?, ?, 0)
            """,
            (user_id, code_plain.strip(), expires_sql),
        )
        conn.commit()
        return None
    except Exception:
        conn.rollback()
        return "Falha ao registar código de verificação. Tente novamente."
    finally:
        conn.close()


def _parse_expires_utc(raw_exp: str) -> datetime | None:
    raw = (raw_exp or "").strip()
    if not raw:
        return None
    try:
        if "T" in raw:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return datetime.strptime(raw[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def consume_mfa_token(user_id: int, code_plain: str) -> bool:
    """Se o código for válido, não expirado e não usado, marca ``usado=1`` e devolve ``True``."""
    code = code_plain.strip()
    conn = get_connection()
    if not conn:
        return False

    now = datetime.now(timezone.utc)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, expira_em
            FROM mfa_tokens
            WHERE user_id = ? AND token = ? AND usado = 0
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id, code),
        )
        row = cursor.fetchone()
        if not row:
            return False
        row_id = int(row[0])
        raw_exp = str(row[1])
        expires = _parse_expires_utc(raw_exp)
        if expires is None:
            return False
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if now > expires:
            return False

        cursor.execute("UPDATE mfa_tokens SET usado = 1 WHERE id = ?", (row_id,))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()
