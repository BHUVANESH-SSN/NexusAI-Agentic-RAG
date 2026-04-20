import logging
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

LOGGER = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an expert Enterprise AI Assistant for a large corporation.
You handle general greetings, reasoning, and follow-up questions that do not require document lookup.

OPERATIONAL GUIDELINES:
1.  **Professional Tone**: Maintain a formal, authoritative, yet helpful enterprise tone.
2.  **Action Words**: Use action-oriented language ("must", "will", "should").
3.  **Conciseness**: Keep your answer between 3 to 5 lines.
4.  **No Hallucinations**: Do not invent facts about the company. If unsure, state you are a general assistant.
"""


class ChatAgent:
    def __init__(self, llm) -> None:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", _SYSTEM_PROMPT),
                (
                    "human",
                    "### CONVERSATION HISTORY\n"
                    "{history}\n"
                    "--- END OF HISTORY ---\n\n"
                    "LATEST USER MESSAGE: {message}\n"
                    "INSTRUCTION: If the user is asking about the history above, answer using that history. If it is a greeting, reply accordingly."
                ),
            ]
        )
        self.chain = prompt | llm | StrOutputParser()

    def run(self, message: str, history: str) -> dict:
        LOGGER.info("Chat Agent processing message")
        try:
            answer = self.chain.invoke({
                "history": history,
                "message": message
            })
            
            return {
                "answer": answer.strip(),
                "source": "general_knowledge",
                "confidence": "high"
            }
        except Exception as e:
            LOGGER.exception("Chat Agent error: %s", e)
            return {
                "answer": "I'm having trouble responding right now.",
                "source": "system",
                "confidence": "low"
            }
