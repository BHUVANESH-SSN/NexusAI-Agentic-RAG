# RAGAS baselines

Snapshots of `run_ragas.py` output over the full `data/eval_dataset.json` (10 cases), for comparing
against after retrieval/prompt changes. Aggregate scores are recorded here; full per-sample JSON
lives alongside each dated file.

| Date | Faithfulness | Answer Relevancy | Context Precision | Context Recall | Notes |
|---|---|---|---|---|---|
| 2026-07-02 | 0.81 | 0.75 | 1.00 | 0.90 | First real baseline — `data/company_docs/` was populated with the 7 expected policy PDFs and the index rebuilt for this run. Judge: Groq (`openai/gpt-oss-120b`), `RunConfig(max_workers=1)`, `answer_relevancy.strictness=1` (Groq rejects `n>1`). One sample ("annual leave") returned the no-answer fallback despite perfect retrieval — likely a transient Groq failure in the corrective-RAG grading loop, not a retrieval defect; worth a spot re-run. |
