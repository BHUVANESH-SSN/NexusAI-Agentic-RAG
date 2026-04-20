import json
import logging
from typing import Any, List, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

LOGGER = logging.getLogger(__name__)

# --- Evaluation Output Schema ---

class EvalScores(BaseModel):
    relevance: float = Field(description="Score from 0.0 to 1.0 based on how well the answer addresses the question.")
    faithfulness: float = Field(description="Score from 0.0 to 1.0 based on how well the answer is grounded in the retrieved context.")
    clarity: float = Field(description="Score from 0.0 to 1.0 based on the readability and structure of the answer.")
    critique: str = Field(description="Detailed explanation for the scores, highlighting any issues.")

# --- Evaluator Class ---

_EVAL_PROMPT = """\
You are an expert AI quality evaluator for a RAG-based chatbot.
Your task is to grade the quality of a generated answer based on the original question and the retrieved context.

METRICS:
1. Relevance (0.0 - 1.0): Does the answer directly address the question? Is it helpful?
2. Faithfulness (0.0 - 1.0): Is every claim in the answer supported by the provided context? Deduct points for hallucinations or info not in context.
3. Clarity (0.0 - 1.0): Is the answer professional, well-structured, and easy to read? Is it concise (3-5 lines)?

{format_instructions}

INPUTS:
- Question: {question}
- Retrieved Context: {context}
- Generated Answer: {answer}
"""

class RAGEvaluator:
    def __init__(self, llm) -> None:
        self.parser = PydanticOutputParser(pydantic_object=EvalScores)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", _EVAL_PROMPT)
        ]).partial(format_instructions=self.parser.get_format_instructions())
        self.chain = self.prompt | llm

    def score(self, question: str, context: str, answer: str) -> EvalScores:
        """Runs LLM-based evaluation for a single Q/A pair."""
        try:
            response = self.chain.invoke({
                "question": question,
                "context": context,
                "answer": answer
            })
            # Handle both AIMessage and raw string
            content = response.content if hasattr(response, 'content') else str(response)
            return self.parser.parse(content)
        except Exception as e:
            LOGGER.error("Evaluation scoring failed: %s", e)
            return EvalScores(relevance=0.0, faithfulness=0.0, clarity=0.0, critique=f"Error: {str(e)}")

def calculate_retrieval_accuracy(retrieved_docs: List[Any], expected_source: Optional[str]) -> float:
    """Calculates if the expected source file is present in the retrieved chunks."""
    if not expected_source or expected_source.lower() == "none":
        return 1.0 # If no source is expected, it's accurate by default
        
    for doc in retrieved_docs:
        src = doc.metadata.get("source", "").lower()
        if expected_source.lower() in src:
            return 1.0
            
    return 0.0
