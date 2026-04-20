import json
import logging
from typing import Any, List

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from rag.retriever import CompanyRetriever, format_documents

LOGGER = logging.getLogger(__name__)

class AgentResponse(BaseModel):
    answer: str = Field(description="The summarized and human-friendly answer based on company documents.")
    source: str = Field(description="Comma-separated names of the source documents used.")
    confidence: str = Field(description="Confidence level: high, medium, or low.")

_SYSTEM_PROMPT = """\
You are a strict enterprise AI assistant.
Use ONLY the provided context to answer the question.

RULES:
1.  **Strict Fidelity**: Use ONLY the provided context to answer the question. Do NOT use general knowledge.
2.  **No Extraneous Info**: Do NOT add any information that is not present in the context.
3.  **Fallback**: If information is missing, say exactly: "The document does not provide enough details."
4.  **Faithful Rephrasing**: Rephrase and summarize, but stay faithful to the content.
5.  **Process Handling**: If the answer involves steps, you MUST use bullet points.
6.  **Formatting**: Keep it concise and clear.

RESPONSE FORMAT (JSON ONLY):
{{
  "answer": "...",
  "source": "...",
  "confidence": "high/medium/low"
}}

{format_instructions}

CONTEXT FROM COMPANY DOCUMENTS:
{context}
"""

class RetrieverAgent:
    def __init__(self, llm, retriever: CompanyRetriever) -> None:
        self.retriever = retriever
        self.parser = PydanticOutputParser(pydantic_object=AgentResponse)
        
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", _SYSTEM_PROMPT),
                (
                    "human",
                    "Conversation history:\n{history}\n\n"
                    "User question: {message}",
                ),
            ]
        ).partial(format_instructions=self.parser.get_format_instructions())
        
        self.chain = self.prompt | llm

    def _extract_source_names(self, documents: List[Any]) -> str:
        if not documents:
            return "none"
        sources = set()
        for doc in documents:
            filename = doc.metadata.get("source", "unknown").split("/")[-1].split("\\")[-1]
            sources.add(filename)
        return ", ".join(sorted(sources))

    def run(self, message: str, history: str) -> dict:
        LOGGER.info("Retriever Agent processing query: %s", message)
        try:
            documents = self.retriever.retrieve(message, history=history)
            if not documents:
                return {
                    "answer": "The document does not provide enough details.",
                    "source": "none",
                    "confidence": "low"
                }

            context_str = format_documents(documents)
            source_names = self._extract_source_names(documents)

            response = self.chain.invoke({
                "context": context_str,
                "history": history,
                "message": message
            })
            
            try:
                content = response.content if hasattr(response, 'content') else str(response)
                parsed = self.parser.parse(content)
                return parsed.model_dump()
            except Exception:
                content = response.content if hasattr(response, 'content') else str(response)
                return {
                    "answer": content.strip(),
                    "source": source_names,
                    "confidence": "medium"
                }

        except Exception as e:
            LOGGER.exception("Retriever Agent runtime error: %s", e)
            return {
                "answer": "I encountered an error while searching for company data.",
                "source": "system",
                "confidence": "low"
            }
