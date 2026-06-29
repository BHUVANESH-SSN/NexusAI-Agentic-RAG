# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

NexusAI — a multi-agent Agentic RAG chatbot. A FastAPI backend (`app.py`) exposes a chat
API orchestrated by a Supervisor→Worker→Validator pipeline over LangChain/LangGraph, with a
separate Next.js 14 frontend in `frontend/`.

## Commands

Backend (run from repo root, with `venv` activated):
```bash
source venv/bin/activate
pip install -r requirements.txt          # docx2txt + pandas are also required (already in requirements)
python -m uvicorn app:app --reload       # serve API on :8000

python -m db.init_db                     # (re)seed db/company.db with demo employees/violations + settings table
python -m rag.ingestion                  # rebuild FAISS + BM25 indices from data/company_docs/ (also runnable as build_indices())
python evaluate.py                       # run the LLM-as-judge RAG eval over data/eval_dataset.json
```

Frontend (from `frontend/`):
```bash
npm install
npm run dev       # next dev
npm run build
npm run lint      # next lint (only linter in the repo; backend has no configured linter/test runner)
```

There is **no automated test suite**. `evaluate.py` is a scored quality harness, not unit tests —
it calls live LLMs and the real retriever, so it needs API keys, built indices, and (ideally) Redis.

## Configuration

All backend config flows through `llm/factory.py::get_settings()` (a cached `Settings` dataclass
populated from `.env` — copy `.env.example` to `.env`). Never read env vars directly elsewhere;
add new config as a `Settings` field. Key vars: `LLM_PROVIDER` (`groq`|`openai`|`anthropic`|`bedrock`),
`GROQ_API_KEY`/`OPENAI_API_KEY`, `REDIS_URL`, `MASTER_ENCRYPTION_KEY` (Fernet key — required for the
`/settings` endpoints and any DB/email feature that decrypts stored secrets).

## Architecture

Request flow for `POST /chat` (see `agents/chatbot.py::EnterpriseChatbot.process_message`):

1. **Semantic cache** (`memory/semantic_cache.py`) — embeds the query, linearly scans
   `semantic_cache:*` Redis keys for cosine similarity ≥ 0.96; on hit, returns the cached result
   and skips the whole pipeline (still records the turn in history).
2. **History load** — `memory/redis_memory.py::RedisSessionManager` reads `chat_history:{user_id}:{session_id}`
   from Redis (1h TTL), with an in-process `_local_fallback` dict if Redis is down.
3. **Supervisor routing** (`router/supervisor.py`) — an LLM classifies the message into exactly one
   of `retriever | db | tool | chat`; defaults to `chat` on any failure.
4. **Worker agent** (one of, in `agents/`):
   - `retriever_agent.py` → hybrid RAG (see below), returns structured `{answer, source, confidence}`.
   - `db_agent.py` → LangChain `create_sql_agent` over SQLite `db/company.db` (or a MySQL URI pulled
     from the encrypted `user_settings` table if configured).
   - `tool_agent.py` → LangGraph `create_react_agent` with email tools, enforcing a
     **Draft → Confirm → Execute** human-in-the-loop protocol (`tools/email_tool.py`). Sending
     falls back to a mock/log if SMTP creds aren't in `user_settings`.
   - `chat_agent.py` → plain conversational LLM for greetings/follow-ups.
5. **Validation** (`agents/validation_agent.py`) — a final LLM pass that re-grounds/normalizes every
   answer into the `{answer, source, confidence}` JSON shape before returning. This is the single
   exit point; all worker outputs are funneled through it.
6. **Persist** the turn to Redis history and **save** to the semantic cache.

The `EnterpriseChatbot` is a singleton built once in the FastAPI `lifespan` and stored on
`app.state.chatbot`.

### RAG pipeline (`rag/`)

- **Ingestion** (`ingestion.py`): loads PDF/MD/DOCX/CSV from `data/company_docs/`, tags each page
  with a heuristic `department` metadata, then does **semantic chunking** — splits text into
  sentences, embeds them, and starts a new chunk when adjacent-sentence cosine similarity drops
  below 0.82 (or `CHUNK_SIZE` is exceeded). Writes a FAISS index plus a pickled `bm25_chunks.pkl`
  to `data/faiss_index/`.
- **Retrieval** (`retriever.py::CompanyRetriever.retrieve`): LLM query-rewrite → hybrid fetch
  (FAISS dense top-10 + BM25 sparse top-10) → dedupe → CrossEncoder rerank → keep top 3.
  Indices are lazy-loaded and cached on the instance; `clear_cache()` forces a reload (called by
  the background re-indexing task after uploads).

### Models (`llm/factory.py`)

`get_chat_model()` is the provider switchboard; `get_embeddings()` (HuggingFace MiniLM, CPU) and
`get_reranker()` (CrossEncoder, CPU) are `lru_cache`d singletons — they load models lazily on first
use, so the first retrieval request is slow. `get_llm_with_failover()` currently just returns the
configured model (despite the name, no actual failover is wired up yet).

### Document management endpoints

`/upload`, `/documents`, `/documents/{filename}` (`app.py`) mutate `data/company_docs/` and trigger
`build_indices()` as a FastAPI `BackgroundTask`, refreshing the live retriever's cache afterward.
`INDEXING_QUEUE` (a module-level set) tracks in-flight re-indexing for status display.

## Conventions & gotchas

- Every agent's `run()` is expected to return a `dict` with at least `answer` and `source`; the
  orchestrator coerces stragglers but new agents should follow the `{answer, source, confidence}`
  shape so the validator and `ChatResponse` model line up.
- Secrets stored via `/settings` (MySQL URI, SMTP creds) are Fernet-encrypted with
  `MASTER_ENCRYPTION_KEY` (`utils/encryption.py`) and live in the `user_settings` table of
  `db/company.db`.
- Rate limiting is enforced inline inside the `/chat` handler (Redis `INCR` per `user_id`, 10/min) —
  the `rate_limit_middleware` function in `app.py` is defined but not registered.
- Redis URLs are normalized to `127.0.0.1` and prefixed with `redis://` inside the memory/cache
  classes; both degrade gracefully (or to a local dict) when Redis is unavailable.
- `db/company.db` is gitignored and seeded by `db/init_db.py` (idempotent — it wipes and re-inserts
  demo rows on each run). FAISS indices under `data/faiss_index/` are committed.
- `config.py` is a thin shim that just exposes `settings = get_settings()`; prefer importing from
  `llm.factory` directly.
- Heads-up: `agents/retriever_agent.py` has a stray module-level `base_dir = "/"` line wedged inside
  the class body (~line 60); leave class methods correctly indented and don't propagate that pattern.

