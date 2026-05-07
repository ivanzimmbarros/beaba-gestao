"""Utilitários de autenticação (hash de senha, MFA) — sem UI de login."""

from __future__ import annotations

import secrets

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Gera hash bcrypt da senha em texto plano."""
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica se a senha confere com o hash armazenado."""
    return _pwd_context.verify(password, password_hash)


def generate_mfa_code() -> str:
    """Gera um código MFA numérico de 6 dígitos (com zeros à esquerda se necessário)."""
    return f"{secrets.randbelow(1_000_000):06d}"
