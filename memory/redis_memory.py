import logging
from typing import List
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import redis

from llm.factory import get_settings

LOGGER = logging.getLogger(__name__)

class RedisSessionManager:
    """Manages chat history using Redis with session isolation and TTL.
    Includes a local fallback for added robustness in transient environments.
    """
    
    _local_fallback = {} # In-memory backup
    
    def __init__(self, ttl_seconds: int = 3600):
        self.settings = get_settings()
        self.ttl = ttl_seconds
        # Force 127.0.0.1 and ensure it starts with redis://
        raw_url = self.settings.redis_url.replace("localhost", "127.0.0.1")
        if not raw_url.startswith("redis://"):
            raw_url = f"redis://{raw_url}"
        self.redis_url = raw_url
        
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            self.redis_client.ping()
            LOGGER.info("RedisSessionManager connected to %s", self.redis_url)
        except Exception as e:
            LOGGER.error("CRITICAL: RedisSessionManager could not connect to Redis: %s", e)
            self.redis_client = None

    def _get_history(self, user_id: str, session_id: str) -> List[dict]:
        """Directly fetch history list from Redis as dicts."""
        if not self.redis_client:
            return []
        
        key = f"chat_history:{user_id}:{session_id}"
        try:
            raw_msgs = self.redis_client.lrange(key, 0, -1)
            # Messages are stored as JSON strings
            import json
            return [json.loads(m) for m in raw_msgs]
        except Exception as e:
            LOGGER.error(f"Direct Redis fetch failed: {e}")
            return []

    def get_messages(self, user_id: str, session_id: str) -> List[BaseMessage]:
        """Map raw redis dicts to LangChain Message objects."""
        # Check Redis first
        raw_msgs = self._get_history(user_id, session_id)
        
        msgs = []
        for m in raw_msgs:
            if m.get("type") == "human":
                msgs.append(HumanMessage(content=m["content"]))
            else:
                msgs.append(AIMessage(content=m["content"]))
        
        # If Redis is empty, use local fallback
        if not msgs:
            fallback_key = f"{user_id}:{session_id}"
            msgs = self._local_fallback.get(fallback_key, [])
            if msgs:
                LOGGER.info("Redis empty, using local fallback.")
        
        return msgs

    def get_history_string(self, user_id: str, session_id: str) -> str:
        """Format history for LLM prompt."""
        messages = self.get_messages(user_id, session_id)
        formatted = []
        for msg in messages:
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            formatted.append(f"{role}: {msg.content}")
        return "\n".join(formatted)

    def save_turn(self, user_id: str, session_id: str, user_message: str, assistant_message: str):
        """Save to both Redis (Direct) and Local Fallback."""
        import json
        fallback_key = f"{user_id}:{session_id}"
        if fallback_key not in self._local_fallback:
            self._local_fallback[fallback_key] = []
        
        u_msg = HumanMessage(content=user_message)
        a_msg = AIMessage(content=assistant_message)
        self._local_fallback[fallback_key].extend([u_msg, a_msg])

        if self.redis_client:
            try:
                key = f"chat_history:{user_id}:{session_id}"
                self.redis_client.rpush(key, json.dumps({"type": "human", "content": user_message}))
                self.redis_client.rpush(key, json.dumps({"type": "ai", "content": assistant_message}))
                self.redis_client.expire(key, self.ttl)
                LOGGER.info("Saved turn directly to Redis: %s", key)
            except Exception as e:
                LOGGER.error(f"Direct Redis save failed: {e}")
