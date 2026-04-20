import sqlite3
import os

db_path = '/home/bhuvi/Desktop/acer/PROJECTS/company-chatbot-langchain/db/company.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("DELETE FROM user_settings WHERE key='mysql_uri'")
conn.commit()
conn.close()
print("Successfully wiped corrupt mysql_uri!")
