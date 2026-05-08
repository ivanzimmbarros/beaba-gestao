"""SMTP config resolution — Gmail presets and EMAIL_* aliases."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.modules import email_utils


def test_resolve_explicit_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EMAIL_USERNAME", raising=False)
    monkeypatch.delenv("EMAIL_PASSWORD", raising=False)
    monkeypatch.delenv("EMAIL_FROM", raising=False)
    monkeypatch.delenv("BEABA_SMTP_GMAIL", raising=False)
    monkeypatch.setenv("SMTP_SERVER", "smtp.example.test")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "u@example.test")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("SMTP_FROM", "from@example.test")
    assert email_utils.resolve_smtp_settings() == (
        "smtp.example.test",
        587,
        "u@example.test",
        "secret",
        "from@example.test",
    )


def test_resolve_gmail_user_defaults_server_port(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in (
        "SMTP_SERVER",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "SMTP_FROM",
        "EMAIL_USERNAME",
        "EMAIL_PASSWORD",
        "EMAIL_FROM",
        "BEABA_SMTP_GMAIL",
        "SMTP_GMAIL",
    ):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("SMTP_USER", "someone@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "app_pw_xxxxxxxxxxxxxx")
    s, p, u, pwd, f = email_utils.resolve_smtp_settings()
    assert s == "smtp.gmail.com"
    assert p == 465
    assert u == "someone@gmail.com"
    assert pwd == "app_pw_xxxxxxxxxxxxxx"
    assert f == "someone@gmail.com"


def test_resolve_email_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in (
        "SMTP_SERVER",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "SMTP_FROM",
        "BEABA_SMTP_GMAIL",
        "SMTP_GMAIL",
    ):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("EMAIL_USERNAME", "ops@gmail.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "pw")
    monkeypatch.setenv("EMAIL_FROM", "noreply@gmail.com")
    s, port, *_ = email_utils.resolve_smtp_settings()
    assert s == "smtp.gmail.com"
    assert port == 465


def test_missing_password_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EMAIL_PASSWORD", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    monkeypatch.delenv("BEABA_SMTP_GMAIL", raising=False)
    monkeypatch.setenv("SMTP_SERVER", "smtp.example.test")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "u@test.com")
    monkeypatch.setenv("SMTP_FROM", "u@test.com")
    with pytest.raises(ValueError) as ei:
        email_utils.resolve_smtp_settings()
    assert "SMTP_PASSWORD" in str(ei.value) or "EMAIL_PASSWORD" in str(ei.value)


def test_send_mfa_email_port_465_uses_ssl_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """Envio MFA na porta 465 usa SMTP_SSL + login + send_message (sem rede)."""
    for k in (
        "SMTP_SERVER",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "SMTP_FROM",
        "EMAIL_USERNAME",
        "EMAIL_PASSWORD",
        "EMAIL_FROM",
        "BEABA_SMTP_GMAIL",
        "SMTP_GMAIL",
    ):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("SMTP_USER", "sender@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "abcdabcdabcdabcd")
    mock_smtp = MagicMock()
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_smtp
    mock_cm.__exit__.return_value = False
    with patch("src.modules.email_utils.smtplib.SMTP_SSL", return_value=mock_cm) as p_ssl:
        email_utils.send_mfa_email("dest@example.org", "123456")
    p_ssl.assert_called_once()
    assert p_ssl.call_args[0][0] == "smtp.gmail.com"
    assert p_ssl.call_args[0][1] == 465
    mock_smtp.login.assert_called_once_with("sender@gmail.com", "abcdabcdabcdabcd")
    mock_smtp.send_message.assert_called_once()
    msg = mock_smtp.send_message.call_args[0][0]
    assert msg["To"] == "dest@example.org"
    assert "123456" in msg.get_content()


def test_send_mfa_email_port_587_starttls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMTP_SERVER", "smtp.office365.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "u@corp.test")
    monkeypatch.setenv("SMTP_PASSWORD", "pw")
    monkeypatch.setenv("SMTP_FROM", "u@corp.test")
    mock_smtp = MagicMock()
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_smtp
    mock_cm.__exit__.return_value = False
    with patch("src.modules.email_utils.smtplib.SMTP", return_value=mock_cm):
        email_utils.send_mfa_email("x@y.test", "999999")
    mock_smtp.starttls.assert_called_once()
    mock_smtp.login.assert_called_once()
    mock_smtp.send_message.assert_called_once()
