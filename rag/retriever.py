import logging
import pickle
from typing import List, Any

from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

from llm.factory import get_embeddings, get_settings, get_llm_with_failover, get_reranker

LOGGER = logging.getLogger(__name__)

# --- Query Rewriting Prompt ---

_REWRITE_PROMPT = """\
You are an AI assistant tasked with improving search queries for a company RAG system.
Given the user message and conversation history, rewrite the user's latest query \
to be more descriptive and search-friendly.
- Expand acronyms if known (e.g., UPSI -> Unpublished Price Sensitive Information).
- Add relevant keywords.
- Keep the original intent clear.
- Output ONLY the rewritten query text.

Conversation History:
{history}

Latest Message:
{message}

Rewritten Query:"""


class CompanyRetriever:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._vector_store = None
        self._bm25_retriever = None
        self._reranker = None
        
        # Initialize Query Rewriter with failover
        llm = get_llm_with_failover()
        prompt = ChatPromptTemplate.from_template(_REWRITE_PROMPT)
        self.rewriter_chain = prompt | llm | StrOutputParser()

    def clear_cache(self):
        """Clears internal index caches to force a reload from disk on next query."""
        LOGGER.info("Clearing retriever index cache for reload.")
        self._vector_store = None
        self._bm25_retriever = None

    def _load_indices(self):
        """Loads both FAISS and BM25 indices."""
        # 1. Load FAISS (Dense)
        if self._vector_store is None:
            if not self.settings.vector_store_path.exists():
                raise FileNotFoundError(f"FAISS index not found at {self.settings.vector_store_path}")
            
            index_file = self.settings.vector_store_path / "index.faiss"
            if index_file.exists():
                import os, time
                mtime = os.path.getmtime(index_file)
                LOGGER.info("FAISS index file timestamp: %s", time.ctime(mtime))
            
            LOGGER.info("Loading FAISS index from %s", self.settings.vector_store_path)
            self._vector_store = FAISS.load_local(
                str(self.settings.vector_store_path),
                get_embeddings(),
                allow_dangerous_deserialization=True,
            )

        # 2. Load BM25 (Sparse)
        if self._bm25_retriever is None:
            bm25_path = self.settings.vector_store_path / "bm25_chunks.pkl"
            if not bm25_path.exists():
                LOGGER.warning("BM25 cache not found at %s. Falling back to Dense-only.", bm25_path)
            else:
                LOGGER.info("Loading BM25 chunks from %s", bm25_path)
                with open(bm25_path, "rb") as f:
                    chunks = pickle.load(f)
                self._bm25_retriever = BM25Retriever.from_documents(chunks)
                self._bm25_retriever.k = 10 # Retrieve 10 candidates for re-ranking

    def _get_reranker(self):
        if self._reranker is None:
            self._reranker = get_reranker()
        return self._reranker

    def _rewrite_query(self, message: str, history: str) -> str:
        """Uses LLM to polish the query."""
        try:
            rewritten = self.rewriter_chain.invoke({"message": message, "history": history}).strip()
            LOGGER.info("Query rewritten: '%s' -> '%s'", message, rewritten)
            return rewritten
        except Exception as e:
            LOGGER.warning("Query rewriting failed: %s. Using original message.", e)
            return message

    def retrieve(self, message: str, history: str = "No history") -> List[Document]:
        """Multi-stage Hybrid Retrieval with Re-ranking."""
        self._load_indices()
        
        # Stage 0: Query Rewriting
        query = self._rewrite_query(message, history)

        # Stage 1: Hybrid Retrieval
        # A. Vector Retrieval (Dense)
        dense_docs = self._vector_store.as_retriever(search_kwargs={"k": 10}).invoke(query)
        
        # B. BM25 Retrieval (Sparse)
        sparse_docs = []
        if self._bm25_retriever:
            sparse_docs = self._bm25_retriever.invoke(query)
            
        # C. Combine & Deduplicate
        seen_content = set()
        candidates = []
        for doc in dense_docs + sparse_docs:
            if doc.page_content not in seen_content:
                candidates.append(doc)
                seen_content.add(doc.page_content)

        LOGGER.info("Stage 1 complete: %d unique candidates found.", len(candidates))

        # Stage 2: Re-ranking
        if not candidates:
            return []
            
        reranker = self._get_reranker()
        pairs = [[query, doc.page_content] for doc in candidates]
        
        # CrossEncoder returns scores
        scores = reranker.predict(pairs)
        
        # Attach scores to documents and sort
        for doc, score in zip(candidates, scores):
            doc.metadata["relevance_score"] = float(score)
            
        candidates.sort(key=lambda x: x.metadata["relevance_score"], reverse=True)
        
        # Stage 3: Selection
        final_docs = candidates[:3]
        LOGGER.info("Stage 2 complete: Top 3 re-ranked documents selected.")
        
        return final_docs


def format_documents(documents: List[Document]) -> str:
    if not documents:
        return "No relevant context found in the company documents."

    blocks = []
    for document in documents:
        source = document.metadata.get("source", "unknown")
        page = document.metadata.get("page", "n/a")
        section = document.metadata.get("section") or document.metadata.get("title", "n/a")
        dept = document.metadata.get("department", "General")
        content = document.page_content.strip()
        
        blocks.append(
            f"Source: {source} | Dept: {dept} | Section: {section} | Page: {page}\n"
            f"{content}"
        )

    return "\n\n".join(blocks)
