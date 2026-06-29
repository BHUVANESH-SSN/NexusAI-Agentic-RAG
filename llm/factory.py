import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Any, Optional

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"

@dataclass(frozen=True)
class Settings:
    llm_provider: str
    groq_model: str
    openai_model: str
    llm_temperature: float
    embedding_model: str
    docs_path: Path
    vector_store_path: Path
    chunk_size: int
    chunk_overlap: int
    retriever_top_k: int
    rerank_model: str
    anthropic_model: str
    bedrock_model_id: str
    failover_providers: List[str]
    redis_url: str
    log_level: str
    # --- Security fields ---
    api_key: str
    admin_api_key: str
    cors_allowed_origins: List[str]
    allowed_upload_extensions: List[str]
    max_upload_bytes: int
    allowed_email_domains: List[str]
    email_send_cap_per_hour: int
    db_path: Path
    langsmith_api_key: str
    langchain_project: str
    db_readonly_uri: str
    rate_limit_per_minute: int


def _resolve_path(value: Optional[str], default: Path) -> Path:
    if not value:
        return default.resolve()

    path = Path(value)
    if path.is_absolute():
        return path

    return (BASE_DIR / path).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Ensure .env is loaded
    load_dotenv(ENV_PATH)
    
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "groq").strip().lower(),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip(),
        llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
        embedding_model=os.getenv(
            "EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        ).strip(),
        docs_path=_resolve_path(
            os.getenv("COMPANY_DOCS_PATH"),
            BASE_DIR / "data" / "company_docs",
        ),
        vector_store_path=_resolve_path(
            os.getenv("VECTOR_STORE_PATH"),
            BASE_DIR / "data" / "faiss_index",
        ),
        chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
        retriever_top_k=int(os.getenv("RETRIEVER_TOP_K", "3")),
        rerank_model=os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2").strip(),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620").strip(),
        bedrock_model_id=os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0").strip(),
        failover_providers=os.getenv("FAILOVER_PROVIDERS", "groq,openai").lower().split(","),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379").strip(),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        # --- Security ---
        api_key=os.getenv("API_KEY", "").strip(),
        admin_api_key=os.getenv("ADMIN_API_KEY", "").strip(),
        cors_allowed_origins=[
            o.strip()
            for o in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
            if o.strip()
        ],
        allowed_upload_extensions=[
            e.strip().lower()
            for e in os.getenv("ALLOWED_UPLOAD_EXTENSIONS", ".pdf,.md,.docx,.csv").split(",")
            if e.strip()
        ],
        max_upload_bytes=int(os.getenv("MAX_UPLOAD_BYTES", str(20 * 1024 * 1024))),
        allowed_email_domains=[
            d.strip().lower()
            for d in os.getenv("ALLOWED_EMAIL_DOMAINS", "").split(",")
            if d.strip()
        ],
        email_send_cap_per_hour=int(os.getenv("EMAIL_SEND_CAP_PER_HOUR", "10")),
        db_path=_resolve_path(
            os.getenv("DB_PATH"),
            BASE_DIR / "db" / "company.db",
        ),
        langsmith_api_key=os.getenv("LANGSMITH_API_KEY", "").strip(),
        langchain_project=os.getenv("LANGCHAIN_PROJECT", "nexusai").strip(),
        db_readonly_uri=os.getenv("DB_READONLY_URI", "").strip(),
        rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "10")),
    )


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def get_chat_model(provider: Optional[str] = None):
    """Return a LangChain-compatible chat model via LiteLLM's unified interface."""
    from langchain_community.chat_models import ChatLiteLLM
    settings = get_settings()
    provider = (provider or settings.llm_provider).strip().lower()

    model_map = {
        "groq":      f"groq/{settings.groq_model}",
        "openai":    f"openai/{settings.openai_model}",
        "anthropic": f"anthropic/{settings.anthropic_model}",
        "bedrock":   f"bedrock/{settings.bedrock_model_id}",
    }
    model_name = model_map.get(provider)
    if not model_name:
        raise ValueError(
            f"Unsupported LLM provider: {provider!r}. Choose from: {list(model_map)}"
        )
    return ChatLiteLLM(model=model_name, temperature=settings.llm_temperature)


try:
    from langchain_core.runnables import Runnable as _LCRunnable
    _RUNNABLE_BASE = _LCRunnable
except ImportError:
    _RUNNABLE_BASE = object  # type: ignore[assignment,misc]


class _FailoverChatModel(_RUNNABLE_BASE):
    """LangChain-compatible chat model that retries across providers at every invoke call.

    Inherits from langchain_core.runnables.Runnable so it participates in LCEL
    chains (prompt | model | parser) via the standard __or__ / pipe interface.
    """

    def __init__(self, providers: List[str]) -> None:
        self._providers = providers

    def _invoke_with_failover(self, method: str, *args, **kwargs) -> Any:
        last_exc: Exception = RuntimeError("No LLM providers configured.")
        for provider in self._providers:
            try:
                return getattr(get_chat_model(provider), method)(*args, **kwargs)
            except Exception as exc:
                logging.getLogger(__name__).warning(
                    "LLM provider '%s' failed at %s: %s. Trying next.", provider, method, exc
                )
                last_exc = exc
        raise RuntimeError(f"All LLM providers failed. Last: {last_exc}") from last_exc

    def invoke(self, *args, **kwargs) -> Any:
        return self._invoke_with_failover("invoke", *args, **kwargs)

    def stream(self, *args, **kwargs) -> Any:
        return self._invoke_with_failover("stream", *args, **kwargs)

    def bind(self, **kwargs) -> "_FailoverChatModel":
        clone = _FailoverChatModel(self._providers)
        clone._bind_kwargs = {**getattr(self, "_bind_kwargs", {}), **kwargs}
        return clone


def get_llm_with_failover() -> _FailoverChatModel:
    """Return a chat model that retries across providers at every invoke call."""
    settings = get_settings()
    providers = [settings.llm_provider] + [
        p for p in settings.failover_providers if p != settings.llm_provider
    ]
    logging.getLogger(__name__).info("LLM failover chain: %s", providers)
    return _FailoverChatModel(providers)


@lru_cache(maxsize=1)
def get_embeddings():
    settings = get_settings()
    from langchain_huggingface import HuggingFaceEmbeddings

    logging.getLogger(__name__).info(
        "Loading embedding model: %s", settings.embedding_model
    )
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


@lru_cache(maxsize=1)
def get_reranker():
    settings = get_settings()
    from sentence_transformers import CrossEncoder

    logging.getLogger(__name__).info(
        "Loading rerank model: %s", settings.rerank_model
    )
    return CrossEncoder(settings.rerank_model, device="cpu")
