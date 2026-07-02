# Improvements — NexusAI (company-chatbot-langchain)

Prioritized, actionable improvements for the project. Pairs with [issues.md](issues.md), which
catalogues the underlying problems. Items are ordered so that fixing the top of the list first gives
the most value and unblocks everything else.

Most of §0–§2 and parts of §3–§5 below have since been resolved (verified 2026-07-02) — kept here,
marked `[DONE]`, so the history of what was fixed and why is still visible. Open items remain
unmarked.

---

## 0. Make it run — `[DONE]`

- `[DONE]` The stray `base_dir = "/"` in `agents/retriever_agent.py` is gone; the module imports and
  boots cleanly (`python -c "import app"` succeeds).
- `[DONE]` `tests/test_import_guard.py` now exists and exercises this exact class of failure.

---

## 1. Security hardening — `[DONE]`

Verified directly in code (not just README claims):
- `[DONE]` Auth: `require_identity`/`require_admin` (`security.py`) gate `/chat` vs
  `/settings`/`/upload`/`/documents`.
- `[DONE]` `GET /settings` returns masked placeholders; decryption only happens server-side at
  point of use.
- `[DONE]` SQL agent: read-only SQLite URI (`mode=ro`), `user_settings` excluded.
- `[DONE]` Uploads: `os.path.basename`, extension allow-list, size cap.
- `[DONE]` Email tool: domain allow-list, hourly cap, Draft → Confirm → Execute protocol.
- `[DONE]` CORS: `CORS_ALLOWED_ORIGINS` (default `http://localhost:3000`), not `["*"]`.
- `[DONE]` Rate limiting: `_enforce_rate_limit` in `app.py`, keyed on source IP via Redis `INCR`,
  `RATE_LIMIT_PER_MINUTE` (default 10) — registered and active, not a dangling unused function.

Re-run `security-review` / `pentesting-nexusai` after any auth/SQL/upload/email changes.

---

## 2. Correctness & configuration — `[DONE]`

- `[DONE]` `retriever_top_k` is honored (`rag/retriever.py`: Qdrant search top `retriever_top_k × 4`,
  keep top `retriever_top_k` after rerank).
- `[DONE]` `get_llm_with_failover()` does real cross-provider failover: `_FailoverChatModel`
  (`llm/factory.py`) tries each provider in `FAILOVER_PROVIDERS` order at every `invoke`/`stream`
  call, with one retry per provider before moving on. Also implements `bind`/`bind_tools` so it
  works as a drop-in for `create_react_agent` (`ToolAgent`).
- `[DONE]` `MASTER_ENCRYPTION_KEY` is validated at startup (`utils/encryption.py::validate_key()`,
  called from the `app.py` lifespan) — fails fast with a generation hint, not deep in a handler.
- `[DONE]` Chunking replaced entirely: `rag/ingestion.py::split_parent_child` uses
  `RecursiveCharacterTextSplitter` at two granularities (800-token parent / 200-token child)
  instead of the old naive `.`-split / cosine-threshold semantic chunker.
