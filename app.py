import logging
import os
import shutil
import sqlite3
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile, File, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from redis import Redis

from agents.chatbot import EnterpriseChatbot
from llm.factory import configure_logging, get_settings
from rag.retriever import CompanyRetriever
from security import require_identity, require_admin
from utils.encryption import encrypt_value, decrypt_value

configure_logging()
LOGGER = logging.getLogger(__name__)

# --- Global State ---
INDEXING_QUEUE: set = set()

# --- Models ---

class ChatRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)

class ChatResponse(BaseModel):
    answer: str
    source: str
    confidence: str

class SettingsPayload(BaseModel):
    mysql_uri: str = ""
    email_smtp: str = ""
    email_user: str = ""
    email_password: str = ""


# --- Background Tasks ---

def build_indices_and_refresh(app):
    try:
        from rag.ingestion import build_indices
        LOGGER.info("Starting background rebuild of indices...")
        build_indices()
        INDEXING_QUEUE.clear()
        if hasattr(app.state, "chatbot"):
            app.state.chatbot.retriever_agent.retriever.clear_cache()
            LOGGER.info("Chatbot retriever cache cleared successfully.")
    except Exception as e:
        LOGGER.error("Background indexing failed: %s", e)
        INDEXING_QUEUE.clear()


# --- Rate Limiting ---

def _enforce_rate_limit(request: Request) -> None:
    settings = get_settings()
    source_ip = request.client.host if request.client else "unknown"
    # Key on identity + source IP — not client-supplied user_id — to prevent spoofing
    key = f"rate_limit:anon:{source_ip}"
    try:
        r = Redis.from_url(settings.redis_url, socket_connect_timeout=1)
        count = r.incr(key)
        if count == 1:
            r.expire(key, 60)
        if count > settings.rate_limit_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again in a minute.",
            )
    except HTTPException:
        raise
    except Exception:
        pass  # Redis down — degrade gracefully, do not block requests


# --- Lifespan ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    retriever = CompanyRetriever()
    app.state.chatbot = EnterpriseChatbot(retriever=retriever)
    LOGGER.info("Application startup complete with EnterpriseChatbot.")
    yield
    LOGGER.info("Application shutdown.")


# --- App Definition ---

def _make_app() -> FastAPI:
    settings = get_settings()
    _app = FastAPI(title="NexusAI Enterprise Chatbot", version="2.0.0", lifespan=lifespan)
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return _app

app = _make_app()


# --- Health ---

@app.get("/health")
def health_check():
    chatbot_ready = hasattr(app.state, "chatbot") and app.state.chatbot is not None
    return {"status": "ok" if chatbot_ready else "starting", "chatbot_ready": chatbot_ready}


# --- Chat ---

@app.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    _identity: str = Depends(require_identity),
):
    _enforce_rate_limit(request)

    try:
        result = request.app.state.chatbot.process_message(
            user_id=payload.user_id,
            session_id=payload.session_id,
            message=payload.message,
        )
        return ChatResponse(
            answer=result.get("answer", ""),
            source=result.get("source", "unknown"),
            confidence=result.get("confidence", "medium"),
        )
    except Exception as exc:
        LOGGER.exception("Chat request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred.",
        )


# --- Settings ---

def get_settings_db():
    db_path = os.path.join(os.path.dirname(__file__), "db", "company.db")
    return sqlite3.connect(db_path)

_SECRET_KEYS = {"mysql_uri", "email_smtp", "email_user", "email_password"}

@app.get("/settings")
def get_user_settings(_identity: str = Depends(require_admin)):
    try:
        conn = get_settings_db()
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS user_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        cursor.execute("SELECT key, value FROM user_settings")
        rows = cursor.fetchall()
        conn.close()

        result = {}
        for k, v in rows:
            result[k] = "***set***" if (v and k in _SECRET_KEYS) else ""
        return result
    except Exception as e:
        LOGGER.error("Failed to fetch settings: %s", e)
        return {}


