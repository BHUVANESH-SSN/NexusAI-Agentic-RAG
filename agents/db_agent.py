import logging
import sqlite3

from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities import SQLDatabase

from llm.factory import get_chat_model, get_settings
from utils.encryption import decrypt_value

LOGGER = logging.getLogger(__name__)

FORBIDDEN_TABLES = {"user_settings"}

DB_PATH = None  # resolved lazily via settings so tests can override

def _get_db_path() -> str:
    return str(get_settings().db_path) if hasattr(get_settings(), "db_path") else \
        __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.dirname(__file__)), "db", "company.db")


def ensure_db():
    path = _get_db_path()
    if not __import__("os").path.exists(path):
        try:
            from db.init_db import init_db
            init_db()
        except ImportError:
            LOGGER.error("Cannot import init_db to seed the database.")


def _resolve_uri() -> str:
    settings = get_settings()
    # 1. Prefer settings-level read-only URI (set via ADMIN /settings route)
    if settings.db_readonly_uri:
        return settings.db_readonly_uri

    # 2. Try encrypted MySQL URI from user_settings table
    try:
        path = _get_db_path()
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM user_settings WHERE key='mysql_uri'")
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            uri = decrypt_value(row[0])
            if uri:
                LOGGER.info("DBAgent connecting to dynamic MySQL database.")
                return uri
    except Exception as e:
        LOGGER.error("Error fetching mysql_uri from settings: %s", e)

    # 3. SQLite read-only mode
    path = _get_db_path()
    return f"sqlite:///file:{path}?mode=ro&uri=true"


class DBAgent:
    def __init__(self):
        ensure_db()
        self.llm = get_chat_model()

        uri = _resolve_uri()
        try:
            self.db = SQLDatabase.from_uri(
                uri,
                ignore_tables=list(FORBIDDEN_TABLES),
            )
        except Exception:
            # read-only mode may not be available on all sqlite builds; fall back gracefully
            path = _get_db_path()
            self.db = SQLDatabase.from_uri(
                f"sqlite:///{path}",
                ignore_tables=list(FORBIDDEN_TABLES),
            )

        self.agent_executor = create_sql_agent(
            llm=self.llm,
            db=self.db,
            agent_type="tool-calling",
            verbose=False,
        )

    def run(self, message: str, history: str = "") -> dict:
        LOGGER.info("DB Agent executing query: %s", message[:120])
        try:
            res = self.agent_executor.invoke({"input": message})
            return {"answer": res["output"], "source": "company.db"}
        except Exception:
            LOGGER.exception("DB Agent failed.")
            return {
                "answer": "I couldn't fetch data from the database right now.",
                "source": "error",
            }
