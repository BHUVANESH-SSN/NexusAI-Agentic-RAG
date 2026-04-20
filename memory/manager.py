import logging
from threading import Lock

from langchain_classic.memory import ConversationBufferMemory

LOGGER = logging.getLogger(__name__)


class SessionMemoryManager:
    def __init__(self) -> None:
        self._memories = {}
        self._lock = Lock()

    def get_memory(self, user_id: str) -> ConversationBufferMemory:
        if not user_id.strip():
            raise ValueError("user_id cannot be empty.")

        with self._lock:
            memory = self._memories.get(user_id)
            if memory is None:
                LOGGER.info("Creating new memory for user_id=%s", user_id)
                memory = ConversationBufferMemory(
                    memory_key="chat_history",
                    return_messages=True,
                    input_key="input",
                    output_key="output",
                )
                self._memories[user_id] = memory

        return memory

    def get_history(self, user_id: str) -> str:
        memory = self.get_memory(user_id)
        messages = memory.load_memory_variables({}).get("chat_history", [])
        if not messages:
            return "No previous conversation."

        lines = []
        for message in messages:
            speaker = "User" if message.type == "human" else "Assistant"
            lines.append(f"{speaker}: {message.content}")

        return "\n".join(lines)

    def save_turn(self, user_id: str, user_message: str, assistant_message: str) -> None:
        memory = self.get_memory(user_id)
        memory.save_context(
            {"input": user_message},
            {"output": assistant_message},
        )
