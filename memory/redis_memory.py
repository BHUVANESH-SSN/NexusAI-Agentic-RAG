import logging
from typing import List
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from llm.factory import get_settings

LOGGER = logging.getLogger(__name__)

class RedisSessionManager:
    """Manages chat history using Redis with session isolation and TTL."""
    
    def __init__(self, ttl_seconds: int = 3600):
        self.settings = get_settings()
        self.ttl = ttl_seconds
        LOGGER.info("RedisSessionManager initialized with TTL=%ds", self.ttl)

    def _get_history(self, user_id: str, session_id: str) -> RedisChatMessageHistory:
        """Helper to create a Redis history instance for a specific session."""
        key = f"chat_history:{user_id}:{session_id}"
        return RedisChatMessageHistory(
            session_id=key,
            url=self.settings.redis_url,
            ttl=self.ttl
        )

    def get_messages(self, user_id: str, session_id: str) -> List[BaseMessage]:
        """Retrieve all messages for a session."""
        history = self._get_history(user_id, session_id)
        return history.messages

    def get_history_string(self, user_id: str, session_id: str) -> str:
        """Format history as a string for LLM context."""
        messages = self.get_messages(user_id, session_id)
        formatted = []
        for msg in messages:
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            formatted.append(f"{role}: {msg.content}")
        return "\n".join(formatted)

    def save_turn(self, user_id: str, session_id: str, user_message: str, assistant_message: str):
        """Save a user message and assistant response to Redis."""
        history = self._get_history(user_id, session_id)
        history.add_user_message(user_message)
        history.add_ai_message(assistant_message)
        LOGGER.debug("Turn saved to Redis for session %s:%s", user_id, session_id)
