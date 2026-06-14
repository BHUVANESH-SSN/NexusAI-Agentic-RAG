---
name: backend-correctness
description: Fixes correctness & configuration bugs in NexusAI — honor configured settings, real LLM failover, multi-format delete, fail-fast encryption key, better chunking. Owns improvements.md §2 (M3-M7). Use after security-hardener.
tools: Read, Edit, Write, Bash, Grep, Glob
---

# backend-correctness — NexusAI correctness & config

You own **§2 "Correctness & configuration"** of `improvements.md` (issues M3–M7). These are bugs
where the code silently ignores config or behaves differently than its name promises.

## Task list

1. **Honor configured settings (M3).** `rag/retriever.py` hardcodes `k=10` and `candidates[:3]`;
   use `settings.retriever_top_k`. The semantic chunker in `rag/ingestion.py` never applies
   `chunk_overlap`; apply it (or remove the unused setting). Changing the env var must take effect.
2. **Real failover (M4).** `llm/factory.py::get_llm_with_failover()` just returns one model. Either
   implement failover across `FAILOVER_PROVIDERS` (try each in order, catch and fall through) or
   rename it to `get_llm()` so it stops promising behavior it lacks. Prefer implementing it.
3. **Multi-format delete (M5).** `app.py delete_document()` and `clear_all_documents()` only glob
   `*.pdf` to decide if the KB is empty and to unlink files. Ingestion supports pdf/md/docx/csv —
   glob all supported extensions so deleting the last PDF doesn't wrongly wipe the FAISS index or
   orphan other files.
4. **Fail-fast encryption key (M7).** `utils/encryption.py` raises only on first use. Validate
   `MASTER_ENCRYPTION_KEY` at startup (FastAPI `lifespan`) with a clear message, and document
   generating one via `Fernet.generate_key()` in `.env.example`/README.
5. **Better chunking (M6).** Replace the naive `.`-split in `rag/ingestion.py split_documents()`
   (breaks on decimals, `U.S.`, `e.g.`, filenames) with a real sentence splitter (nltk/spacy) or
   `RecursiveCharacterTextSplitter` as a fallback, preserving the semantic-similarity chunk boundary
   logic (cosine < 0.82).

## Invariants (do not violate)

- All config flows through `get_settings()` — never `os.getenv` elsewhere; keep the dataclass frozen
  and `lru_cache`d. Mirror new fields in `.env.example`.
- Don't introduce blocking model loads at import time — keep `get_embeddings`/`get_reranker` lazy.
- Agent return contract `{answer, source, confidence}` unchanged; ValidationAgent stays last.
- If you touch retrieval/chunking, rebuild indices: `python -m rag.ingestion`.

## Verify

```bash
source venv/bin/activate
python -c "import app"
python -m rag.ingestion            # if chunking/retrieval changed
python evaluate.py                 # confirm retrieval quality didn't regress
```

Use the `evaluating-with-ragas` skill to compare RAG quality before/after chunking changes.

Related skills: `refactoring-nexusai`, `evaluating-with-ragas`, `reviewing-nexusai`.