@app.post("/settings")
def update_user_settings(
    payload: SettingsPayload,
    _identity: str = Depends(require_admin),
):
    try:
        conn = get_settings_db()
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS user_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        data = payload.model_dump()
        for k, v in data.items():
            if v:
                encrypted = encrypt_value(v)
                cursor.execute(
                    "INSERT OR REPLACE INTO user_settings (key, value) VALUES (?, ?)",
                    (k, encrypted),
                )
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        LOGGER.exception("Failed to save settings: %s", e)
        raise HTTPException(status_code=500, detail="Failed to save settings")


# --- Document Management ---

def _safe_filename(filename: str) -> str:
    return os.path.basename(filename).strip()

@app.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    _identity: str = Depends(require_admin),
):
    settings = get_settings()
    safe_name = _safe_filename(file.filename or "")
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    ext = os.path.splitext(safe_name)[1].lower()
    if ext not in settings.allowed_upload_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type {ext!r} not allowed. Allowed: {settings.allowed_upload_extensions}",
        )

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {settings.max_upload_bytes // (1024*1024)} MB).",
        )

    try:
        settings.docs_path.mkdir(parents=True, exist_ok=True)
        file_path = settings.docs_path / safe_name
        file_path.write_bytes(content)
        INDEXING_QUEUE.add(safe_name)
        background_tasks.add_task(build_indices_and_refresh, app)
        return {"status": "success", "message": f"Uploaded {safe_name} and queued for re-indexing."}
    except Exception as e:
        LOGGER.error("Upload failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to upload document")


@app.get("/documents")
def list_documents(_identity: str = Depends(require_admin)):
    settings = get_settings()
    if not settings.docs_path.exists():
        return {"documents": []}

    vector_exists = settings.vector_store_path.exists()
    docs = []
    for ext in ["*.pdf", "*.md", "*.docx", "*.csv"]:
        for doc in settings.docs_path.glob(ext):
            docs.append({
                "name": doc.name,
                "status": "Processing" if doc.name in INDEXING_QUEUE else (
                    "Indexed" if vector_exists else "Pending"
                ),
                "size": doc.stat().st_size,
            })
    return {"documents": docs}


@app.delete("/documents/{filename}")
async def delete_document(
    filename: str,
    background_tasks: BackgroundTasks,
    _identity: str = Depends(require_admin),
):
    settings = get_settings()
    safe_name = _safe_filename(filename)
    file_path = settings.docs_path / safe_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        file_path.unlink()
        remaining_files = [
            f for ext in ["*.pdf", "*.md", "*.docx", "*.csv"]
            for f in settings.docs_path.glob(ext)
        ]
        if not remaining_files:
            if settings.vector_store_path.exists():
                shutil.rmtree(settings.vector_store_path)
            return {"status": "success", "message": f"Deleted {safe_name} and cleared empty knowledge base."}

        background_tasks.add_task(build_indices_and_refresh, app)
        return {"status": "success", "message": f"Deleted {safe_name} and queued index rebuild."}
    except Exception as e:
        LOGGER.error("Failed to delete document %s: %s", safe_name, e)
        raise HTTPException(status_code=500, detail="Failed to delete document")


@app.delete("/documents")
async def clear_all_documents(_identity: str = Depends(require_admin)):
    settings = get_settings()
    try:
        if settings.docs_path.exists():
            for ext in ["*.pdf", "*.md", "*.docx", "*.csv"]:
                for doc_file in settings.docs_path.glob(ext):
                    doc_file.unlink()
        if settings.vector_store_path.exists():
            shutil.rmtree(settings.vector_store_path)
        return {"status": "success", "message": "All documents and knowledge bases cleared."}
    except Exception as e:
        LOGGER.error("Failed to clear knowledge base: %s", e)
        raise HTTPException(status_code=500, detail="Failed to clear knowledge base")
