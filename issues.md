# NexusAI Redesign Blueprint — LangGraph RAG with Observability & RAGAS Eval

---

## Table of contents

1. [Audit — keep vs replace](#1-audit--keep-vs-replace)
2. [New tech stack](#2-new-tech-stack)
3. [LangGraph design](#3-langgraph-design)
4. [RAG architecture](#4-rag-architecture)
5. [Observability](#5-observability)
6. [RAGAS evaluation pipeline](#6-ragas-evaluation-pipeline)
7. [Build plan](#7-build-plan)

---

## 1. Audit — keep vs replace

### Replace

| Issue | Problem | Fix |
|---|---|---|
| Flat supervisor routing | Single LLM deciding `retriever\|db\|tool\|chat` with no state. Race conditions with history load, no retry logic, no fallback if routing fails. | Replace with a proper LangGraph `StateGraph` with typed state, conditional edges, and fallback nodes. |
| O(n) semantic cache scan | Redis cosine similarity over all keys is O(n) — kills p99 latency at scale. | Replace with a proper vector store (pgvector or Qdrant) with approximate nearest-neighbour search. Keep Redis for session/history only. |
| `retriever_top_k` ignored + naive chunking | `top_k` is hardcoded somewhere and chunking is fixed-size with no sentence boundary awareness. | Implement semantic chunking (sentence-transformers), configurable `top_k`, and a proper reranking pipeline. |

### Fix immediately (30-min tasks)

- **M5 delete bug** — `delete` globs `*.pdf` only, misses `.docx`, `.txt`, etc. Fix the glob to match all allowed extensions.
- **M10 hardcoded frontend URL** — `http://127.0.0.1:8000` is in 3+ frontend files. Replace with `NEXT_PUBLIC_API_URL` env var.
- **`.zshenv` crash** — `.zshenv` tries to `source ~/.cargo/env` (Rust toolchain missing), so no shell commands run. Delete that line from `.zshenv` — **do this before anything else or you can't start the app.**

### Keep

| What | Why |
|---|---|
| Hybrid RAG (FAISS + BM25 + CrossEncoder) | Hybrid dense+sparse retrieval is the right call. CrossEncoder reranking is good. Keep this pattern — just fix the `top_k` bug and integrate it properly into the LangGraph retriever node. |
| Security fixes (C2, C3, H1, H3, H5–H8) | The ~80% security hardening already done is solid. Don't throw it away in the redesign — port these guards into the new FastAPI layer. |

---

## 2. New tech stack

| Layer | Old | New |
|---|---|---|
| Agent framework | Custom supervisor + if/else routing | LangGraph `StateGraph` (typed, checkpointed) |
| LLM provider | Single LLM, no fallback | Claude 3.5 Sonnet primary, Haiku fallback via LiteLLM |
| Embeddings | MiniLM (local HuggingFace) | Keep MiniLM or upgrade to `bge-m3` for multilingual |
| Vector store | FAISS (in-memory, no persistence) | pgvector (Postgres) or Qdrant for persistence + ANN |
| Semantic cache | Redis cosine scan (O(n)) | GPTCache or Qdrant-backed cache with ANN lookup |
| Conversation history | Redis 1h TTL + in-memory fallback | LangGraph Postgres checkpointer — replaces Redis for conv. state |
| Database agent | Raw SQL agent (DDL allowed) | LangGraph db node, read-only URI, Vanna.ai for NL→SQL |
| Observability | None | LangSmith traces + Prometheus/Grafana + OpenTelemetry |
| RAG evaluation | None | RAGAS pipeline (faithfulness, context recall, answer relevancy) |
| Chunking | Fixed-size naive chunking | Semantic chunking (sentence-transformers + overlap) |
| Frontend | Next.js 14, hardcoded `127.0.0.1:8000` | Next.js 14 + env-based API URL + SSE streaming |
| Testing | None | pytest + LangSmith dataset evals + GitHub Actions CI |

---

## 3. LangGraph design

### Typed state schema

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    query: str
    retrieved_docs: list[Document]
    answer: str
    sources: list[str]
    confidence: float
    route: str          # "retriever" | "db" | "tool" | "chat"
    tenant_id: str
    trace_id: str
```

### Graph nodes

| Node | Role |
|---|---|
| `cache_check` | ANN similarity lookup in Qdrant/pgvector. Hit → skip graph, return cached. Miss → continue. |
| `supervisor` | LLM with structured output (Pydantic `RouteDecision`). Routes to retriever / db / tool / chat based on query intent. |
| `retriever_node` | Hybrid FAISS+BM25 fetch → CrossEncoder rerank → `top_k` from state. Returns docs + scores into state. |
| `db_node` | Read-only SQL agent. NL→SQL via Vanna.ai. Table allowlist enforced. Returns structured result into state. |
| `tool_node` | LangGraph ReAct loop for email/calendar tools. Domain allowlist and rate cap enforced inside node. |
| `grade_docs` | LLM grades retrieved docs for relevance. Low relevance → `query_rewrite` loop (max 2 retries). |
| `query_rewrite` | Rewrites query using HyDE or step-back prompting. Feeds back into `retriever_node`. Max 2 iterations. |
| `generate` | Final answer generation with citations. Streams tokens via SSE. Writes answer + sources to state. |
| `validate` | Hallucination check — does the answer contradict source docs? Normalises to `ChatResponse` schema. |
| `persist` | Writes to Postgres checkpointer (conv. history) + updates semantic cache + logs run to LangSmith. |

### Graph flow (simplified)

```
POST /chat
  → cache_check
      → [HIT]  return cached answer
      → [MISS] supervisor
                 → retriever_node → grade_docs
                                      → [OK]     generate → validate → persist
                                      → [POOR]   query_rewrite → retriever_node (max 2×)
                 → db_node       → generate → validate → persist
                 → tool_node     → generate → validate → persist
                 → chat_agent    → generate → validate → persist
```

---

## 4. RAG architecture

### Ingestion pipeline (offline)

**Step 1 — Document loading**
LangChain loaders for PDF, DOCX, TXT, HTML. Attach metadata: `source`, `page`, `date`, `tenant_id`.

**Step 2 — Semantic chunking**
Use `sentence-transformers` semantic chunker. Target 256–512 tokens, 20% overlap. Never split mid-sentence.

**Step 3 — Embed + store**
`bge-m3` or MiniLM embeddings → pgvector or Qdrant. BM25 index built in parallel (sparse vectors).

**Step 4 — Parent-child chunking**
Store small child chunks (128 tokens) for precise retrieval, return larger parent chunk (512 tokens) as context. Significantly improves faithfulness.

### Retrieval pipeline (online)

**Step 1 — Query expansion**
HyDE: generate a hypothetical document, embed it. Multi-query: 3 rewordings → retrieve for each. Fuse results.

**Step 2 — Hybrid fetch**
Dense retrieval (pgvector/Qdrant ANN, top 20) + BM25 sparse (top 20). Reciprocal Rank Fusion to merge.

**Step 3 — CrossEncoder rerank**
`ms-marco-MiniLM-L-6-v2` reranker on the merged top 40. Take `top_k` (configurable, default 5). Filter by score threshold.

**Step 4 — Relevance grading**
LLM grades each doc as relevant/irrelevant. If fewer than 3 docs pass → trigger `query_rewrite` node (max 2 loops).

---

## 5. Observability

### Stack

| Layer | Tool |
|---|---|
| Trace every LLM run | LangSmith |
| Metrics + alerting | Prometheus |
| Dashboards | Grafana |
| Distributed tracing | OpenTelemetry |

### LangSmith tracing

Wrap every LangGraph node with `@traceable` or use the built-in LangGraph ↔ LangSmith integration:

```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=<your-key>
export LANGCHAIN_PROJECT=nexusai-prod
```

Each run surfaces: node timings, LLM inputs/outputs, token counts, retrieved docs, reranker scores. Use `run.feedback()` to log RAGAS scores back onto traces for correlation.

### Prometheus metrics to expose

```
rag_request_total{route, status}
rag_latency_seconds{node}            # histogram
rag_cache_hits_total{type}           # semantic | exact
rag_retriever_docs_returned{k}
rag_llm_tokens_total{model, type}    # prompt | completion
rag_ragas_faithfulness_score         # gauge, updated per batch
rag_rerank_score_avg                 # gauge
```

### OpenTelemetry

Use `opentelemetry-sdk` + `opentelemetry-instrumentation-fastapi`. Each `POST /chat` gets a `trace_id` propagated through all LangGraph nodes. Correlates with LangSmith run ID and Postgres logs. Helps debug multi-tenant latency spikes.

### Grafana dashboards to build

1. Request rate + p50/p95/p99 latency per route
2. Cache hit rate over time (target ≥ 30%)
3. RAGAS metric trends (faithfulness, context recall, answer relevancy)
4. LLM token cost per hour + per tenant
5. Retriever score distribution (detect degradation early)

---

## 6. RAGAS evaluation pipeline

### The 4 metrics

| Metric | What it measures | Target |
|---|---|---|
| **Faithfulness** | Does the answer contradict the retrieved docs? Catches hallucinations. | ≥ 0.85 |
| **Context recall** | Did retrieval surface the docs needed to answer? Low score = retrieval bug. | ≥ 0.75 |
| **Answer relevancy** | Is the answer on-topic? Catches when the LLM rambles. | ≥ 0.80 |
| **Context precision** | Are the retrieved docs actually used in the answer? | ≥ 0.75 |

### Pipeline architecture

**Step 1 — Golden dataset**
Build 100–200 Q&A pairs from your company docs. Store in a LangSmith dataset. Each row: `question`, `ground_truth_answer`, `ground_truth_contexts`.

**Step 2 — Nightly eval run**
GitHub Actions cron or APScheduler: run the full RAG pipeline on the golden set, collect `{answer, contexts}` for each question.

**Step 3 — Score with RAGAS**

```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
    context_precision,
)
from datasets import Dataset

data = Dataset.from_list(run_pipeline_on_golden_set())

results = evaluate(
    data,
    metrics=[faithfulness, answer_relevancy, context_recall, context_precision],
)

print(results.to_pandas())
```

**Step 4 — Regression gate**
If `faithfulness` drops > 0.05 vs last run → Slack alert + block deployment. Wire into CI as a hard quality gate.

---

## 7. Build plan

### Phase 1 — Hotfixes + foundation (Week 1) `⚠️ do first`

- Fix `.zshenv` Cargo crash (delete `source ~/.cargo/env` line)
- Fix M5 delete bug — glob all allowed extensions, not `*.pdf` only
- Fix M10 — replace hardcoded `http://127.0.0.1:8000` with `NEXT_PUBLIC_API_URL` env var
- Port all existing security fixes (C2, C3, H1, H3, H5–H8) into the new codebase
- Add `/health` endpoint
- Set up `pytest` skeleton + GitHub Actions CI

### Phase 2 — LangGraph core + RAG (Weeks 2–4)

- Define `AgentState` TypedDict
- Build all graph nodes: `supervisor`, `retriever_node`, `db_node`, `tool_node`, `chat_agent`, `grade_docs`, `query_rewrite`, `generate`, `validate`, `persist`
- Swap FAISS → pgvector or Qdrant
- Implement semantic chunking + parent-child chunking
- Add HyDE query expansion
- Wire SSE streaming to Next.js frontend

### Phase 3 — Observability (Weeks 4–5)

- LangSmith tracing on every node (`LANGCHAIN_TRACING_V2=true`)
- Prometheus `/metrics` endpoint + 7 custom metrics
- Grafana dashboards: latency, cache hit rate, RAGAS trends
- OpenTelemetry trace propagation (trace_id through all nodes)
- Replace Redis semantic cache with Qdrant ANN cache

### Phase 4 — RAGAS eval + deployment (Weeks 5–6)

- Build 100-row golden Q&A dataset from company docs
- Nightly RAGAS eval cron job
- LangSmith regression gate in GitHub Actions CI
- Docker Compose for full stack: FastAPI + Postgres + Qdrant + Redis + Grafana
- All secrets via env vars, nothing hardcoded
- Write `RUNBOOK.md` and architecture docs

---

## Quick reference — directory structure (target)

```
nexusai/
├── backend/
│   ├── agents/
│   │   ├── state.py          # AgentState TypedDict
│   │   ├── supervisor.py     # routing node
│   │   ├── retriever.py      # hybrid RAG node
│   │   ├── db_agent.py       # SQL node
│   │   ├── tool_agent.py     # ReAct tool node
│   │   ├── grader.py         # relevance grader
│   │   ├── rewriter.py       # query rewrite node
│   │   ├── generate.py       # answer generation
│   │   └── validate.py       # hallucination check
│   ├── graph.py              # StateGraph assembly + edges
│   ├── ingestion/
│   │   ├── chunker.py        # semantic chunking
│   │   └── indexer.py        # embed + store to pgvector/Qdrant
│   ├── cache/
│   │   └── semantic_cache.py # ANN-backed cache
│   ├── observability/
│   │   ├── metrics.py        # Prometheus counters/histograms
│   │   └── tracing.py        # OpenTelemetry setup
│   ├── eval/
│   │   ├── golden_dataset.json
│   │   └── ragas_eval.py     # nightly eval script
│   ├── app.py                # FastAPI entrypoint
│   └── config.py             # pydantic-settings, no hardcoded secrets
├── frontend/
│   └── .env.local            # NEXT_PUBLIC_API_URL=...
├── docker-compose.yml
├── .github/workflows/
│   ├── ci.yml                # pytest + lint
│   └── ragas_eval.yml        # nightly quality gate
└── RUNBOOK.md
```