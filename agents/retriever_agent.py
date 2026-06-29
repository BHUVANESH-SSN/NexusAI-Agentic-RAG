import logging
from typing import TypedDict, List

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END

from llm.factory import get_llm_with_failover, get_settings
from rag.retriever import CompanyRetriever, format_documents

LOGGER = logging.getLogger(__name__)

_GRADE_PROMPT = ChatPromptTemplate.from_template("""\
Grade whether this document is relevant to the question.
Answer with ONLY "yes" or "no".

Question: {question}
Document: {document}""")

_REWRITE_PROMPT = ChatPromptTemplate.from_template("""\
The retrieved documents were not relevant enough to answer the question.
Rewrite the question to be more specific and search-friendly.
Output ONLY the rewritten question, nothing else.

Original question: {question}""")

_ANSWER_PROMPT = ChatPromptTemplate.from_template("""\
You are a helpful enterprise AI assistant. Answer the question using ONLY the provided context.
If the context doesn't contain the answer, say exactly:
"The document does not provide details on that topic."

Context:
{context}

Question: {question}

Answer:""")


class RAGState(TypedDict):
    query: str
    history: str
    documents: List[Document]
    relevant_docs: List[Document]
    answer: str
    source: str
    confidence: str
    iterations: int


class RetrieverAgent:
    def __init__(self, retriever: CompanyRetriever) -> None:
        self.retriever = retriever
        llm = get_llm_with_failover()
        top_k = get_settings().retriever_top_k

        grader = _GRADE_PROMPT | llm | StrOutputParser()
        rewriter = _REWRITE_PROMPT | llm | StrOutputParser()
        answerer = _ANSWER_PROMPT | llm | StrOutputParser()

        def retrieve_node(state: RAGState) -> RAGState:
            docs = self.retriever.retrieve(state["query"], state["history"])
            return {**state, "documents": docs, "iterations": state["iterations"] + 1}

        def grade_node(state: RAGState) -> RAGState:
            relevant = []
            for doc in state["documents"]:
                try:
                    verdict = grader.invoke({
                        "question": state["query"],
                        "document": doc.page_content[:800],
                    }).strip().lower()
                    if verdict.startswith("yes"):
                        relevant.append(doc)
                except Exception:
                    relevant.append(doc)  # fail-open on grader error
            LOGGER.info(
                "Graded %d docs — %d relevant (iteration %d)",
                len(state["documents"]), len(relevant), state["iterations"],
            )
            return {**state, "relevant_docs": relevant}

        def rewrite_node(state: RAGState) -> RAGState:
            try:
                rewritten = rewriter.invoke({"question": state["query"]}).strip()
                LOGGER.info("Query rewritten: %r -> %r", state["query"], rewritten)
                return {**state, "query": rewritten}
            except Exception:
                return state

        def generate_node(state: RAGState) -> RAGState:
            docs = state["relevant_docs"] or state["documents"]
            context = format_documents(docs)
            sources = ", ".join(sorted({
                doc.metadata.get("source", "unknown") for doc in docs
            }))
            try:
                answer = answerer.invoke({
                    "context": context,
                    "question": state["query"],
                }).strip()
                confidence = "high" if len(state["relevant_docs"]) >= top_k else (
                    "medium" if state["relevant_docs"] else "low"
                )
            except Exception:
                LOGGER.exception("Answer generation failed.")
                answer = "I couldn't retrieve that information right now."
                confidence = "low"
                sources = "error"
            return {**state, "answer": answer, "source": sources, "confidence": confidence}

        def routing(state: RAGState) -> str:
            enough = len(state.get("relevant_docs", [])) >= top_k
            at_limit = state["iterations"] >= 2
            return "generate" if (enough or at_limit) else "rewrite"

        graph = StateGraph(RAGState)
        graph.add_node("retrieve", retrieve_node)
        graph.add_node("grade", grade_node)
        graph.add_node("rewrite", rewrite_node)
        graph.add_node("generate", generate_node)
        graph.set_entry_point("retrieve")
        graph.add_edge("retrieve", "grade")
        graph.add_conditional_edges(
            "grade", routing, {"generate": "generate", "rewrite": "rewrite"}
        )
        graph.add_edge("rewrite", "retrieve")
        graph.add_edge("generate", END)
        self._graph = graph.compile()

    def run(self, message: str, history: str = "") -> dict:
        LOGGER.info("RetrieverAgent (Corrective RAG): %s", message[:80])
        try:
            final = self._graph.invoke({
                "query": message,
                "history": history or "No history",
                "documents": [],
                "relevant_docs": [],
                "answer": "",
                "source": "unknown",
                "confidence": "low",
                "iterations": 0,
            })
            return {
                "answer": final["answer"],
                "source": final["source"],
                "confidence": final["confidence"],
            }
        except Exception:
            LOGGER.exception("RetrieverAgent failed.")
            return {
                "answer": "I encountered an issue retrieving information from the knowledge base.",
                "source": "error",
                "confidence": "low",
            }
