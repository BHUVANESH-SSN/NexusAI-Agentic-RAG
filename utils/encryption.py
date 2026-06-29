import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

def get_cipher() -> Fernet:
    key = os.getenv("MASTER_ENCRYPTION_KEY")
    if not key:
        raise ValueError("MASTER_ENCRYPTION_KEY is missing from .env!")
    return Fernet(key.encode())

def encrypt_value(text: str) -> str:
    if not text:
        return ""
    cipher = get_cipher()
    return cipher.encrypt(text.encode('utf-8')).decode('utf-8')

def decrypt_value(token: str) -> str:
    if not token:
        return ""
    cipher = get_cipher()
    return cipher.decrypt(token.encode('utf-8')).decode('utf-8')

def validate_key() -> None:
    """Call at startup. Raises ValueError with generation hint if key is missing/invalid."""
    key = os.getenv("MASTER_ENCRYPTION_KEY", "").strip()
    if not key:
        raise ValueError(
            "MASTER_ENCRYPTION_KEY is not set. Generate one with:\n"
            "  python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
            "Then add it to your .env file."
        )
    try:
        Fernet(key.encode())
    except Exception as exc:
        raise ValueError(
            f"MASTER_ENCRYPTION_KEY is invalid (must be a Fernet key): {exc}"
        ) from exc
