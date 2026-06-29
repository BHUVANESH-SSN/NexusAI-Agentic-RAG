import collections
import logging
import smtplib
import sqlite3
import time
from email.message import EmailMessage

from langchain_core.tools import tool

from llm.factory import get_settings
from utils.encryption import decrypt_value

LOGGER = logging.getLogger(__name__)

_SEND_LOG: collections.deque = collections.deque()


def _get_db_path() -> str:
    return str(get_settings().db_path)


def _get_setting(key: str) -> str:
    db_path = _get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM user_settings WHERE key=?", (key,))
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            return decrypt_value(row[0])
    except Exception as e:
        LOGGER.error("Error fetching %s from settings: %s", key, e)
    return ""


def _recipient_allowed(recipient: str) -> bool:
    settings = get_settings()
    smtp_configured = bool(_get_setting("email_smtp"))
    if not smtp_configured:
        return True  # mock mode — no restriction needed
    if not settings.allowed_email_domains:
        return True  # allow-list not configured — permit all
    domain = recipient.split("@")[-1].lower() if "@" in recipient else ""
    return domain in settings.allowed_email_domains


def _within_send_cap() -> bool:
    settings = get_settings()
    cap = settings.email_send_cap_per_hour
    now = time.time()
    cutoff = now - 3600
    while _SEND_LOG and _SEND_LOG[0] < cutoff:
        _SEND_LOG.popleft()
    return len(_SEND_LOG) < cap


def _record_send() -> None:
    _SEND_LOG.append(time.time())
    LOGGER.info("Email send recorded. Sends in last hour: %d", len(_SEND_LOG))


@tool
def prepare_email_draft(recipient: str, subject: str, message: str) -> str:
    """Prepare a draft of an email. Use this FIRST before actually sending.

    Args:
        recipient: The email address of the person receiving the email.
        subject: The subject line of the email.
        message: The actual body/content of the email.
    """
    LOGGER.info("Drafting email to %s", recipient)
    return (
        f"DRAFT_PREPARED: I have drafted a mail to {recipient} with subject '{subject}'. "
        f'The message is: "{message}"\n\nShall I proceed and send this email?'
    )


@tool
def execute_send_email(recipient: str, subject: str, message: str) -> str:
    """Send an email to a specific recipient. ONLY use this if the user has already confirmed the draft.

    Args:
        recipient: The email address of the person receiving the email.
        subject: The subject line of the email.
        message: The actual body/content of the email.
    """
    LOGGER.info("Executing actual email send to %s", recipient)

    if not _recipient_allowed(recipient):
        LOGGER.warning("Email to %s blocked — domain not in allow-list.", recipient)
        return f"BLOCKED: Sending to {recipient} is not permitted by policy."

    if not _within_send_cap():
        LOGGER.warning("Email send cap reached for this hour.")
        return "BLOCKED: Hourly email send limit reached. Try again later."

    smtp_server = _get_setting("email_smtp")
    smtp_user = _get_setting("email_user")
    smtp_pass = _get_setting("email_password")

    if not (smtp_server and smtp_user and smtp_pass):
        LOGGER.warning("Email credentials not configured. Using mock fallback.")
        LOGGER.info("MOCK EMAIL — To: %s | Subject: %s | Body: %s", recipient, subject, message)
        _record_send()
        return f"SUCCESS: Email credentials not configured. Mock email sent to {recipient}."

    try:
        msg = EmailMessage()
        msg.set_content(message)
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = recipient

        host = smtp_server.split(":")[0]
        port = int(smtp_server.split(":")[1]) if ":" in smtp_server else 587

        server = smtplib.SMTP(host, port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()

        _record_send()
        return f"SUCCESS: Successfully sent email to {recipient}."
    except Exception:
        LOGGER.exception("SMTP email sending failed.")
        return f"ERROR: Failed to send email to {recipient}. Check SMTP configuration."
