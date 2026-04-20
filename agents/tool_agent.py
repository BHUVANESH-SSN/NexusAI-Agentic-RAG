import logging
from langgraph.prebuilt import create_react_agent
from tools.email_tool import prepare_email_draft, execute_send_email
from llm.factory import get_llm_with_failover

LOGGER = logging.getLogger(__name__)

class ToolAgent:
    def __init__(self):
        self.llm = get_llm_with_failover()
        self.tools = [prepare_email_draft, execute_send_email]
        
        system_prompt = (
            "You are a highly capable Action Agent with direct access to Email tools. "
            "You CAN send emails directly to recipients using 'execute_send_email'. "
            "POLICY: Always use 'prepare_email_draft' FIRST to propose a draft. "
            "AFTER the user confirms (checks conversation history for 'Yes' or 'Go ahead'), "
            "you MUST immediately call 'execute_send_email' to finalize the task."
        )
        
        self.agent_executor = create_react_agent(
            model=self.llm, 
            tools=self.tools, 
            prompt=system_prompt
        )

    def run(self, message: str, history: str = "") -> dict:
        LOGGER.info("Tool Agent processing trigger.")
        try:
            # Simplify: Only use the last 2 turns of history if possible, or just the current message
            # For now, we'll keep the full history but label it more clearly
            combined_input = f"HISTORY:\n{history}\n\nUSER_REQUEST: {message}"
            
            res = self.agent_executor.invoke({"messages": [("user", combined_input)]})
            
            final_answer = res["messages"][-1].content
            return {
                "answer": final_answer,
                "source": "Workflow Engine"
            }
        except Exception as e:
            LOGGER.error(f"Tool Agent runtime error: {type(e).__name__} - {str(e)}")
            # If it's a tool-specific error, try to return a graceful answer
            return {
                "answer": f"I encountered a technical issue while processing that action: {str(e)}. However, I can still help you with information.",
                "source": "System Notice"
            }
