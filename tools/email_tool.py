import logging
import sqlite3
import os
import smtplib
from email.message import EmailMessage
from langchain_core.tools import tool
from utils.encryption import decrypt_value

LOGGER = logging.getLogger(__name__)

def _get_setting(key: str) -> str:
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db", "company.db")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM user_settings WHERE key=?", (key,))
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            return decrypt_value(row[0])
    except Exception as e:
        LOGGER.error(f"Error fetching {key} from settings: {e}")
    return ""

@tool
def prepare_email_draft(recipient: str, subject: str, message: str) -> str:
    """Prepare a draft of an email. Use this FIRST before actually sending.
    
    Args:
        recipient: The email address of the person receiving the email.
        subject: The subject line of the email.
        message: The actual body/content of the email.
    """
    LOGGER.info("Drafting email to %s", recipient)
    return f"DRAFT_PREPARED: I have drafted a mail to {recipient} with subject '{subject}'. The message is: \"{message}\"\n\nShall I proceed and send this email?"

@tool
def execute_send_email(recipient: str, subject: str, message: str) -> str:
    """Send an email to a specific recipient. ONLY use this if the user has already confirmed the draft.
    
    Args:
        recipient: The email address of the person receiving the email.
        subject: The subject line of the email.
        message: The actual body/content of the email.
    """
    LOGGER.info("Executing actual email send to %s", recipient)
    
    smtp_server = _get_setting("email_smtp")
    smtp_user = _get_setting("email_user")
    smtp_pass = _get_setting("email_password")
    
    if not (smtp_server and smtp_user and smtp_pass):
        LOGGER.warning("Email credentials not configured. Using Mock fallback.")
        LOGGER.info("\n--- MOCK EMAIL SENT ---")
        LOGGER.info(f"To: {recipient}\nSubject: {subject}\nMessage: {message}")
        LOGGER.info("-----------------------\n")
        return f"SUCCESS: Email credentials not configured. Mock email sent to {recipient}."

    try:
        msg = EmailMessage()
        msg.set_content(message)
        msg['Subject'] = subject
        msg['From'] = smtp_user
        msg['To'] = recipient

        host = smtp_server.split(":")[0]
        port = int(smtp_server.split(":")[1]) if ":" in smtp_server else 587

        server = smtplib.SMTP(host, port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        
        return f"SUCCESS: Successfully sent email to {recipient}."
    except Exception as e:
        LOGGER.exception("SMTP email sending failed.")
        return f"ERROR: Failed to send email to {recipient}: {str(e)}"
