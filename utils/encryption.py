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
