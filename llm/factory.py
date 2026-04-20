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
    )


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def get_chat_model(provider: Optional[str] = None):
    settings = get_settings()
    provider = provider or settings.llm_provider

    if provider == "groq":
        from langchain_groq import ChatGroq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is missing.")
        return ChatGroq(model=settings.groq_model, temperature=settings.llm_temperature, max_retries=1)

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing.")
        return ChatOpenAI(model=settings.openai_model, temperature=settings.llm_temperature, max_retries=1)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is missing.")
        return ChatAnthropic(model=settings.anthropic_model, temperature=settings.llm_temperature)

    if provider == "bedrock":
        from langchain_aws import ChatBedrock
        return ChatBedrock(model_id=settings.bedrock_model_id, model_kwargs={"temperature": settings.llm_temperature})

    raise ValueError(f"Unsupported provider: {provider}")


def get_llm_with_failover():
    """Returns the main configured model. Pluggable for future use."""
    return get_chat_model()


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
