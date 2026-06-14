---
name: refactoring-nexusai
description: Refactor NexusAI backend code (FastAPI + LangChain multi-agent RAG) while preserving the Supervisor→Worker→Validator contract. Use when restructuring agents, the RAG pipeline, memory/cache layers, or LLM factory without changing external behavior.
version: 1.0.0
---

# Refactoring NexusAI

## Overview

NexusAI is a multi-agent Agentic RAG chatbot: a FastAPI backend (`app.py`) orchestrating a
Supervisor→Worker→Validator pipeline (`agents/`, `router/`) over LangChain/LangGraph, plus a
Next.js frontend. This skill keeps refactors safe by respecting the project's invariants.

## When to Use

- Splitting/merging agents, extracting shared agent base classes, or renaming routes.
- Reworking the RAG pipeline (`rag/ingestion.py`, `rag/retriever.py`).
- Consolidating Redis/memory/cache code (`memory/`).
- Cleaning up `llm/factory.py`, config handling, or removing dead code.

## Invariants You MUST Preserve

1. **Agent return contract**: every agent `run()` returns a `dict` with at least `answer` and
   `source` (ideally `+ confidence`). The orchestrator (`agents/chatbot.py`) and the `ChatResponse`
   model in `app.py` depend on this. The `ValidationAgent` is the single exit point — keep it last.
2. **Routing labels**: the Supervisor emits exactly `retriever | db | tool | chat`. If you rename a
   route, update `router/supervisor.py`, the `process_message` dispatch, and the prompt together.
3. **Config flows through `llm/factory.py::get_settings()`** (a frozen, `lru_cache`d dataclass).
   Never read `os.getenv` outside the factory — add a new `Settings` field instead. `get_settings`,
   `get_embeddings`, `get_reranker` are cached singletons; don't break their cache semantics.
4. **Graceful degradation**: Redis memory and semantic cache must keep working when Redis is down
   (local fallback dict / no-op). Preserve the try/except connection guards.
5. **HitL email protocol**: `tools/email_tool.py` keeps the `prepare_email_draft` → confirm →
   `execute_send_email` split. Do not collapse drafting and sending.
6. **Encryption boundary**: secrets in the `user_settings` table are Fernet-encrypted via
   `utils/encryption.py`. Encrypt on write, decrypt on read — never store plaintext.

## Process

1. **Map the blast radius.** Grep for the symbol across `agents/`, `router/`, `rag/`, `memory/`,
   `app.py`. The chatbot wires every agent in `EnterpriseChatbot.__init__` — update it in lockstep.
2. **Make behavior-preserving edits** in small steps; match existing logging style
   (`LOGGER = logging.getLogger(__name__)`, `%`-style args).
3. **Verify it still imports and serves**:
   ```bash
   source venv/bin/activate
   python -c "import app"                       # catches import/indentation errors
   python -m uvicorn app:app --reload           # smoke test /chat
   ```
4. **Re-run the eval harness** if retrieval/answer logic changed (see `evaluating-with-ragas`).

## Known Issues to Fix Opportunistically

- `agents/retriever_agent.py` has a stray module-level `base_dir = "/"` wedged in the class body
  (~line 60) — remove it when touching that file.
- `rate_limit_middleware` in `app.py` is defined but never registered; rate limiting is duplicated
  inline in the `/chat` handler. Consolidate to one mechanism.
- `get_llm_with_failover()` does not actually fail over despite its name and the `FAILOVER_PROVIDERS`
  setting. Either implement failover or rename to reflect reality.
- `memory/manager.py` (`SessionMemoryManager`) appears superseded by `memory/redis_memory.py`
  (`RedisSessionManager`); confirm it's unused before relying on it.

## Don'ts

- Don't change the JSON shape returned to the frontend without updating `frontend/` callers.
- Don't introduce blocking model loads at import time — keep them lazy in the factory.
- Don't commit `db/company.db` or `.env` (both gitignored).
</content>
