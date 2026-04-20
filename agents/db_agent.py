import os
import logging
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities import SQLDatabase
from llm.factory import get_chat_model
from utils.encryption import decrypt_value
import sqlite3

LOGGER = logging.getLogger(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db", "company.db")

def ensure_db():
    if not os.path.exists(DB_PATH):
        try:
            from db.init_db import init_db
            init_db()
        except ImportError:
            LOGGER.error("Cannot import init_db to seed the database.")

class DBAgent:
    def _get_mysql_uri(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM user_settings WHERE key='mysql_uri'")
            row = cursor.fetchone()
            conn.close()
            if row and row[0]:
                return decrypt_value(row[0])
        except Exception as e:
            LOGGER.error(f"Error fetching mysql_uri from settings: {e}")
        return None

    def __init__(self):
        ensure_db()
        self.llm = get_chat_model()
        
        mysql_uri = self._get_mysql_uri()
        if mysql_uri:
            LOGGER.info("DBAgent connecting to dynamic MySQL database.")
            self.db = SQLDatabase.from_uri(mysql_uri)
        else:
            LOGGER.warning("No dynamic MySQL URI found. Falling back to local SQLite.")
            self.db = SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")

        self.agent_executor = create_sql_agent(
            llm=self.llm,
            db=self.db,
            agent_type="tool-calling",
            verbose=True
        )

    def run(self, message: str, history: str = "") -> dict:
        LOGGER.info("DB Agent executing query: %s", message)
        try:
            # We attempt standard invoke
            res = self.agent_executor.invoke({"input": message})
            return {
                "answer": res["output"],
                "source": "company.db"
            }
        except Exception as e:
            LOGGER.exception("DB Agent failed.")
            return {"answer": f"I couldn't fetch data from the database. Error: {str(e)}", "source": "error"}
