"""Envio de e-mail via SMTP (MFA e integrações futuras)."""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage


def _smtp_from_address() -> str:
    raw = (os.environ.get("SMTP_FROM") or os.environ.get("SMTP_USER") or "").strip()
    return raw


def send_mfa_email(destinatario: str, codigo: str) -> None:
    """Envia o código MFA de 6 dígitos usando ``smtplib`` com TLS/SSL conforme a porta.

    Variáveis de ambiente obrigatórias: ``SMTP_SERVER``, ``SMTP_PORT``, ``SMTP_USER``, ``SMTP_PASSWORD``.
    Opcional: ``SMTP_FROM`` (remetente; por omissão ``SMTP_USER``).

    Raises:
        ValueError: configuração incompleta.
        OSError / smtplib.SMTPException: falha de rede ou servidor SMTP.

    Args:
        destinatario: e-mail destino (normalmente o do utilizador autenticado).
        codigo: código MFA (texto curto).

    """
    server = (os.environ.get("SMTP_SERVER") or "").strip()
    port_raw = (os.environ.get("SMTP_PORT") or "").strip()
    user = (os.environ.get("SMTP_USER") or "").strip()
    password = (os.environ.get("SMTP_PASSWORD") or "").strip()

    missing = []
    if not server:
        missing.append("SMTP_SERVER")
    if not port_raw:
        missing.append("SMTP_PORT")
    if not user:
        missing.append("SMTP_USER")
    if not password:
        missing.append("SMTP_PASSWORD")
    if missing:
        raise ValueError(f"SMTP não configurado: defina {' e '.join(missing)} no ambiente.")

    port = int(port_raw)
    from_addr = _smtp_from_address()
    if not from_addr:
        raise ValueError("Defina SMTP_FROM ou SMTP_USER para o remetente.")

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
