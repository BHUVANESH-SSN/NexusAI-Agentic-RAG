import json
import logging
from pathlib import Path
from statistics import mean

from llm.factory import get_chat_model, configure_logging
from rag.retriever import CompanyRetriever, format_documents
from agents.retriever_agent import RetrieverAgent
from evaluation.evaluator import RAGEvaluator, calculate_retrieval_accuracy

# Setup logging
configure_logging()
LOGGER = logging.getLogger("RAG_Eval")

def run_evaluation():
    # 1. Initialize core components
    print("\n--- Starting RAG Evaluation ---")
    llm = get_chat_model()
    retriever = CompanyRetriever()
    agent = RetrieverAgent(llm=llm, retriever=retriever)
    evaluator = RAGEvaluator(llm=llm)

    # 2. Load dataset
    dataset_path = Path("data/eval_dataset.json")
    if not dataset_path.exists():
        print(f"Dataset not found at {dataset_path}")
        return

    with open(dataset_path, "r") as f:
        data = json.load(f)
        test_cases = data.get("test_cases", [])

    results = []

    # 3. Iterate through test cases
    for case in test_cases:
        qid = case["id"]
        question = case["question"]
        expected_source = case.get("expected_source")
        
        print(f"\n[{qid}] Evaluating: {question}")
        
        try:
            # A. Run Chatbot
            # We get documents manually to measure retrieval accuracy separately
            documents = retriever.retrieve(question)
            context = format_documents(documents)
            
            # Run the agent to get the final answer
            # (In production, the agent calls retriever too, but here we capture context)
            response = agent.run(question, "No history")
            answer = response.get("answer", "")
            
            # B. Score result
            scores = evaluator.score(question, context, answer)
            retrieval_acc = calculate_retrieval_accuracy(documents, expected_source)
            
            case_result = {
                "id": qid,
                "question": question,
                "answer": answer,
                "scores": scores,
                "retrieval_accuracy": retrieval_acc
            }
            results.append(case_result)
            
            print(f"   Rel: {scores.relevance:.2f} | Faith: {scores.faithfulness:.2f} | Clarity: {scores.clarity:.2f} | Retrieve: {retrieval_acc:.2f}")

        except Exception as e:
            print(f"   Error evaluating case {qid}: {e}")

    # 4. Aggregate and Print Report
    print("\n" + "="*50)
    print("FINAL EVALUATION REPORT")
    print("="*50)
    
    avg_rel = mean([r["scores"].relevance for r in results])
    avg_faith = mean([r["scores"].faithfulness for r in results])
    avg_clarity = mean([r["scores"].clarity for r in results])
    avg_retrieval = mean([r["retrieval_accuracy"] for r in results])
    
    print(f"Overall Average Scores:")
    print(f" - Relevance:         {avg_rel:.2%}")
    print(f" - Faithfulness:      {avg_faith:.2%}")
    print(f" - Clarity:           {avg_clarity:.2%}")
    print(f" - Retrieval Accuracy: {avg_retrieval:.2%}")
    
    # 5. Highlight Bad Cases (Score < 0.7)
    print("\n--- Cases Requiring Improvement ---")
    bad_exists = False
    for r in results:
        s = r["scores"]
        if min(s.relevance, s.faithfulness, s.clarity) < 0.7 or r["retrieval_accuracy"] < 1.0:
            bad_exists = True
            print(f"\n[ID {r['id']}] {r['question']}")
            print(f"   Reasoning: {s.critique}")
            if r["retrieval_accuracy"] < 1.0:
                print(f"   * FAILED to retrieve expected source: {test_cases[r['id']-1].get('expected_source')}")

    if not bad_exists:
        print("None! All cases passed with high scores.")

if __name__ == "__main__":
    run_evaluation()
