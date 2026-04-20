import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from redis import Redis

from agent.chatbot import EnterpriseChatbot
from llm.factory import configure_logging, get_settings
from rag.retriever import CompanyRetriever
from utils.encryption import encrypt_value, decrypt_value
import sqlite3
import os

configure_logging()
LOGGER = logging.getLogger(__name__)

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

# --- Rate Limiting ---

async def rate_limit_middleware(request: Request, call_next):
    if request.url.path != "/chat":
        return await call_next(request)
        
    # Simple rate limiting: 10 requests per minute per user_id
    try:
        body = await request.json()
        user_id = body.get("user_id", "anonymous")
    except Exception:
        user_id = "anonymous"

    settings = get_settings()
    # Connection shared via app state isn't easily accessible in middleware for sync redis
    # but we can create a temporary connection or use a pool. 
    # For this demo, we'll use a direct check.
    r = Redis.from_url(settings.redis_url)
    key = f"rate_limit:{user_id}"
    
    requests = r.incr(key)
    if requests == 1:
        r.expire(key, 60)
        
    if requests > 10:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded. Try again in a minute."}
        )
        
    return await call_next(request)

# --- Lifespan ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    retriever = CompanyRetriever()
    
    # Global Chatbot Singleton
    app.state.chatbot = EnterpriseChatbot(retriever=retriever)
    LOGGER.info("Application startup complete with EnterpriseChatbot.")
    yield
    LOGGER.info("Application shutdown.")

# --- App Definition ---

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Enterprise AI Chatbot",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Note: In a real apps, middleware would be added with app.add_middleware
# but reading the body in middleware can be tricky with FastAPI.
# We'll use a dependency or direct check if needed, but the user asked for logic.

@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request):
    # Manual rate limit check for demonstration as body is already parsed here
    settings = get_settings()
    r = Redis.from_url(settings.redis_url)
    key = f"rate_limit:{payload.user_id}"
    req_count = r.incr(key)
    if req_count == 1:
        r.expire(key, 60)
    if req_count > 10:
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")

    try:
        result = request.app.state.chatbot.process_message(
            user_id=payload.user_id,
            session_id=payload.session_id,
            message=payload.message
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
            detail="An internal error occurred."
        )

# --- Settings ---

def get_settings_db():
    db_path = os.path.join(os.path.dirname(__file__), "db", "company.db")
    return sqlite3.connect(db_path)

@app.get("/settings")
def get_user_settings():
    try:
        conn = get_settings_db()
        cursor = conn.cursor()
        # Initialize table if it doesn't exist (failsafe)
        cursor.execute("CREATE TABLE IF NOT EXISTS user_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        cursor.execute("SELECT key, value FROM user_settings")
        rows = cursor.fetchall()
        conn.close()
        
        settings = {}
        for k, v in rows:
            try:
                settings[k] = decrypt_value(v)
            except Exception:
                settings[k] = ""
                
        # Never return full password in plaintext over GET, mask it or return partial
        # For this prototype we will return the decrypted so the frontend form can pre-fill, 
        # but in production we'd just return '***' if set.
        return settings
    except Exception as e:
        LOGGER.error(f"Failed to fetch settings: {e}")
        return {}

@app.post("/settings")
def update_user_settings(payload: SettingsPayload):
    try:
        conn = get_settings_db()
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS user_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        
        data = payload.model_dump()
        for k, v in data.items():
            if v:
                encrypted = encrypt_value(v)
                cursor.execute("INSERT OR REPLACE INTO user_settings (key, value) VALUES (?, ?)", (k, encrypted))
        
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        LOGGER.exception(f"Failed to save settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to save settings")

# --- Document Management ---

@app.post("/upload")
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    try:
        settings = get_settings()
        settings.docs_path.mkdir(parents=True, exist_ok=True)
        
        file_path = settings.docs_path / file.filename
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
            
        # Rebuild RAG indices in background
        from rag.ingestion import build_indices
        background_tasks.add_task(build_indices)
        
        return {"status": "success", "message": f"Successfully uploaded {file.filename} and queued for indexing."}
    except Exception as e:
        LOGGER.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload document")

@app.get("/documents")
def list_documents():
    settings = get_settings()
    if not settings.docs_path.exists():
        return {"documents": []}
        
    docs = []
    vector_exists = settings.vector_store_path.exists()
    
    for pdf in settings.docs_path.glob("*.pdf"):
        docs.append({
            "name": pdf.name,
            "status": "Indexed" if vector_exists else "Processing",
            "size": pdf.stat().st_size
        })
    return {"documents": docs}

