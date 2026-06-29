import logging
import time
import uuid
from typing import Optional, Dict, Any

from llm.factory import get_embeddings, get_settings

LOGGER = logging.getLogger(__name__)

_CACHE_COLLECTION = "semantic_cache"
_CACHE_TTL = 86400  # 24 h


class SemanticCache:
    """ANN-backed semantic cache using Qdrant (separate collection from the doc index).

    Cache entries live in vector_store_path/cache/ — a different Qdrant path from
    the document index, so the two clients never hold the same file lock.
    """

    def __init__(self, threshold: float = 0.96):
        self.threshold = threshold
        self.embeddings = get_embeddings()
        self._qdrant = None

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import VectorParams, Distance
            from rag.qdrant_store import VECTOR_DIM

            settings = get_settings()
            cache_path = settings.vector_store_path / "cache"
            cache_path.mkdir(parents=True, exist_ok=True)

            self._qdrant = QdrantClient(path=str(cache_path))
            existing = {c.name for c in self._qdrant.get_collections().collections}
            if _CACHE_COLLECTION not in existing:
                self._qdrant.create_collection(
                    collection_name=_CACHE_COLLECTION,
                    vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
                )
            LOGGER.info("SemanticCache connected to Qdrant (ANN lookup).")
        except Exception as e:
            LOGGER.warning("SemanticCache Qdrant init failed; cache disabled: %s", e)
            self._qdrant = None

    def check(self, query: str) -> Optional[Dict[str, Any]]:
        if not self._qdrant:
            return None
        try:
            query_vector = self.embeddings.embed_query(query)
            hits = self._qdrant.search(
                collection_name=_CACHE_COLLECTION,
                query_vector=query_vector,
                limit=1,
                score_threshold=self.threshold,
            )
            if hits:
                payload = hits[0].payload or {}
                if time.time() - payload.get("ts", 0) > _CACHE_TTL:
                    return None
                LOGGER.info("[CACHE HIT] Similarity %.4f for query: %s", hits[0].score, query)
                return payload.get("result")
            return None
        except Exception as e:
            LOGGER.error("Semantic cache check failed: %s", e)
            return None

    def save(self, query: str, result: Dict[str, Any]) -> None:
        if not self._qdrant:
            return
        if "error" in str(result).lower():
            return
        try:
            from qdrant_client.models import PointStruct

            query_vector = self.embeddings.embed_query(query)
            self._qdrant.upsert(
                collection_name=_CACHE_COLLECTION,
                points=[PointStruct(
                    id=str(uuid.uuid4()),
                    vector=query_vector,
                    payload={"query": query, "result": result, "ts": time.time()},
                )],
            )
            LOGGER.info("[CACHE SAVE] Saved semantic entry for: %.50s", query)
        except Exception as e:
            LOGGER.error("Semantic cache save failed: %s", e)
