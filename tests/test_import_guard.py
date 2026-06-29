import subprocess
import sys
import os


def _run(code: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "MASTER_ENCRYPTION_KEY": "dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleTA=",
           "GROQ_API_KEY": "fake", "API_KEY": "x", "ADMIN_API_KEY": "x"}
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env,
                          cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_app_imports():
    r = _run("import app")
    assert r.returncode == 0, f"import app failed:\n{r.stderr}"


def test_all_agents_import():
    r = _run(
        "from agents.chatbot import EnterpriseChatbot; "
        "from agents.db_agent import DBAgent; "
        "from agents.tool_agent import ToolAgent; "
        "from agents.retriever_agent import RetrieverAgent; "
        "from agents.chat_agent import ChatAgent"
    )
    assert r.returncode == 0, f"agent import failed:\n{r.stderr}"
