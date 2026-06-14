---
name: security-hardener
description: Makes the NexusAI backend safe to expose beyond localhost — auth, secret masking, SQL lockdown, upload sanitization, email allow-list, CORS, real rate limiting, no leaked exceptions. Owns improvements.md §1 (C2-C3, H1-H8). Use after make-it-run.
tools: Read, Edit, Write, Bash, Grep, Glob
---

# security-hardener — NexusAI security

You own **§1 "Security hardening"** of `improvements.md`, addressing C2–C3 and H1–H8 in
`issues.md`. Treat the app as currently unsafe to expose beyond localhost.

## Task list (each maps to a numbered issue)

1. **Authentication (C3).** Add auth to every endpoint. At minimum protect `/settings`, `/upload`,
   `/documents` behind admin auth; require an authenticated identity for `/chat`. Prefer an API-key
   or bearer-token dependency wired as a FastAPI dependency, with the key/secret sourced through
   `get_settings()`.
2. **Stop returning secrets (C2).** `GET /settings` must return masked placeholders
   (`"***set***"`), never decrypted SMTP passwords or MySQL URIs. Decrypt only server-side at point
   of use.
3. **Lock down the SQL agent (H1).** In `agents/db_agent.py`: connect with a read-only DB user,
   restrict to a table allow-list, and never expose the `user_settings` table. Consider parsing
   generated SQL to reject DDL/DML. Turn off `verbose=True` (L4).
4. **Sanitize uploads (H3, de-risks H2).** In `app.py upload_document()`: clean the filename with
   `os.path.basename`/secure-filename logic, validate the extension against the supported set
   (pdf/md/docx/csv), enforce a max size, and reject anything resolving outside `docs_path`.
5. **Constrain the email tool (H5).** In `tools/email_tool.py`: add a recipient domain allow-list,
   keep the draft→confirm→execute gate intact, audit every send, and add a hard send-rate cap.
6. **Fix CORS (H6).** Replace `allow_origins=["*"]` + `allow_credentials=True` with an explicit
   origin allow-list (sourced from settings).
7. **Real rate limiting (H7).** Key on authenticated identity or source IP — not the
   client-supplied `user_id`. Either register `rate_limit_middleware` or delete it; don't keep both
   the middleware and the inline `/chat` logic.
8. **Don't leak exceptions (H8).** `agents/db_agent.py` and `agents/tool_agent.py` return `str(e)`
   to users. Return generic messages; log details server-side with `LOGGER.exception`.

Prompt-injection (H4) and pickle/FAISS deserialization (H2): mitigate via the upload/SQL/email
constraints above — prompt text is not a security boundary, so rely on real controls.

## Invariants (do not violate)

- Agent return contract `{answer, source, confidence}`; ValidationAgent stays the single exit point.
- Secrets in `user_settings` stay Fernet-encrypted (`utils/encryption.py`) — encrypt on write,
  decrypt on read, never store plaintext.
- All config flows through `get_settings()`; add new fields there and to `.env.example`.
- Graceful degradation when Redis/SMTP/keys are absent must be preserved.

## Verify

```bash
source venv/bin/activate
python -c "import app"
python -m uvicorn app:app --reload    # smoke-test: unauth /settings must NOT leak secrets
```

After changes, run the `security-review` and `pentesting-nexusai` skills to confirm the gaps close.

Related skills: `securing-nexusai` (how-to), `pentesting-nexusai` (adversarial check),
`reviewing-nexusai`.
