#!/usr/bin/env python3
"""Evaluate the NexusAI retriever pipeline with RAGAS.

Builds an evaluation dataset by running the project's real CompanyRetriever + RetrieverAgent
over the questions in data/eval_dataset.json, then scores it with RAGAS using the same LLM /
embeddings as production (via llm.factory).

Usage:
    python .claude/skills/evaluating-with-ragas/scripts/run_ragas.py [--limit N] [--no-recall] [--out FILE]

Requires:  pip install ragas datasets   and   built FAISS/BM25 indices (python -m rag.ingestion)
Run from the repo root with the venv activated.
"""
import argparse
import json
import sys
from pathlib import Path

# Ensure repo root is importable when run from anywhere.
REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))


def build_samples(limit=None, with_recall=True):
    from rag.retriever import CompanyRetriever
    from agents.retriever_agent import RetrieverAgent

    dataset_path = REPO_ROOT / "data" / "eval_dataset.json"
    test_cases = json.loads(dataset_path.read_text()).get("test_cases", [])
    if limit:
        test_cases = test_cases[:limit]

    retriever = CompanyRetriever()
    agent = RetrieverAgent(retriever)

    samples = []
    for case in test_cases:
        q = case["question"]
        print(f"[run] {case.get('id', '?')}: {q}")
        docs = retriever.retrieve(q, history="No history")
        contexts = [d.page_content for d in docs] or ["No context retrieved."]
        answer = agent.run(q, "No history").get("answer", "")

        sample = {"question": q, "answer": answer, "contexts": contexts}
        if with_recall:
            # context_recall needs a reference answer. This dataset stores it as "expected_answer";
            # prefer an explicit "ground_truth" if present, else fall back to expected_source.
            sample["ground_truth"] = (
                case.get("ground_truth")
                or case.get("expected_answer")
                or case.get("expected_source", "")
            )
        samples.append(sample)
    return samples


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="Only evaluate the first N questions.")
    ap.add_argument("--no-recall", action="store_true", help="Skip context_recall (no ground truth).")
    ap.add_argument("--out", default=None, help="Write full results JSON to this path.")
    args = ap.parse_args()

    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
        from ragas.llms import LangchainLLMWrapper
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.run_config import RunConfig
    except ImportError:
        sys.exit("Missing deps. Run: pip install ragas datasets")

    from llm.factory import get_chat_model, get_embeddings, get_settings, configure_logging
    configure_logging()

    settings = get_settings()
    if settings.langsmith_api_key:
        import os as _os
        _os.environ["LANGCHAIN_TRACING_V2"] = "true"
        _os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        _os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
        print(f"[langsmith] tracing enabled (project: {settings.langchain_project})")

    with_recall = not args.no_recall
    samples = build_samples(limit=args.limit, with_recall=with_recall)
    if not samples:
        sys.exit("No samples built — check data/eval_dataset.json and that indices are built.")

    ds = Dataset.from_list(samples)

    # answer_relevancy defaults to strictness=3, which asks the judge LLM for 3
    # generations (n=3) per call. Groq's API hard-rejects n>1 ("number must be at
    # most 1"), which silently zeroes the metric under ragas's default
    # raise_exceptions=False. Force single-generation scoring instead.
    answer_relevancy.strictness = 1

    metrics = [faithfulness, answer_relevancy, context_precision]
    if with_recall:
        metrics.append(context_recall)

    judge_llm = LangchainLLMWrapper(get_chat_model())
    judge_emb = LangchainEmbeddingsWrapper(get_embeddings())

    # Groq's free tier rate-limits hard; ragas defaults to 16 concurrent judge calls,
    # which triggers cascading 429s/connection errors that get masked as 0-scores.
    # Fully serialize judge calls so retries have room to actually succeed.
    run_config = RunConfig(max_workers=1, timeout=300, max_retries=5, max_wait=30)

    print(f"\n[ragas] scoring {len(samples)} samples on {[m.name for m in metrics]} ...")
    result = evaluate(ds, metrics=metrics, llm=judge_llm, embeddings=judge_emb, run_config=run_config)

    print("\n" + "=" * 50)
    print("RAGAS RESULTS (aggregate)")
    print("=" * 50)
    print(result)

    if args.out:
        df = result.to_pandas()
        Path(args.out).write_text(df.to_json(orient="records", indent=2))
        print(f"\nFull per-sample results written to {args.out}")


if __name__ == "__main__":
    main()
