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
python -m rag.ingestion                  # rebuild Qdrant + BM25 + parent-store indices from data/company_docs/ (also runnable as build_indices())
python evaluate.py                       # run the LLM-as-judge RAG eval over data/eval_dataset.json
python -m pytest tests/                  # run the backend test suite (agent contracts, supervisor routing, encryption, import guard, security)
ruff check .                             # lint (installed but not yet in requirements.txt/CI)
```

Frontend (from `frontend/`):
```bash
npm install
npm run dev       # next dev
npm run build
npm run lint      # next lint
```

`tests/` has a real pytest suite (agent return-contract tests, supervisor routing, an encryption
round-trip, an import guard, and security checks) — it's not wired into CI yet. Separately,
`evaluate.py` is an LLM-as-judge **quality** harness, not unit tests — it calls live LLMs and the
real retriever, so it needs API keys, built indices, and (ideally) Redis. The `evaluating-with-ragas`
skill (`.claude/skills/evaluating-with-ragas/scripts/run_ragas.py`) runs the same idea through RAGAS
metrics (faithfulness, answer relevancy, context precision/recall); on Groq, pass a low
`RunConfig(max_workers=...)` and expect `answer_relevancy` to need `strictness=1` — Groq's API
rejects `n>1`, which several RAGAS metrics request by default.

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
  with a heuristic `department` metadata, then does **parent-child chunking**
  (`split_parent_child`): an 800-token parent split (richer LLM context, stored in `ParentStore`
  as JSON via `rag/parent_store.py`) and a nested 200-token child split per parent (precise
  retrieval unit, embedded and stored in **Qdrant**, `rag/qdrant_store.py`). Each child chunk
  carries its `parent_id` in metadata. Also writes a pickled `bm25_chunks.pkl` to
  `data/faiss_index/` for the sparse side (the directory name predates the Qdrant migration).
- **Retrieval** (`retriever.py::CompanyRetriever.retrieve`): LLM query-rewrite → Qdrant dense
  search (`retriever_top_k × 4`) + BM25 sparse search over the same corpus → dedupe → CrossEncoder
  rerank → keep top `retriever_top_k` → **parent expansion** (each surviving child chunk is
  swapped for its 800-token parent text before being passed to the answer LLM). Indices are
  lazy-loaded and cached on the instance; `clear_cache()` forces a reload (called by the
  background re-indexing task after uploads), and the Qdrant client releases its file lock before
  a re-index runs so it doesn't collide with itself.
- **Corrective RAG loop** (`agents/retriever_agent.py`, LangGraph): retrieve → grade each doc
  relevant/irrelevant (LLM, fail-opens on error) → if too few relevant and iterations < 2, rewrite
  the query and retry → otherwise generate the answer from what's relevant.

### Models (`llm/factory.py`)

`get_chat_model(provider)` builds a **native** LangChain chat model per provider (`ChatGroq`,
`ChatOpenAI`, `ChatAnthropic`, `ChatBedrock`) — it used to route everything through
`langchain_community`'s `ChatLiteLLM` wrapper, but that class was removed upstream when
`langchain-community` deprecated several third-party integrations, so `requirements.txt` now pins
`langchain-community==0.3.31` (the last version with `chat_models/vertexai.py`, which `ragas`
still hard-imports) and the factory talks to each provider's own SDK directly instead.
`get_embeddings()` (HuggingFace MiniLM, CPU) and `get_reranker()` (CrossEncoder, CPU) are
`lru_cache`d singletons — they load models lazily on first use, so the first retrieval request is
slow. `get_llm_with_failover()` returns a `_FailoverChatModel` that actually does try each
provider in `FAILOVER_PROVIDERS` order at every `invoke`/`stream` call (one quick retry per
provider before moving to the next, since a single transient connection blip shouldn't burn the
whole chain), and implements `bind`/`bind_tools` so it still works as a drop-in model for
LangGraph's `create_react_agent` (used by `ToolAgent`).

### Document management endpoints

`/upload`, `/documents`, `/documents/{filename}` (`app.py`) mutate `data/company_docs/` and trigger
`build_indices()` as a FastAPI `BackgroundTask`, refreshing the live retriever's cache afterward.
The in-flight re-indexing set lives in Redis (`nexusai:indexing_queue`, a 1h-TTL set — see
`_indexing_queue_add/_remove/_contains/_clear` in `app.py`), not an in-process variable, so status
is correct across multiple workers/replicas.

## Conventions & gotchas

- Every agent's `run()` is expected to return a `dict` with at least `answer` and `source`; the
  orchestrator coerces stragglers but new agents should follow the `{answer, source, confidence}`
  shape so the validator and `ChatResponse` model line up.
- Secrets stored via `/settings` (MySQL URI, SMTP creds) are Fernet-encrypted with
  `MASTER_ENCRYPTION_KEY` (`utils/encryption.py`) and live in the `user_settings` table of
  `db/company.db`. `GET /settings` returns masked placeholders, never decrypted values.
  `validate_key()` runs at startup (`app.py` lifespan) and fails fast if the key is missing/invalid.
- Rate limiting is enforced inline inside the `/chat` handler via `_enforce_rate_limit`, keyed on
  source IP (`rate_limit:anon:{ip}`, Redis `INCR`, `RATE_LIMIT_PER_MINUTE` per minute — default 10).
- CORS is restricted to `CORS_ALLOWED_ORIGINS` (defaults to `http://localhost:3000`), not a wildcard.
- Redis URLs are normalized to `127.0.0.1` and prefixed with `redis://` inside the memory/cache
  classes; both degrade gracefully (or to a local dict) when Redis is unavailable.
- `db/company.db` is gitignored and seeded by `db/init_db.py` (idempotent — it wipes and re-inserts
  demo rows on each run). The `.gitignore` pattern `faiss_index/` also matches `data/faiss_index/`
  (Qdrant/BM25/parent-store files, directory name predates the FAISS→Qdrant migration), so it is
  **not committed**, despite what older docs said. A fresh clone must run `python -m rag.ingestion`
  before the retriever route works, and that in turn needs real source documents committed under
  `data/company_docs/` (not itself gitignored) — see the 7 policy PDFs added 2026-07-02, matching
  `data/eval_dataset.json`'s expected sources.
- `HF_HUB_DISABLE_XET` is set in `.env` — HuggingFace Hub's `hf_xet` fast-download backend hangs
  indefinitely in some sandboxed/restricted-network environments; this forces the plain HTTP
  downloader for model downloads (embeddings, reranker).

