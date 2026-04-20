import logging
from langgraph.prebuilt import create_react_agent
from tools.email_tool import send_email
from llm.factory import get_llm_with_failover

LOGGER = logging.getLogger(__name__)

class ToolAgent:
    def __init__(self):
        self.llm = get_llm_with_failover()
        self.tools = [send_email]
        
        system_prompt = "You are an action-oriented workflow agent. Use your tools to fulfill the user's request. Confirm when actions (e.g. emails) are complete."
        
        # In LangGraph prebuilt v1.0.10, the explicit argument for the system prompt is just 'prompt'
        self.agent_executor = create_react_agent(
            model=self.llm, 
            tools=self.tools, 
            prompt=system_prompt
        )

    def run(self, message: str, history: str = "") -> dict:
        LOGGER.info("Tool Agent processing trigger.")
        try:
            # LangGraph standard invoke shape 
            res = self.agent_executor.invoke({"messages": [("user", message)]})
            
            # Extract final message from trajectory
            final_answer = res["messages"][-1].content
            return {
                "answer": final_answer,
                "source": "Tool Execution: Email"
            }
        except Exception as e:
            LOGGER.exception("Tool Agent failed.")
            return {"answer": f"Action failed. {str(e)}", "source": "error"}
