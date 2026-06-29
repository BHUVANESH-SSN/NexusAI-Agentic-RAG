import pytest
from cryptography.fernet import Fernet


@pytest.fixture(autouse=True)
def set_test_env(monkeypatch):
    monkeypatch.setenv("MASTER_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("API_KEY", "test-user-key")
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-tests")
    monkeypatch.setenv("LANGSMITH_API_KEY", "")
    from llm.factory import get_settings, get_embeddings, get_reranker
    get_settings.cache_clear()
