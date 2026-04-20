import logging
import json
from typing import Optional, Dict, Any
import redis

from llm.factory import get_embeddings, get_settings

LOGGER = logging.getLogger(__name__)

class SemanticCache:
    """Stores query embeddings and results in Redis to bypass LLM for similar questions."""
    
    def __init__(self, threshold: float = 0.96):
        self.settings = get_settings()
        self.threshold = threshold
        self.embeddings = get_embeddings()
        
        # Use existing Redis connection logic from memory
        raw_url = self.settings.redis_url.replace("localhost", "127.0.0.1")
        if not raw_url.startswith("redis://"):
            raw_url = f"redis://{raw_url}"
            
        try:
            self.redis_client = redis.from_url(raw_url, decode_responses=True)
            self.redis_client.ping()
            LOGGER.info("SemanticCache connected to Redis.")
        except Exception as e:
            LOGGER.error(f"SemanticCache Redis connection failed: {e}")
            self.redis_client = None

    def _get_all_cache_keys(self):
        if not self.redis_client: return []
        return self.redis_client.keys("semantic_cache:*")

    def _cosine_similarity(self, v1: list, v2: list) -> float:
        """Simple dot product (assuming embeddings are normalized)."""
        return sum(a * b for a, b in zip(v1, v2))

    def check(self, query: str) -> Optional[Dict[str, Any]]:
        """Checks if a similar query exists in cache."""
        if not self.redis_client: return None
        
        try:
            query_vector = self.embeddings.embed_query(query)
            keys = self._get_all_cache_keys()
            
            for key in keys:
                cached_data_raw = self.redis_client.get(key)
                if not cached_data_raw: continue
                
                cached_entry = json.loads(cached_data_raw)
                cached_vector = cached_entry["embedding"]
                
                similarity = self._cosine_similarity(query_vector, cached_vector)
                
                if similarity >= self.threshold:
                    LOGGER.info(f"[CACHE HIT] Similarity {similarity:.4f} for query: {query}")
                    return cached_entry["result"]
                    
            return None
        except Exception as e:
            LOGGER.error(f"Semantic cache check failed: {e}")
            return None

    def save(self, query: str, result: Dict[str, Any]):
        """Saves a query and its result to the semantic cache."""
        if not self.redis_client: return
        
        # Avoid caching error responses
        if "error" in str(result).lower(): return
        
        try:
            query_vector = self.embeddings.embed_query(query)
            # Create a unique key based on the query start
            safe_query = "".join([c if c.isalnum() else "_" for c in query[:30]])
            key = f"semantic_cache:{safe_query}_{hash(query) % 10000}"
            
            payload = {
                "query": query,
                "embedding": query_vector,
                "result": result
            }
            
            # Cache for 24 hours
            self.redis_client.set(key, json.dumps(payload), ex=86400)
            LOGGER.info(f"[CACHE SAVE] Saved semantic entry for: {query[:50]}...")
        except Exception as e:
            LOGGER.error(f"Semantic cache save failed: {e}")
