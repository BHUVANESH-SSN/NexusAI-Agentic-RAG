import logging
from typing import Dict, Any

from router.supervisor import Supervisor
from agents.tool_agent import ToolAgent
from agents.db_agent import DBAgent
from agents.validation_agent import ValidationAgent

# Import legacy agents
from agent.retriever_agent import RetrieverAgent
from agent.chat_agent import ChatAgent
from memory.redis_memory import RedisSessionManager
from llm.factory import get_llm_with_failover

LOGGER = logging.getLogger(__name__)

class EnterpriseChatbot:
    """The central DAG orchestrator enforcing Supervisor -> Agent -> Validator patterns."""
    
    def __init__(self, retriever):
        self.memory = RedisSessionManager(ttl_seconds=3600)
        self.llm = get_llm_with_failover()
        
        self.supervisor = Supervisor()
        
        # Core Execution Agents
        self.retriever_agent = RetrieverAgent(llm=self.llm, retriever=retriever) 
        self.chat_agent = ChatAgent(llm=self.llm)
        
        # New Execution Agents
        self.tool_agent = ToolAgent()
        self.db_agent = DBAgent()
        
        # Final Layer Agent
        self.validator = ValidationAgent()
        
    def process_message(self, user_id: str, session_id: str, message: str) -> Dict[str, Any]:
        LOGGER.info("Process User=%s, Session=%s", user_id, session_id)
        
        # 1. Load History
        history_str = self.memory.get_history_string(user_id, session_id)
        
        # 2. Supervisor Route Determination
        route = self.supervisor.route(message)
        LOGGER.info("Supervisor elected route: %s", route)
        
        # 3. Agent Execution (Single Responsibility)
        agent_result = {}
        if route == "retriever":
            agent_result = self.retriever_agent.run(message=message, history=history_str)
            # Standardize format if output was raw string
            if isinstance(agent_result, str): agent_result = {"answer": agent_result, "source": "Retriever Documents"}
            
        elif route == "db":
            agent_result = self.db_agent.run(message, history_str)
            
        elif route == "tool":
            agent_result = self.tool_agent.run(message, history_str)
            
        else:
            agent_result = self.chat_agent.run(message=message, history=history_str)
            if isinstance(agent_result, str): agent_result = {"answer": agent_result, "source": "Chat Model"}
            
        if not isinstance(agent_result, dict):
            agent_result = {"answer": str(agent_result), "source": route}
            
        # 4. Validation (Strict Ending Step)
        final_result = self.validator.validate(message, agent_result)
        
        # 5. Persist the turn
        self.memory.save_turn(
            user_id=user_id,
            session_id=session_id,
            user_message=message,
            assistant_message=final_result.get("answer", "")
        )
        
        return final_result
