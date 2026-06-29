import logging
import pickle
from typing import List

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

from llm.factory import get_embeddings, get_settings, get_llm_with_failover, get_reranker

LOGGER = logging.getLogger(__name__)

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
        self._qdrant_client = None
        self._vector_store = None
        self._bm25_retriever = None
        self._parent_store = None

        llm = get_llm_with_failover()
        prompt = ChatPromptTemplate.from_template(_REWRITE_PROMPT)
        self.rewriter_chain = prompt | llm | StrOutputParser()

    def clear_cache(self):
        LOGGER.info("Clearing retriever cache for reload.")
        self._qdrant_client = None
        self._vector_store = None
        self._bm25_retriever = None
        self._parent_store = None

    def _load_indices(self):
        if self._vector_store is None:
            from rag.qdrant_store import get_qdrant_client, get_vector_store
            if not self.settings.vector_store_path.exists():
                raise FileNotFoundError(
                    f"Qdrant index not found at {self.settings.vector_store_path}. "
                    "Run `python -m rag.ingestion` to build it."
                )
            LOGGER.info("Loading Qdrant index from %s", self.settings.vector_store_path)
            self._qdrant_client = get_qdrant_client(self.settings.vector_store_path)
            self._vector_store = get_vector_store(self._qdrant_client, get_embeddings())

        if self._bm25_retriever is None:
            bm25_path = self.settings.vector_store_path / "bm25_chunks.pkl"
            if not bm25_path.exists():
                LOGGER.warning("BM25 cache not found — dense-only retrieval.")
            else:
                LOGGER.info("Loading BM25 chunks from %s", bm25_path)
                with open(bm25_path, "rb") as f:
                    chunks = pickle.load(f)
                from langchain_community.retrievers import BM25Retriever
                self._bm25_retriever = BM25Retriever.from_documents(chunks)
                self._bm25_retriever.k = max(self.settings.retriever_top_k * 4, 10)

        if self._parent_store is None:
            from rag.parent_store import ParentStore
            self._parent_store = ParentStore(self.settings.vector_store_path)

    def _rewrite_query(self, message: str, history: str) -> str:
        try:
            rewritten = self.rewriter_chain.invoke(
                {"message": message, "history": history}
            ).strip()
            LOGGER.info("Query rewritten: '%s' -> '%s'", message, rewritten)
            return rewritten
        except Exception as e:
            LOGGER.warning("Query rewriting failed: %s. Using original.", e)
            return message

    def retrieve(self, message: str, history: str = "No history") -> List[Document]:
        """Hybrid retrieval: Qdrant dense + BM25 sparse, CrossEncoder reranked."""
        self._load_indices()
        query = self._rewrite_query(message, history)
        fetch_k = max(self.settings.retriever_top_k * 4, 10)

        # Stage 1: Dense (Qdrant)
        dense_docs = self._vector_store.similarity_search(query, k=fetch_k)

        # Stage 2: Sparse (BM25)
        sparse_docs = self._bm25_retriever.invoke(query) if self._bm25_retriever else []

        # Stage 3: Deduplicate
        seen: set = set()
        candidates: List[Document] = []
        for doc in dense_docs + sparse_docs:
            if doc.page_content not in seen:
                candidates.append(doc)
                seen.add(doc.page_content)
        LOGGER.info("Stage 1: %d unique candidates.", len(candidates))

        if not candidates:
            return []

        # Stage 4: CrossEncoder rerank
        reranker = get_reranker()
        pairs = [[query, doc.page_content] for doc in candidates]
        scores = reranker.predict(pairs)
        for doc, score in zip(candidates, scores):
            doc.metadata["relevance_score"] = float(score)
        candidates.sort(key=lambda x: x.metadata["relevance_score"], reverse=True)

        final = candidates[:self.settings.retriever_top_k]
        LOGGER.info("Stage 2: top %d selected.", self.settings.retriever_top_k)

        # Stage 5: Expand child chunks → parent context
        expanded: List[Document] = []
        seen_parents: set = set()
        for doc in final:
            pid = doc.metadata.get("parent_id")
            if pid and pid not in seen_parents and self._parent_store:
                parent_text = self._parent_store.get(pid)
                if parent_text:
                    expanded.append(Document(
                        page_content=parent_text,
                        metadata={**doc.metadata, "expanded_to_parent": True},
                    ))
                    seen_parents.add(pid)
                    continue
            expanded.append(doc)
        LOGGER.info("Stage 5: %d docs after parent expansion.", len(expanded))
        return expanded


def format_documents(documents: List[Document]) -> str:
    if not documents:
        return "No relevant context found in the company documents."
    blocks = []
    for document in documents:
        source = document.metadata.get("source", "unknown")
        page = document.metadata.get("page", "n/a")
        section = document.metadata.get("section") or document.metadata.get("title", "n/a")
        dept = document.metadata.get("department", "General")
        blocks.append(
            f"Source: {source} | Dept: {dept} | Section: {section} | Page: {page}\n"
            f"{document.page_content.strip()}"
        )
    return "\n\n".join(blocks)
