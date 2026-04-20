import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from llm.factory import get_llm_with_failover

LOGGER = logging.getLogger(__name__)

class Supervisor:
    def __init__(self):
        self.llm = get_llm_with_failover()
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a classification supervisor.
Analyze the user's query and strictly categorize it into exactly one of these labels:
- 'retriever' : if asking about company policies, internal documents, or specific corporate facts.
- 'db' : if asking about structured records, employee data, or payroll tables.
- 'tool' : if asking to perform an action (sending email, generating reports).
- 'chat' : for greetings, personal follow-up questions ("what did I ask?", "tell me more"), or general reasoning.

Respond ONLY with the exact lowercase label. Nothing else."""),
            ("human", "{input}")
        ])
        self.chain = prompt | self.llm | StrOutputParser()

    def route(self, message: str) -> str:
        try:
            res = self.chain.invoke({"input": message}).strip().lower()
            valid_routes = ["retriever", "db", "tool", "chat"]
            for route in valid_routes:
                if route in res:
                    return route
            return "chat"
        except Exception as e:
            LOGGER.error(f"Supervisor parsing error: {e}")
            return "chat"
