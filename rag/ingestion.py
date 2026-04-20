import logging
import pickle
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from llm.factory import get_embeddings, get_settings

LOGGER = logging.getLogger(__name__)


def _cosine_similarity(v1, v2):
    """Simple dot product between normalized vectors."""
    return sum(a * b for a, b in zip(v1, v2))


from langchain_community.document_loaders import PyPDFLoader, TextLoader

def get_loader(ext, doc_file):
    """Factory to return the appropriate loader, or None if dependencies missing."""
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
        LOGGER.error(f"Missing dependency for {ext}: {e}. Please install it to enable this format.")
    except Exception as e:
        LOGGER.error(f"Error initializing loader for {ext}: {e}")
    return None

def load_documents():
    """Loads PDF, Markdown, DOCX, and CSV documents from the docs path."""
    settings = get_settings()
    # Support multiple formats
    extensions = ["*.pdf", "*.md", "*.docx", "*.csv"]
    files = []
    for ext in extensions:
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
                # Ensure source is tracked
                page.metadata["source"] = doc_file.name
                
                # Heuristic for department
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
            LOGGER.error(f"Failed to load {doc_file.name}: {e}")

    return documents


def split_documents(documents):
    """Agentic/Semantic Chunking: Groups sentences based on embedding similarity."""
    settings = get_settings()
    embeddings_model = get_embeddings()
    
    all_chunks = []
    
    for doc in documents:
        # 1. Break into sentences (simple splitter)
        text = doc.page_content
        sentences = [s.strip() for s in text.replace("\n", " ").split(".") if len(s.strip()) > 10]
        
        if not sentences:
            all_chunks.append(doc)
            continue
            
        # 2. Embed sentences
        sentence_embeddings = embeddings_model.embed_documents(sentences)
        
        # 3. Group by similarity
        current_chunk_text = [sentences[0]]
        for i in range(1, len(sentences)):
            similarity = _cosine_similarity(sentence_embeddings[i], sentence_embeddings[i-1])
            
            # If meaning shifts significantly (threshold 0.82) OR chunk is getting too big
            if similarity < 0.82 or len(" ".join(current_chunk_text)) > settings.chunk_size:
                # Close current chunk
                all_chunks.append(Document(
                    page_content=" ".join(current_chunk_text),
                    metadata=doc.metadata.copy()
                ))
                current_chunk_text = [sentences[i]]
            else:
                current_chunk_text.append(sentences[i])
        
        # Add last piece
        if current_chunk_text:
            all_chunks.append(Document(
                page_content=" ".join(current_chunk_text),
                metadata=doc.metadata.copy()
            ))
            
    LOGGER.info("Semantic Splitting complete: produced %d chunks from %d docs", len(all_chunks), len(documents))
    return all_chunks


def build_indices():
    settings = get_settings()
    settings.vector_store_path.mkdir(parents=True, exist_ok=True)

    documents = load_documents()
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
