"""Envio de e-mail via SMTP (MFA e integrações futuras).

Gmail: use **palavra-passe de aplicação** (16 caracteres) em ``SMTP_PASSWORD`` ou ``EMAIL_PASSWORD`` —
nunca a senha normal da conta. Ative 2FA na conta Google e crie a palavra-passe em
https://myaccount.google.com/apppasswords

O MFA envia apenas e-mail de saída (SMTP); não há leitura de caixa de entrada na app.
"""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage


def _truthy(raw: str | None) -> bool:
    return (raw or "").strip().lower() in ("1", "true", "yes", "on")


def _is_gmail_address(addr: str) -> bool:
    a = (addr or "").strip().lower()
    return a.endswith("@gmail.com") or a.endswith("@googlemail.com")


def resolve_smtp_settings() -> tuple[str, int, str, str, str]:
    """Lê configuração SMTP com suporte a Gmail (predefinições) e aliases ``EMAIL_*``.

    Ordem: ``SMTP_*`` explícitos; depois ``EMAIL_USERNAME`` / ``EMAIL_PASSWORD`` / ``EMAIL_FROM``
    (mesmos nomes que os secrets no GitHub Actions).

    Gmail: se ``BEABA_SMTP_GMAIL=1`` ou o utilizador for ``@gmail.com``/``@googlemail.com``,
    usa ``smtp.gmail.com`` e porta ``465`` quando servidor/porta não estão definidos.

    Returns:
        Tupla (server, port, user, password, from_addr).

    Raises:
        ValueError: configuração incompleta, com mensagem orientada a Gmail quando aplicável.
    """
    server = (os.environ.get("SMTP_SERVER") or "").strip()
    port_raw = (os.environ.get("SMTP_PORT") or "").strip()
    user = (os.environ.get("SMTP_USER") or os.environ.get("EMAIL_USERNAME") or "").strip()
    password = (os.environ.get("SMTP_PASSWORD") or os.environ.get("EMAIL_PASSWORD") or "").strip()
    from_addr = (os.environ.get("SMTP_FROM") or os.environ.get("EMAIL_FROM") or user or "").strip()

    gmail_mode = _truthy(os.environ.get("BEABA_SMTP_GMAIL")) or _truthy(os.environ.get("SMTP_GMAIL"))
    if not gmail_mode and user and _is_gmail_address(user):
        gmail_mode = True

    if gmail_mode:
        if not server:
            server = "smtp.gmail.com"
        if not port_raw:
            port_raw = "465"

    missing = []
    if not server:
        missing.append("SMTP_SERVER (ou Gmail: defina SMTP_USER com @gmail.com ou BEABA_SMTP_GMAIL=1)")
    if not port_raw:
        missing.append("SMTP_PORT")
    if not user:
        missing.append("SMTP_USER ou EMAIL_USERNAME")
    if not password:
        missing.append("SMTP_PASSWORD ou EMAIL_PASSWORD (Gmail: palavra-passe de *aplicação*, 16 caracteres)")
    if missing:
        hint = ""
        if gmail_mode or any("gmail" in m.lower() for m in missing):
            hint = (
                " Para Gmail: crie uma palavra-passe de aplicação em "
                "https://myaccount.google.com/apppasswords e coloque-a em SMTP_PASSWORD ou EMAIL_PASSWORD."
            )
        raise ValueError(
            "SMTP não configurado: defina no `.env` ou no ambiente: "
            + ", ".join(missing)
            + "."
            + hint
        )

    port = int(port_raw)
    if not from_addr:
        raise ValueError("Defina SMTP_FROM ou EMAIL_FROM (ou SMTP_USER / EMAIL_USERNAME) para o remetente.")

    return server, port, user, password, from_addr


def send_mfa_email(destinatario: str, codigo: str) -> None:
    """Envia o código MFA de 6 dígitos usando ``smtplib`` com TLS/SSL conforme a porta.

    Raises:
        ValueError: configuração incompleta.
        OSError / smtplib.SMTPException: falha de rede ou servidor SMTP.

    Args:
        destinatario: e-mail destino (normalmente o do utilizador autenticado).
        codigo: código MFA (texto curto).

    """
    server, port, user, password, from_addr = resolve_smtp_settings()

    body = (
        "BeaBa Gestão — verificação em duas etapas\n\n"
        f"O seu código de acesso é: {codigo}\n\n"
        "Este código expira em poucos minutos. Se não pediu este e-mail, ignore esta mensagem."
    )
    msg = EmailMessage()
    msg["Subject"] = "BeaBa Gestão — código de verificação"
    msg["From"] = from_addr
    msg["To"] = destinatario.strip()
    msg.set_content(body)

    ssl_ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(server, port, context=ssl_ctx, timeout=30) as smtp:
            smtp.login(user, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(server, port, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ssl_ctx)
            smtp.ehlo()
            smtp.login(user, password)
            smtp.send_message(msg)
