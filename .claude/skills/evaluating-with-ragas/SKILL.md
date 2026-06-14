---
name: evaluating-with-ragas
description: Evaluate the NexusAI RAG pipeline with the RAGAS framework — faithfulness, answer relevancy, context precision/recall. Use when measuring retrieval/answer quality, adding RAGAS to the project, or comparing RAG changes against a baseline.
version: 1.0.0
---

# Evaluating NexusAI with RAGAS

## Overview

The repo ships a custom LLM-as-judge harness (`evaluate.py` + `evaluation/evaluator.py`) that scores
relevance/faithfulness/clarity. This skill adds **RAGAS** (https://docs.ragas.io) — a standard RAG
metric suite — on top of the same dataset and the project's real retriever/agent.

RAGAS core metrics for this project:
- **faithfulness** — is the answer grounded in retrieved contexts (anti-hallucination)?
- **answer_relevancy** — does the answer address the question?
- **context_precision** — are the retrieved chunks relevant / well-ranked?
- **context_recall** — did retrieval surface what's needed (requires `ground_truth`)?

## Inputs

RAGAS needs per-sample: `question`, `answer`, `contexts` (list of retrieved chunk texts), and for
recall, `ground_truth`. Source questions from `data/eval_dataset.json` (`test_cases[].question`,
`expected_source`). Add a `ground_truth` field to each test case to enable context_recall — without
it, skip that metric.

The contexts come from the project retriever: `CompanyRetriever().retrieve(question)` →
`doc.page_content` for each doc. The answer comes from `RetrieverAgent.run(question, "No history")`.

## Setup

```bash
source venv/bin/activate
pip install ragas datasets            # not yet in requirements.txt — add if you keep this
python -m rag.ingestion               # ensure FAISS + BM25 indices exist
redis-cli ping                        # optional; retriever works without Redis
```

RAGAS needs an LLM + embeddings. **Reuse the project's** `llm.factory.get_chat_model()` and
`get_embeddings()` via `LangchainLLMWrapper` / `LangchainEmbeddingsWrapper` so eval uses the same
models as production. Note: RAGAS judging with Groq Llama can be rate-limited — set
`LLM_PROVIDER=openai` (or anthropic) for the judge if you hit limits.

## Run

A ready-to-use runner is provided:

```bash
python .claude/skills/evaluating-with-ragas/scripts/run_ragas.py
# options: --limit N   --no-recall   --out results.json
```

It builds the eval dataset by running the real retriever + agent, then computes RAGAS metrics and
prints per-sample and aggregate scores. See [scripts/run_ragas.py](scripts/run_ragas.py).

## Interpreting Results

- Scores are 0–1; higher is better. Investigate any metric < ~0.7.
- **Low faithfulness** → agent hallucinating; tighten the `RetrieverAgent` grounding prompt.
- **Low context_precision/recall** → retrieval problem; tune `RETRIEVER_TOP_K`, the rerank step,
  the 0.82 semantic-chunking threshold, or query rewriting in `rag/retriever.py`.
- **Low answer_relevancy** → answer drifts; check prompt and query rewriting.
- Treat the first run as a **baseline**; re-run after RAG changes and compare. Keep `--out` JSONs.

## Caveats

- RAGAS makes many LLM calls — it's slow and costs tokens/quota. Use `--limit` while iterating.
- Results vary run-to-run (LLM judges); compare deltas, not single absolute numbers.
- This evaluates the **retriever path** only. The `db`/`tool`/`chat` routes are out of RAGAS scope.
- Keep RAGAS eval separate from the existing `evaluate.py`; don't replace it unless asked.
</content>