- `[DONE]` DB path is centralized via `Settings.db_path` (`llm/factory.py`), consumed consistently
  by `app.py`, `agents/db_agent.py`, `tools/email_tool.py`. (`db/init_db.py`'s seed script derives
  the same path independently, by design — it predates `Settings` and doesn't need `.env`.)
- Still open: multi-format delete logic (`app.py`) — verify it globs `*.pdf *.md *.docx *.csv`, not
  just `*.pdf`, when deciding whether the KB is empty.

---

## 3. Scalability & performance

- `[DONE]` Semantic cache is ANN-backed via Qdrant (`memory/semantic_cache.py`), not a linear
  `KEYS`+cosine scan.
- `[DONE]` Cross-worker state: the indexing-in-progress set lives in Redis
  (`nexusai:indexing_queue`, 1h TTL — see `_indexing_queue_*` in `app.py`), not an in-process dict,
  so `--workers >1` is safe for this piece.
- `[DONE]` Qdrant lock safety: the retriever releases its file lock before a background re-index
  runs, so re-indexing doesn't collide with itself.
- `[DONE]` Input size caps: `ChatRequest.message` capped at 4096 chars, `user_id`/`session_id` at
  128; uploads capped at `MAX_UPLOAD_BYTES` (20 MB default).
- **Still open — re-indexing is still synchronous-in-process**: `/upload` rebuilds the *entire*
  index from scratch as a FastAPI `BackgroundTask` on every upload. For larger corpora, move to a
  real task queue (RQ/Celery/arq) and rebuild incrementally.
- **Still open — no response streaming**: `/chat` waits for the full Supervisor→Worker→Validator
  pipeline before returning. Add `StreamingResponse`/SSE so the UI can show tokens as they arrive.

---

## 4. Quality, testing & DX

- `[DONE]` Test suite exists: `tests/` — agent return-contract tests, supervisor routing, an
  encryption round-trip, an import guard, and security checks (`conftest.py` + 5 test files).
  **Still open**: not wired into CI yet (no `.github/workflows` step runs `pytest`).
- `[DONE]` Dead code removed (2026-07-02): `config.py` (unused shim — every caller already imports
  `llm.factory` directly), the unused `litellm` dependency (nothing imports it since `get_chat_model`
  moved to native per-provider SDKs), and 7 unused imports/variables across `agents/chat_agent.py`,
  `agents/validation_agent.py`, `app.py`, `evaluation/evaluator.py`, `memory/redis_memory.py`,
  `utils/redis_inspect.py` (via `ruff check --fix`). `memory/manager.py`, the stray `import time` in
  `app.py`, and the "duplicate `PyPDFLoader`" this list used to mention no longer exist either.
- `[DONE]` `/health` endpoint exists (`app.py`).
- `[DONE]` `ruff` added to `requirements.txt` as the project's linter (`ruff check .`); not yet
  wired into CI.
- **Still open — dependency pinning**: most entries in `requirements.txt` still use `>=`, not exact
  pins or a lockfile. `langchain-community` is now pinned to `==0.3.31` specifically (0.4.x dropped
  the `chat_models.vertexai`/`litellm` submodules that both our old `ChatLiteLLM` usage and `ragas`
  0.4.3 depend on) — the rest could still use a lockfile (`pip-compile`/`uv pip compile`) for
  reproducibility.
- **Still open — containerize**: no `Dockerfile`/`docker-compose.yml` yet. Needed before the
  EC2/Docker deployment work.

---

## 5. RAG evaluation (RAGAS)

- `[DONE]` RAGAS runs end-to-end via `.claude/skills/evaluating-with-ragas/scripts/run_ragas.py`,
  with `expected_answer` → `ground_truth` mapped for `context_recall`, and `ragas`/`datasets` in
  `requirements.txt`.
- `[DONE]` **Baseline tracked**: `evaluation/baselines/ragas_baseline_2026-07-02.json` (+ summary in
  `evaluation/baselines/README.md`) — `faithfulness=0.81, answer_relevancy=0.75,
  context_precision=1.00, context_recall=0.90` over the full 10-case set, against the real indexed
  policy docs (`data/company_docs/` was empty before this date; see git history).
- Fixed along the way: `run_ragas.py` was calling `RetrieverAgent(llm=..., retriever=...)`, which no
  longer matches the class's actual `__init__(self, retriever)` signature — now fixed. Groq rejects
  `n>1`, which `answer_relevancy`'s default `strictness=3` requests — now forced to `strictness=1`,
  and judge calls run at `RunConfig(max_workers=1)` to avoid rate-limit cascades being silently
  scored as 0 (ragas's default `raise_exceptions=False` masks failed judge calls as zero rather than
  surfacing them).
- **Still open — expand the eval set**: still only the original 10 retriever-path cases. RAGAS only
  covers `retriever`; the `db`/`tool`/`chat` routes still need separate checks against their
  expected route/behavior.

---

## 6. Product / feature ideas (optional, longer-term)

- **Conversation-aware retrieval**: the query rewriter already uses history — consider also returning
  citations/snippets to the frontend so users can verify sources.
- **Per-user knowledge bases / multi-tenancy**: today there's one shared Qdrant collection and one
  SQLite DB.
- **Admin UI for evals**: surface RAGAS/baseline trends in the existing Next.js dashboard.
- **Audit log** for sensitive actions (settings changes, emails sent, documents deleted).

---

### What's actually left

1. Wire `pytest` and `ruff` into CI (§4).
2. Containerize (`Dockerfile` + `docker-compose.yml`) — blocks the EC2/Docker deployment (§4).
3. Task-queue-based re-indexing + `/chat` streaming (§3).
4. Full dependency pinning/lockfile (§4).
5. Expand RAGAS coverage to `db`/`tool`/`chat` routes (§5).
6. §6 feature ideas, whenever there's appetite for them.
