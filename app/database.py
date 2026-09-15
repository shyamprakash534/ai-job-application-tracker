import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "jobs.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            location TEXT,
            work_model TEXT,
            posting_date TEXT,
            source TEXT,
            url TEXT,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'FOUND',
            best_resume TEXT,
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
