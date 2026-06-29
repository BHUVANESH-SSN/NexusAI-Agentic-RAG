---
name: debugging-nexusai
description: Diagnose runtime failures in the NexusAI FastAPI/LangChain RAG backend — bad routing, empty retrieval, Redis/cache misses, SQL agent errors, email tool failures, or 500s on /chat. Use when the chatbot returns wrong/empty answers or throws.
version: 1.0.0
---

# Debugging NexusAI

## Overview

Failures usually fall into one of six stages of the `/chat` pipeline
(`agents/chatbot.py::process_message`): semantic cache → history load → Supervisor routing →
worker agent → validation → persist. Localize the stage first, then drill in.

## First Moves

```bash
source venv/bin/activate
python -c "import app"                    # rule out import/syntax errors first
python -m uvicorn app:app --reload        # watch the structured logs while reproducing
redis-cli ping                            # confirm Redis is up (PONG)
```

Logs are the primary tool: the pipeline emits `Supervisor elected route: ...`,
`MEMORY_TRACE`, `[CACHE HIT]/[CACHE SAVE]`, and per-agent log lines. Set `LOG_LEVEL=DEBUG` in
`.env` for more. Every module uses `LOGGER = logging.getLogger(__name__)`.

## Symptom → Likely Cause

| Symptom | Where to look |
|---|---|
| 500 on `/chat` | `app.py` chat handler; check `LOGGER.exception` trace. Often missing API key or Redis. |
| Wrong agent handles query | `router/supervisor.py` — the LLM mislabeled; inspect the routed label in logs. Falls back to `chat` on any error. |
| "The document does not provide details" / empty | `rag/retriever.py` — no FAISS index built, BM25 pickle missing, or rerank dropped everything. Run `python -m rag.ingestion`. |
| `FileNotFoundError: FAISS index not found` | Indices not built; `data/faiss_index/` missing. Rebuild via ingestion. |
| Stale answers after upload | retriever cache not cleared; check `clear_cache()` ran in the `/upload` background task. |
| Repeated identical answers | semantic cache hit (similarity ≥ 0.96). Inspect `semantic_cache:*` keys; flush with `redis-cli FLUSHDB` if testing. |
| History not remembered | `memory/redis_memory.py` — Redis down (using local fallback dict, lost on restart) or wrong `user_id:session_id`. Check `MEMORY_TRACE`. |
| DB agent errors | `agents/db_agent.py` — `company.db` missing (run `python -m db.init_db`), or bad MySQL URI in `user_settings`. |
| Email not sent | `tools/email_tool.py` — no SMTP creds in `user_settings` → silently mock-logs; or `MASTER_ENCRYPTION_KEY` missing breaks decrypt. |
| `ValueError: ...KEY is missing` | required key absent from `.env` (`GROQ_API_KEY`, `MASTER_ENCRYPTION_KEY`, etc.). |
| Validation returns low-confidence fallback | `agents/validation_agent.py` JSON parse failed — the worker emitted non-JSON; check the worker's raw output. |

## Useful Probes

```bash
redis-cli keys 'chat_history:*'           # session history keys
redis-cli keys 'semantic_cache:*'         # cache entries
redis-cli lrange chat_history:USER:SESSION 0 -1
python -m utils.redis_inspect             # project's Redis inspector, if applicable
sqlite3 db/company.db '.tables'           # confirm schema seeded
```

Reproduce a single turn without the server:
```python
from rag.retriever import CompanyRetriever
from agents.chatbot import EnterpriseChatbot
bot = EnterpriseChatbot(retriever=CompanyRetriever())
print(bot.process_message("u1", "s1", "your query here"))
```

## Notes

- First request after boot is slow: HuggingFace embeddings + CrossEncoder load lazily (CPU).
- Redis URLs are normalized to `127.0.0.1` and prefixed `redis://` inside memory/cache classes.
- Don't trust the answer being correct just because there's no exception — the LLM can hallucinate;
  cross-check against `format_documents` context in the logs.
</content>
