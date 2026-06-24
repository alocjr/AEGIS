import logging
import smtplib
from email.message import EmailMessage
from urllib.parse import quote

from app.config import settings
from app.utils.email_templates import render_password_reset_html, render_password_reset_text

logger = logging.getLogger("aegis")


def smtp_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_user and settings.smtp_password)


def _build_reset_link(token: str) -> str:
    base = settings.app_base_url.rstrip("/")
    return f"{base}/login?reset_token={quote(token, safe='')}"


def send_password_reset_email(to_email: str, token: str) -> bool:
    """Envia email com link e token de reset. Retorna True se enviado."""
    if not smtp_configured():
        logger.warning("SMTP não configurado; email de reset não enviado para %s", to_email)
        return False

    reset_link = _build_reset_link(token)
    expire = settings.password_reset_expire_minutes
    subject = "Recuperação de senha — Valorian 4 Future"
    body_text = render_password_reset_text(reset_link, token, expire)
    body_html = render_password_reset_html(reset_link, token, expire)

    from_addr = settings.smtp_from or settings.smtp_user
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.set_content(body_text)
    msg.add_alternative(body_html, subtype="html")

    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30) as server:
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
    except Exception:
        logger.exception("Falha ao enviar email de reset para %s", to_email)
        return False

    logger.info("Email de reset de senha enviado para %s", to_email)
    return True
