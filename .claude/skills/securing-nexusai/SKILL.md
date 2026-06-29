---
name: securing-nexusai
description: Harden the NexusAI FastAPI + LangChain RAG backend — add authentication, mask secrets, lock the SQL agent to read-only, sanitize uploads, constrain the email tool, fix CORS, and add real rate limiting. Use when implementing security fixes (improvements.md §1) or making the app safe to expose beyond localhost.
version: 1.0.0
---

# Securing NexusAI

## Overview

NexusAI ships with powerful capabilities (SQL agent, email sending, document upload + re-index) and
**no auth**, plaintext secret return, and permissive CORS. This skill is the how-to for closing
those gaps. It complements `pentesting-nexusai` (which *finds* the gaps) and `reviewing-nexusai`
(which checks the diff). It implements `improvements.md §1` / `issues.md` C2–C3, H1–H8.

## When to Use

- Adding authentication/authorization to `app.py` endpoints.
- Masking secrets in `GET /settings`.
- Restricting the SQL agent or the email tool.
- Fixing CORS or rate limiting.

## Threat Model (what an attacker can do today)

Unauthenticated, they can: read decrypted SMTP/DB creds via `GET /settings`; drive the SQL agent to
`DROP`/`DELETE` or read `user_settings`; send email to anyone once SMTP is set; upload a file with a
`../` path and trigger a re-index; and exfiltrate prompts via injection. Prompt text is **not** a
security boundary — only real controls count.

## Patterns

### Auth (do this first — everything else assumes an identity)
- Add a FastAPI dependency that validates an API key / bearer token sourced from `get_settings()`.
- Apply admin auth to `/settings`, `/upload`, `/documents`; require an authenticated identity for
  `/chat`. Use that identity (not client-supplied `user_id`) for rate limiting and history keys.

### Secret masking
- `GET /settings` returns `"***set***"` / `null`, never decrypted values. Decrypt only at point of
  use, server-side. Keep Fernet encryption on write (`utils/encryption.py`).

### SQL agent lockdown (`agents/db_agent.py`)
- Connect as a read-only DB user; restrict to an explicit table allow-list; exclude `user_settings`.
- Optionally parse generated SQL and reject DDL/DML. Set `verbose=False`.
- Return generic error messages — never `str(e)` to the user (log with `LOGGER.exception`).

### Upload sanitization (`app.py upload_document()`)
- `name = os.path.basename(file.filename)`; reject if it changed or contains separators.
- Validate extension ∈ {pdf, md, docx, csv}; enforce a max byte size; ensure the resolved path stays
  inside `docs_path`. This also de-risks the pickle/FAISS deserialization (H2).

### Email tool (`tools/email_tool.py`)
- Keep the draft→confirm→execute gate. Add a recipient domain allow-list, a send-rate cap, and an
  audit log entry per send.

### CORS & rate limiting
- Replace `allow_origins=["*"]` + `allow_credentials=True` with an explicit origin list from settings.
- Rate-limit on authenticated identity / source IP. Pick ONE mechanism — either register
  `rate_limit_middleware` or keep the inline `/chat` logic, not both.

## Invariants You MUST Preserve

- Agent return contract `{answer, source, confidence}`; ValidationAgent is the single exit point.
- All config flows through `get_settings()`; add new fields (auth keys, allowed origins, allowed
  email domains, size caps) there and mirror in `.env.example`.
- Graceful degradation when Redis/SMTP/keys are absent.
- Never store plaintext secrets; never commit `db/company.db` or `.env`.

## Verify

```bash
source venv/bin/activate
python -c "import app"
python -m uvicorn app:app --reload
# unauthenticated GET /settings must NOT return decrypted creds
# unauthenticated /upload, /documents, /settings must be rejected
```

Then run the `security-review` and `pentesting-nexusai` skills to confirm each gap is closed.

## Don'ts

- Don't rely on prompt instructions as a security control.
- Don't leak exception text, SQL, or stack traces to users.
- Don't widen CORS or disable auth "just for testing" in committed code.
