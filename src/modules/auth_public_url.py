"""URL pública da app (links em e-mails de recuperação / MFA)."""

from __future__ import annotations

import os


def public_app_base_url() -> str:
    """Base HTTPS do deploy actual (Secrets, ``BEABA_PUBLIC_APP_URL`` ou inferência por ambiente)."""
    explicit = (os.environ.get("BEABA_PUBLIC_APP_URL") or "").strip().rstrip("/")
    if explicit:
        return explicit
    try:
        from src.database.connection import get_beaba_env_type_raw

        env = get_beaba_env_type_raw()
    except Exception:
        env = (os.environ.get("ENV_TYPE") or os.environ.get("BEABA_ENV") or "").strip().lower()
    if env in ("staging", "stg"):
        return "https://testes-beabagestao.streamlit.app"
    if env in ("dev", "development", "develop", "local"):
        return "https://dev-beabagestao.streamlit.app"
    if env in ("production", "prod", "main"):
        return "https://gestaobeaba.streamlit.app"
    return ""


def password_change_entry_url() -> str:
    """Link directo para o fluxo de troca de senha (login + MFA + ecrã obrigatório)."""
    base = public_app_base_url()
    if not base:
        return ""
    return f"{base}/?bea_recuperar=1"
