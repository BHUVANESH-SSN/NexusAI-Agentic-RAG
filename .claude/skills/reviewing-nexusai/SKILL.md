---
name: reviewing-nexusai
description: Review NexusAI backend changes (FastAPI + LangChain multi-agent RAG) for correctness, the agent contract, security of secrets, prompt/RAG quality, and project conventions. Use when reviewing a diff, PR, or branch for this repo.
version: 1.0.0
---

# Reviewing NexusAI

## Overview

A focused review checklist for this multi-agent RAG codebase. Prioritize the pipeline contract,
secret handling, and graceful degradation — these break silently and are easy to regress.

## Review Checklist

### Pipeline & contract
- [ ] Every agent `run()` still returns `{answer, source[, confidence]}`. New agents follow suit.
- [ ] `ValidationAgent` remains the final step; nothing returns to `app.py` bypassing it.
- [ ] Supervisor labels stay in sync (`retriever | db | tool | chat`) across the prompt,
      `route()`, and the dispatch in `agents/chatbot.py`. Default-to-`chat` fallback intact.
- [ ] New agents are wired in `EnterpriseChatbot.__init__`.

### Config & secrets
- [ ] No `os.getenv` outside `llm/factory.py`; new config added as a `Settings` field.
- [ ] No secrets/API keys hardcoded or logged. Check log lines don't print tokens, passwords,
      decrypted SMTP creds, or full MySQL URIs.
- [ ] Secrets written to `user_settings` go through `encrypt_value`; reads through `decrypt_value`.
- [ ] `.env`, `db/*.db` not committed.

### Robustness
- [ ] Redis-dependent code (memory, cache, rate limit) degrades gracefully when Redis is down.
- [ ] External calls (LLM, SMTP, SQL) are wrapped in try/except with a sensible fallback dict.
- [ ] No model loading at import time — stays lazy/cached in the factory.

### RAG & prompts
- [ ] Prompt edits keep the "use ONLY provided context / don't hallucinate" grounding rules.
- [ ] Retrieval changes (top-k, thresholds, rerank) are intentional; consider re-running RAGAS eval.
- [ ] `allow_dangerous_deserialization=True` on FAISS load is only ever used on trusted local index
      files (flag if index source becomes user-controlled).

### Web layer
- [ ] CORS is currently `allow_origins=["*"]` — flag if shipping to prod.
- [ ] Rate limiting: note the inline `/chat` check vs the unregistered `rate_limit_middleware`;
      changes shouldn't leave both half-wired.
- [ ] File upload (`/upload`) validates/limits filenames and types if extended.

### Conventions
- [ ] Logging via `LOGGER = logging.getLogger(__name__)`, `%`-style args.
- [ ] Matches surrounding naming, structure, and import style.

## How to Review

1. `git diff main...HEAD` (or the PR range). Map each change to a pipeline stage.
2. For correctness bugs and cleanups, you can also run the built-in `/code-review` skill.
3. Confirm it imports (`python -c "import app"`) and, for behavior changes, smoke-test `/chat`.
4. Summarize findings by severity: blocking (contract/secret/crash) vs. nits.

## Known Pre-existing Issues (don't attribute to the diff)
- Stray `base_dir = "/"` in `agents/retriever_agent.py` (~line 60).
- `rate_limit_middleware` defined but unregistered.
- `get_llm_with_failover()` performs no failover.
</content>
