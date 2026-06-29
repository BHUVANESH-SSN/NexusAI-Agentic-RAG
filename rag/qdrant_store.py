import logging
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from langchain_qdrant import QdrantVectorStore

LOGGER = logging.getLogger(__name__)
COLLECTION_NAME = "nexusai_docs"
VECTOR_DIM = 384  # all-MiniLM-L6-v2 output dimension


def get_qdrant_client(store_path: Path) -> QdrantClient:
    """Return a file-based Qdrant client (no server required)."""
    store_path.mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(store_path))


def ensure_collection(client: QdrantClient) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION_NAME not in existing:
        LOGGER.info("Creating Qdrant collection '%s'", COLLECTION_NAME)
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        )


def get_vector_store(client: QdrantClient, embeddings) -> QdrantVectorStore:
    ensure_collection(client)
    return QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )
