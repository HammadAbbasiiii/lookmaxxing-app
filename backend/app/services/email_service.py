"""Pluggable transactional email sender (currently: password reset).

``EMAIL_PROVIDER`` selects the backend:
- ``console`` (default) — logs the message. Perfect for dev/test, no credentials.
- ``smtp``            — sends via stdlib smtplib using SMTP_* settings.

Crucially, ``send_*`` NEVER raises: a misconfigured or failing email backend must
not break the anti-enumeration contract of ``POST /auth/forgot-password`` (which
always returns 200 whether or not the address exists).
"""
import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger("lookmaxx.email")


def send_password_reset_email(to_email: str, reset_url: str) -> None:
    subject = "Reset your LookMaxx password"
    text = (
        "We received a request to reset your LookMaxx password.\n\n"
        f"Reset it here (link valid for {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes):\n"
        f"{reset_url}\n\n"
        "If you didn't request this, you can safely ignore this email — your password won't change.\n"
    )
    html = (
        "<p>We received a request to reset your LookMaxx password.</p>"
        f"<p><a href=\"{reset_url}\">Reset your password</a> "
        f"(valid for {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes).</p>"
        "<p>If you didn't request this, ignore this email — your password won't change.</p>"
    )
    _send(to_email, subject, text, html)


def _send(to_email: str, subject: str, text: str, html: str) -> None:
    provider = settings.EMAIL_PROVIDER.lower()
    if provider == "smtp":
        _send_smtp(to_email, subject, text, html)
        return
    # console (default) and any unknown provider: log instead of raising.
    if provider != "console":
        logger.warning("Unknown EMAIL_PROVIDER %r — falling back to console log.", settings.EMAIL_PROVIDER)
    logger.info("[email -> %s] %s\n%s", to_email, subject, text)
    print(f"\U0001F4E7 [EMAIL -> {to_email}] {subject}\n{text}")


def _send_smtp(to_email: str, subject: str, text: str, html: str) -> None:
    if not settings.SMTP_HOST:
        logger.warning("EMAIL_PROVIDER=smtp but SMTP_HOST is empty — email not sent.")
        print(f"\u26a0\ufe0f [EMAIL] SMTP unconfigured; would send to {to_email}:\n{text}")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = to_email
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as exc:  # noqa: BLE001 — must never propagate
        logger.error("Failed to send reset email to %s: %s", to_email, exc)
