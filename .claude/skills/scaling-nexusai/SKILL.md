---
name: scaling-nexusai
description: Make the NexusAI FastAPI + LangChain RAG backend scale — replace the O(n) semantic-cache scan with a vector index, move in-process state into Redis for multi-worker safety, offload re-indexing to a task queue, stream /chat, and cap input sizes. Use when implementing performance/scale work (improvements.md §3 / issues M1, M2, M9).
version: 1.0.0
---

# Scaling NexusAI

## Overview

NexusAI today can't run safely with `uvicorn --workers >1`: it keeps state in process-local globals,
the semantic cache does a blocking `KEYS` scan + per-entry cosine on every request, and uploads
rebuild the whole index synchronously in-process. This skill is the how-to for fixing those. It
implements `improvements.md §3` / `issues.md` M1, M2, M9.

## When to Use

- Reworking `memory/semantic_cache.py`, `memory/redis_memory.py`, or `INDEXING_QUEUE` in `app.py`.
- Adding streaming to `/chat` or input-size caps.
- Moving re-indexing off the request path.

## Patterns

### Semantic cache: vector index, not a scan (M2)
- `check()` currently calls `redis_client.keys("semantic_cache:*")` (blocking on the whole keyspace)
  and cosine-compares every entry. Replace with a vector index: Redis Search (RediSearch
  `FT.SEARCH` KNN) or a small FAISS index keyed by query embedding.
- Keep the **≥ 0.96** cosine hit threshold and the existing behavior: on hit return the cached
  result and still record the turn in history; on miss run the pipeline and save to cache.
- Preserve the graceful no-op when Redis is unavailable.

### Shared state across workers (M1)
- Move `INDEXING_QUEUE` (upload/re-index status) into Redis (a set/hash) so all workers agree.
- Move `RedisSessionManager._local_fallback` to be a genuine last-resort only; Redis is the source of
  truth for `chat_history:{user_id}:{session_id}` (1h TTL).
- Leave the `lru_cache` model singletons per-process (loading them is the point of caching) — just
  don't rely on them for cross-worker correctness.

### Re-indexing off the request path
- Replace the `BackgroundTask` full rebuild with a task queue (RQ / Celery / arq). Rebuild
  incrementally where possible. After a rebuild, refresh the live retriever via `clear_cache()`.

### Streaming `/chat`
- Add SSE / `StreamingResponse`. Stream the worker's answer tokens, but keep the validated
  `{answer, source, confidence}` contract for non-streaming clients — the ValidationAgent stays the
  single exit point.

### Input caps (M9)
- Add `max_message_length` to `ChatRequest` and a max upload byte size, sourced from settings.

## Invariants You MUST Preserve

- Redis-down graceful degradation must survive every change (try/except guards; local fallback as a
  last resort).
- Config via `get_settings()` only — add `cache_backend`, `task_queue_url`, `max_message_length`,
  `max_upload_bytes` as `Settings` fields and to `.env.example`.
- Agent return contract and ValidationAgent exit point intact for non-streaming responses.
- Don't break the FAISS/BM25 index format produced by `rag/ingestion.py`.

## Verify

```bash
source venv/bin/activate
python -c "import app"
python -m uvicorn app:app --workers 2          # state consistent across workers
# same query twice → second request served via the cache vector index (check logs)
```

For diagnosing cache misses or Redis behavior, use `debugging-nexusai`. For behavior-preserving
restructuring, use `refactoring-nexusai`.

## Don'ts

- Don't use `KEYS`/`SCAN`-then-compare for cache lookups — that's the bug.
- Don't introduce process-local state that two workers would disagree on.
- Don't block the request thread on a full re-index.
