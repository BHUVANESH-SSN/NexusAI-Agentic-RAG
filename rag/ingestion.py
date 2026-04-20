import logging
import pickle
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from llm.factory import get_embeddings, get_settings

LOGGER = logging.getLogger(__name__)


def load_pdf_documents():
    settings = get_settings()
    pdf_files = sorted(settings.docs_path.glob("*.pdf"))

    if not pdf_files:
        raise FileNotFoundError(
            f"No PDF files found in {settings.docs_path}. "
            "Add documents to data/company_docs before running ingest.py."
        )

    documents = []
    for pdf_file in pdf_files:
        LOGGER.info("Loading PDF: %s", pdf_file.name)
        pages = PyPDFLoader(str(pdf_file)).load()
        for page in pages:
            # Enhanced metadata extraction
            page.metadata["source"] = pdf_file.name
            
            # Heuristic for department/section if not already present
            content_lower = page.page_content.lower()
            if "hr" in content_lower or "employee" in content_lower:
                page.metadata["department"] = "HR"
            elif "finance" in content_lower or "payroll" in content_lower:
                page.metadata["department"] = "Finance"
            elif "it" in content_lower or "security" in content_lower:
                page.metadata["department"] = "IT"
            else:
                page.metadata["department"] = "General"
                
        documents.extend(pages)

    return documents


def split_documents(documents):
    settings = get_settings()
    # Recursive splitting is better than fixed-size splitting
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""],
    )
    return splitter.split_documents(documents)


def build_indices():
    settings = get_settings()
    settings.vector_store_path.mkdir(parents=True, exist_ok=True)

    documents = load_pdf_documents()
    chunks = split_documents(documents)

    # 1. Build & Save FAISS (Dense)
    LOGGER.info("Creating FAISS index with %s chunks", len(chunks))
    vector_store = FAISS.from_documents(chunks, get_embeddings())
    vector_store.save_local(str(settings.vector_store_path))
    LOGGER.info("Saved FAISS index to %s", settings.vector_store_path)

    # 2. Build & Save BM25 (Sparse) 
    # BM25Retriever doesn't have a save_local, so we save the chunks
    bm25_path = settings.vector_store_path / "bm25_chunks.pkl"
    LOGGER.info("Saving BM25 chunks to %s", bm25_path)
    with open(bm25_path, "wb") as f:
        pickle.dump(chunks, f)

    return {
        "documents": len(documents),
        "chunks": len(chunks),
        "index_path": str(settings.vector_store_path),
    }


if __name__ == "__main__":
    from llm.factory import configure_logging
    configure_logging()
    build_indices()
