# Improvements — NexusAI (company-chatbot-langchain)

Prioritized, actionable improvements for the project. Pairs with [issues.md](issues.md), which
catalogues the underlying problems. Items are ordered so that fixing the top of the list first gives
the most value and unblocks everything else.

---

## 0. Make it run (do this first)

The backend currently fails to import (see issue **C1**). Nothing else can be tested until this is fixed.

1. **Fix the syntax error.** Remove the stray `base_dir = "/"` from `agents/retriever_agent.py:60`.
   Then verify the whole backend compiles and boots:
   ```bash
   source venv/bin/activate
   python -m py_compile agents/*.py app.py     # must exit 0
   python -c "import app"                       # must not raise
   python -m uvicorn app:app --reload          # smoke-test POST /chat
   ```
2. **Add a `py_compile`/import check to CI** (or a pre-commit hook) so a non-importable file can never
   be committed again. This one-line guard would have caught C1.

---

## 1. Security hardening (high priority)

These address C2–C3 and H1–H8. Treat the app as currently unsafe to expose beyond localhost.

- **Add authentication** to every endpoint (API key, session token, or OAuth). At minimum, protect
  `/settings`, `/upload`, `/documents` behind admin auth and require an auth'd identity for `/chat`.
- **Stop returning secrets.** `GET /settings` should return masked placeholders (`"***set***"`),
  never decrypted SMTP passwords or DB URIs. Decryption should only happen server-side at point of use.
- **Lock down the SQL agent** (`agents/db_agent.py`): connect with a **read-only** DB user, restrict
  to a table allow-list, and consider validating/parsing generated SQL to reject DDL/DML. Never let it
  see the `user_settings` table.
- **Sanitize uploads** (`/upload`): use `os.path.basename`/`werkzeug.secure_filename`-style cleaning,
  validate extension against the supported set, enforce a max size, and reject anything that resolves
  outside `docs_path`. This also de-risks the pickle/FAISS deserialization (H2).
- **Constrain the email tool** (`tools/email_tool.py`): recipient domain allow-list, keep the
  draft→confirm→execute gate, and log/audit every send. Consider a hard send-rate cap.
- **Fix CORS**: replace `allow_origins=["*"]` + `allow_credentials=True` with an explicit origin list.
- **Real rate limiting**: key on authenticated identity or source IP (not client-supplied `user_id`),
  and either register the middleware or remove it — don't keep both half-wired.
- **Don't leak exceptions**: return generic user messages; log details server-side with `LOGGER.exception`.
- Run the bundled **`security-review`** and **`pentesting-nexusai`** skills after these changes.

---

## 2. Correctness & configuration

- **Honor configured settings**: use `settings.retriever_top_k` in `rag/retriever.py` instead of the
  hardcoded `[:3]`/`k=10`, and apply `chunk_overlap` (or remove the unused settings to avoid confusion).
- **Implement real failover** in `get_llm_with_failover()` using `FAILOVER_PROVIDERS` (try providers in
  order, catch and fall through), or rename it to `get_llm()` so it stops promising behavior it lacks.
- **Fix multi-format delete logic** (`app.py`): when deciding whether the KB is empty, glob all
  supported extensions (`*.pdf *.md *.docx *.csv`), not just `*.pdf`; same for `clear_all_documents()`.
- **Validate `MASTER_ENCRYPTION_KEY` at startup** (fail fast with a clear message) rather than deep in
  request handlers. Document how to generate one (`Fernet.generate_key()`).
- **Improve chunking** (`rag/ingestion.py`): replace the naive `.`-split with a sentence splitter
  (e.g. `nltk`/`spacy` or LangChain's `RecursiveCharacterTextSplitter` as a fallback) so retrieval
  quality doesn't suffer on abbreviations/decimals.

---

## 3. Scalability & performance

- **Replace the semantic-cache linear scan** (issue M2): stop using `KEYS` + per-key cosine. Use Redis
  vector search (RediSearch/`redis-py` vector index) or a small FAISS index keyed by query embedding so
  lookups are sub-linear and non-blocking.
- **Make state shareable across workers/replicas** (issue M1): move `INDEXING_QUEUE` and the memory
  fallback into Redis; treat the in-process dict only as a last-resort cache. Then the app can run with
  `--workers >1` safely.
- **Make re-indexing robust**: the current `BackgroundTask` rebuilds the full index in-process on every
  upload. For larger corpora, move ingestion to a real task queue (RQ/Celery/arq) and rebuild
  incrementally rather than from scratch.
- **Stream responses**: add streaming (SSE/`StreamingResponse`) for `/chat` so the UI shows tokens as
  they arrive instead of waiting for the full validate step.
- **Cap input sizes** (issue M9): set a max message length on `ChatRequest` and a max upload size.

---

## 4. Quality, testing & DX

- **Add a test suite** (`pytest`): unit-test the supervisor routing, each agent's `run()` contract
  (`{answer, source, confidence}`), the encryption round-trip, retriever formatting, and a mocked
  `/chat` end-to-end. Wire it into CI alongside the import check from section 0. (Currently there are
  **no tests** — issue M8.)
- **Pin and de-duplicate dependencies** (issue L1): remove the duplicate `langchain` line, pin
  versions (`==` or a lockfile), and drop the stale "install docx2txt/pandas manually" note in the
  README since they're already declared.
- **Delete dead code** (issue L2): remove `memory/manager.py` if unused, collapse `config.py`, drop
  unused imports (`import time` in `app.py`, the duplicate `PyPDFLoader` in `rag/ingestion.py`).
- **Centralize the DB path** (issue L3) into one helper or a `Settings` field instead of three
  independent derivations.
- **Add `/health`** and request-id logging (issue L6) for observability.
- **Containerize**: add a `Dockerfile` + `docker-compose.yml` (app + Redis) so setup is one command and
  matches the multi-service architecture in the README.

---

## 5. RAG evaluation (RAGAS)

- **Enable RAGAS** end-to-end using the `evaluating-with-ragas` skill and its
  `scripts/run_ragas.py` runner. To unlock `context_recall`, map the existing `expected_answer` field
  in `data/eval_dataset.json` to `ground_truth` (the runner currently falls back to the weaker
  `expected_source` — issue L5). The 10 cases already include `expected_answer` references.
- **Add `ragas` and `datasets` to `requirements.txt`** if you keep RAGAS in the project.
- **Track a baseline**: save the first RAGAS run (`--out baseline.json`) and re-run after any retrieval
  or prompt change to catch regressions in faithfulness / context precision.
- **Expand the eval set** beyond the current 10 cases and cover the `db`/`tool`/`chat` routes too
  (RAGAS covers the retriever path; the others need separate checks against the expected route).

---

## 6. Product / feature ideas (optional, longer-term)

- **Conversation-aware retrieval**: the query rewriter already uses history — consider also returning
  citations/snippets to the frontend so users can verify sources.
- **Per-user knowledge bases / multi-tenancy**: today there's one shared FAISS index and one SQLite DB.
- **Admin UI for evals**: surface RAGAS/baseline trends in the existing Next.js dashboard.
- **Audit log** for sensitive actions (settings changes, emails sent, documents deleted).

---

### Suggested order of attack

1. Section 0 (make it run) → 2. Section 1 security → 3. Section 2 correctness →
4. Section 4 tests/CI (so the rest stays fixed) → 5. Section 3 scalability →
6. Section 5 RAGAS → 7. Section 6 features.
</content>
