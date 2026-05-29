"""Optional SMTP delivery using stdlib only (no paid vendor SDK).

Set SMTP_HOST (and typically SMTP_USER, SMTP_PASSWORD, SMTP_FROM) to send
scheduled-report notifications. If SMTP_HOST is unset, callers should keep
placeholder logging behavior.
"""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def smtp_configured() -> bool:
    return bool(os.getenv("SMTP_HOST", "").strip())


def send_smtp_text_email(*, to_addr: str, subject: str, body: str) -> None:
    host = os.getenv("SMTP_HOST", "").strip()
    if not host:
        raise RuntimeError("SMTP_HOST is not set")

    port = _env_int("SMTP_PORT", 587)
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    mail_from = os.getenv("SMTP_FROM", user or "noreply@localhost").strip()
    use_tls = os.getenv("SMTP_USE_TLS", "1").lower() not in ("0", "false", "no")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = to_addr
    msg.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=_env_int("SMTP_TIMEOUT_SECONDS", 20)) as smtp:
        if use_tls:
            smtp.starttls(context=context)
        if user:
            smtp.login(user, password)
        smtp.send_message(msg)

    logger.info("SMTP notification sent to %s subject=%s", to_addr, subject)
