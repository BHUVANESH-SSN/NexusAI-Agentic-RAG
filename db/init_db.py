import os
import sqlite3
import logging

LOGGER = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "company.db")

def init_db():
    LOGGER.info("Initializing SQLite database at %s", DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create Employee Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        department TEXT NOT NULL,
        role TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL
    )
    """)

    # Create Violations Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS violations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        violation_type TEXT NOT NULL,
        date_reported DATE NOT NULL,
        severity TEXT NOT NULL,
        FOREIGN KEY(employee_id) REFERENCES employees(id)
    )
    """)

    # Create User Settings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)

    # Clear old data for idempotency
    cursor.execute("DELETE FROM violations")
    cursor.execute("DELETE FROM employees")

    # Insert Dummy Data
    employees = [
        ("Alice Smith", "HR", "Manager", "alice@company.com"),
        ("Bob Jones", "Engineering", "Developer", "bob@company.com"),
        ("Charlie Brown", "Sales", "Director", "charlie@company.com")
    ]
    cursor.executemany("INSERT INTO employees (name, department, role, email) VALUES (?, ?, ?, ?)", employees)

    violations = [
        (2, "Data Breach (UPSI)", "2026-03-15", "High"),
        (3, "Compliance Training Overdue", "2026-04-01", "Low")
    ]
    cursor.executemany("INSERT INTO violations (employee_id, violation_type, date_reported, severity) VALUES (?, ?, ?, ?)", violations)

    conn.commit()
    conn.close()
    LOGGER.info("Database initialized successfully.")

if __name__ == "__main__":
    init_db()
