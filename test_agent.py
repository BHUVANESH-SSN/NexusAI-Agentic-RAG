import sys
import logging
import traceback
from agent.chatbot import EnterpriseChatbot
from rag.retriever import CompanyRetriever

logging.basicConfig(level=logging.WARNING)

def test_pipeline():
    print("\n" + "="*60)
    print("🚀 INITIALIZING ENTERPRISE MULTI-AGENT CHATBOT...")
    print("="*60)
    
    try:
        retriever = CompanyRetriever()
        bot = EnterpriseChatbot(retriever=retriever)
        print("✅ Backend Loaded Successfully.\n")
    except Exception as e:
        print(f"❌ Initialization Error: {e}")
        print("Please ensure your .env variables and vector indexes are set up!")
        traceback.print_exc()
        sys.exit(1)
        
    queries = [
        # Test 1: Data Fetching (DB Agent)
        "Fetch the most recent violations for our employees from the database.",
        
        # Test 2: Tool Execution (Tool Agent)
        "Can you email the latest HR audit report to admin@company.com?",
        
        # Test 3: RAG Retrieval (Retriever Agent)
        "What is the company policy concerning data retention?"
    ]
    
    for i, q in enumerate(queries, 1):
        print(f"\n[{i}] 👤 USER QUERY: {q}")
        print("-" * 60)
        
        try:
            response = bot.process_message(
                user_id="test_user_01", 
                session_id="test_session_01", 
                message=q
            )
            
            print(f"🖥  AGENT RESPONSE:")
            print(f"   {response.get('answer', str(response))}")
            print(f"📡 SOURCE / ROUTE: {response.get('source', '')}")
            print(f"🎯 CONFIDENCE: {response.get('confidence', 'N/A')}")
        except Exception as e:
            print(f"❌ Execution Error: {e}")
            traceback.print_exc()
            
        print("=" * 60)

if __name__ == "__main__":
    test_pipeline()
