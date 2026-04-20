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
def send_email(recipient: str, subject: str, message: str) -> str:
    """Send an email to a specific recipient.
    
    Args:
        recipient: The email address of the person receiving the email.
        subject: The subject line of the email.
        message: The actual body/content of the email.
    """
    LOGGER.info("Attempting to send email to %s | Subject: %s", recipient, subject)
    
    smtp_server = _get_setting("email_smtp")
    smtp_user = _get_setting("email_user")
    smtp_pass = _get_setting("email_password")
    
    if not (smtp_server and smtp_user and smtp_pass):
        LOGGER.warning("Email settings not configured. Falling back to mock email.")
        print(f"\n--- MOCK EMAIL SENT ---")
        print(f"To: {recipient}\nSubject: {subject}\nMessage: {message}")
        print(f"-----------------------\n")
        return f"Warning: Email credentials not configured in Settings. Mock email sent to {recipient}."

    try:
        msg = EmailMessage()
        msg.set_content(message)
        msg['Subject'] = subject
        msg['From'] = smtp_user
        msg['To'] = recipient

        # Standard TLS connection port, commonly 587
        parts = smtp_server.split(":")
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 587

        server = smtplib.SMTP(host, port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        
        return f"Successfully sent email to {recipient} with subject '{subject}'."
    except Exception as e:
        LOGGER.exception("SMTP email sending failed.")
        return f"Failed to send email to {recipient}: {str(e)}"
