from utils.encryption import encrypt_value, decrypt_value, validate_key


def test_round_trip():
    plaintext = "super-secret-value"
    assert decrypt_value(encrypt_value(plaintext)) == plaintext


def test_empty_passthrough():
    assert encrypt_value("") == ""
    assert decrypt_value("") == ""


def test_validate_key_passes(monkeypatch):
    from cryptography.fernet import Fernet
    monkeypatch.setenv("MASTER_ENCRYPTION_KEY", Fernet.generate_key().decode())
    validate_key()  # must not raise


def test_validate_key_missing_raises(monkeypatch):
    import pytest
    monkeypatch.setenv("MASTER_ENCRYPTION_KEY", "")
    with pytest.raises(ValueError, match="not set"):
        validate_key()
