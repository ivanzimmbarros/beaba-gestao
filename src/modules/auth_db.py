"""Operações SQLite para credenciais e tokens MFA."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from src.database.connection import get_connection
from src.modules.auth_utils import verify_password

_MFA_TTL_MIN = 10


def get_usuario_por_id(user_id: int) -> dict[str, Any] | None:
    """Snapshot de utilizador activo por ``id`` (pós‑MFA)."""
    conn = get_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, nome, email, perfil, ativo
            FROM usuarios
            WHERE id = ?
            """,
            (int(user_id),),
        )
        row = cursor.fetchone()
        if not row:
            return None
        uid, nome, mail, perfil, ativo = row
        if not int(ativo):
            return None
        return {
            "id": int(uid),
            "nome": str(nome),
            "email": str(mail),
            "perfil": str(perfil),
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
