import logging
import pickle
from langchain_community.document_loaders import PyPDFLoader, TextLoader

from llm.factory import get_embeddings, get_settings

LOGGER = logging.getLogger(__name__)


def get_loader(ext, doc_file):
    try:
        if ext == ".pdf":
            return PyPDFLoader(str(doc_file))
        elif ext == ".md":
            return TextLoader(str(doc_file), encoding="utf-8")
        elif ext == ".docx":
            from langchain_community.document_loaders import Docx2txtLoader
            return Docx2txtLoader(str(doc_file))
        elif ext == ".csv":
            from langchain_community.document_loaders import CSVLoader
            return CSVLoader(str(doc_file), encoding="utf-8")
    except ImportError as e:
        LOGGER.error("Missing dependency for %s: %s", ext, e)
    except Exception as e:
        LOGGER.error("Error initialising loader for %s: %s", ext, e)
    return None


def load_documents():
    settings = get_settings()
    files = []
    for ext in ["*.pdf", "*.md", "*.docx", "*.csv"]:
        files.extend(list(settings.docs_path.glob(ext)))
    files = sorted(files)

    if not files:
        LOGGER.warning("No documents found in %s.", settings.docs_path)
        return []

    documents = []
    for doc_file in files:
        ext = doc_file.suffix.lower()
        LOGGER.info("Loading %s: %s", ext[1:].upper(), doc_file.name)
        try:
            loader = get_loader(ext, doc_file)
            if not loader:
                continue
            pages = loader.load()
            for page in pages:
                page.metadata["source"] = doc_file.name
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
        except Exception as e:
            LOGGER.error("Failed to load %s: %s", doc_file.name, e)
    return documents


def split_parent_child(documents):
    """Return (parent_texts dict, child_chunks list).

    Parent chunks (800 tokens): passed to the LLM as context.
    Child chunks (200 tokens): embedded and stored in Qdrant for retrieval precision.
    Each child carries a parent_id in its metadata.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from rag.parent_store import ParentStore

    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800, chunk_overlap=80,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=200, chunk_overlap=20,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    child_chunks = []
    parent_texts: dict = {}

    for parent_doc in parent_splitter.split_documents(documents):
        parent_id = ParentStore.new_id()
        parent_texts[parent_id] = parent_doc.page_content
        for child in child_splitter.split_documents([parent_doc]):
            child.metadata["parent_id"] = parent_id
            child_chunks.append(child)

    LOGGER.info(
        "Parent-child split: %d parents → %d children from %d docs",
        len(parent_texts), len(child_chunks), len(documents),
    )
    return parent_texts, child_chunks


def build_indices():
    from rag.qdrant_store import get_qdrant_client, get_vector_store, COLLECTION_NAME, VECTOR_DIM
    from qdrant_client.models import VectorParams, Distance
    from rag.parent_store import ParentStore

    settings = get_settings()
    settings.vector_store_path.mkdir(parents=True, exist_ok=True)

    documents = load_documents()
    if not documents:
        LOGGER.warning("No documents found — skipping index build.")
        return {"documents": 0, "chunks": 0, "parents": 0, "index_path": str(settings.vector_store_path)}

    parent_texts, child_chunks = split_parent_child(documents)
    embeddings = get_embeddings()

    # 1. Qdrant — child chunks
    LOGGER.info("Building Qdrant index with %d child chunks", len(child_chunks))
    client = get_qdrant_client(settings.vector_store_path)
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION_NAME in existing:
        client.delete_collection(COLLECTION_NAME)
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
    )
    vector_store = get_vector_store(client, embeddings)
    vector_store.add_documents(child_chunks)

    # 2. Parent store
    store = ParentStore(settings.vector_store_path)
    store.clear()
    store.save_all(parent_texts)
    LOGGER.info("Parent store saved: %d entries", len(parent_texts))

    # 3. BM25 — child chunks
    bm25_path = settings.vector_store_path / "bm25_chunks.pkl"
    with open(bm25_path, "wb") as f:
        pickle.dump(child_chunks, f)
    LOGGER.info("BM25 index saved.")

    return {
        "documents": len(documents),
        "chunks": len(child_chunks),
        "parents": len(parent_texts),
        "index_path": str(settings.vector_store_path),
    }


if __name__ == "__main__":
    from llm.factory import configure_logging
    configure_logging()
    build_indices()
