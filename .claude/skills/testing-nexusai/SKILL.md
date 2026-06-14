---
name: testing-nexusai
description: Build the pytest suite and CI gate for the NexusAI FastAPI + LangChain RAG backend — agent return-contract tests, supervisor routing, encryption round-trip, mocked /chat end-to-end, and an import guard. Use when adding tests (improvements.md §4 / issue M8) or wiring CI. For RAG quality scoring use evaluating-with-ragas instead.
version: 1.0.0
---

# Testing NexusAI

## Overview

NexusAI has **no automated test suite** (issue M8); `evaluate.py` is a live-LLM quality harness, not
unit tests. A non-importable file (C1) shipped undetected because nothing guarded it. This skill is
the how-to for a `pytest` suite + CI gate that runs **without** API keys, built indices, or Redis.
It implements `improvements.md §4` testing items.

## When to Use

- Adding `pytest` tests for agents, routing, encryption, retriever formatting, or `/chat`.
- Wiring the import guard / test gate into CI.

## What to Test (and how to isolate it)

The boundaries to mock are: the LLM (`llm/factory.py::get_chat_model`/`get_llm_with_failover`),
embeddings/reranker, Redis, and SMTP. Everything else is fair game to test directly.

1. **Import guard (cheap, catches C1-class bugs).**
   `python -m py_compile ...` + `python -c "import app"` as the first CI step.
2. **Agent return contract.** For each agent in `agents/`, assert `run()` returns a `dict` with at
   least `answer` and `source` (ideally `confidence`). Mock the LLM so it's deterministic. This is
   the project's core invariant — test it for every agent including new ones.
3. **Supervisor routing (`router/supervisor.py`).** With a mocked classifier LLM, assert messages map
   to exactly one of `retriever | db | tool | chat`, and that any failure defaults to `chat`.
4. **Encryption round-trip (`utils/encryption.py`).** With a test `MASTER_ENCRYPTION_KEY`, assert
   `decrypt(encrypt(x)) == x` and that a missing key fails clearly.
5. **Retriever output formatting.** With a fake vector store / BM25 / reranker, assert
   `CompanyRetriever.retrieve` returns the structured `{answer, source, confidence}`-compatible shape
   and respects `settings.retriever_top_k`.
6. **Mocked `/chat` end-to-end.** Use FastAPI `TestClient` with the chatbot's LLM/Redis dependencies
   mocked; assert the response matches the `ChatResponse` model and that rate limiting / input caps
   behave. Patch `app.state.chatbot` or its collaborators.

## Conventions

- Layout: `tests/` with `conftest.py` holding shared fixtures (mock LLM, fake retriever, fixed
  Fernet key, `monkeypatch` of `get_settings`). Name files `test_<module>.py`.
- Use `pytest` + `pytest-mock`/`unittest.mock` and `fastapi.testclient.TestClient`. Add them (test
  extras) to `requirements.txt` or a `requirements-dev.txt`.
- Override config via `get_settings`'s cache: clear it (`get_settings.cache_clear()`) after
  `monkeypatch.setenv`, since it's `lru_cache`d.
- Tests must be hermetic — no network, no real Redis, no real model downloads, no live keys.

## Test-design help

For boundary values, equivalence partitions, and error-guessing on validation logic (input caps,
file-type/size checks, allow-lists), use the `art-of-testing` skill. For deciding what's worth
testing vs implementation detail and mock-vs-stub choices, use `unit-testing-khorikov`.

## CI Gate

A minimal `.github/workflows/ci.yml`: install deps → `python -c "import app"` → `pytest -q`. Keep
`evaluate.py` and RAGAS **out** of this gate (they need live LLMs/indices — that's
`evaluating-with-ragas`).

## Verify

```bash
source venv/bin/activate
pip install -r requirements.txt        # incl. pytest
pytest -q                              # all green, no network/keys/Redis needed
python -c "import app"
```

## Don'ts

- Don't call live LLMs, Redis, or download models in unit tests.
- Don't assert on exact LLM wording — assert on structure/contract and routing decisions.
- Don't put the RAGAS/`evaluate.py` quality harness in the unit-test CI gate.
