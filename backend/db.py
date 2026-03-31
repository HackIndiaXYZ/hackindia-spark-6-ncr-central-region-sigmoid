import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "agentforge.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            author TEXT,
            version TEXT,
            tags TEXT,
            input_type TEXT,
            output_type TEXT,
            entry TEXT,
            manifest_path TEXT,
            trust_score REAL DEFAULT 0.5,
            total_runs INTEGER DEFAULT 0,
            successful_runs INTEGER DEFAULT 0,
            avg_latency_ms REAL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS execution_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pipeline_id TEXT,
            agent_id TEXT,
            input_preview TEXT,
            output_preview TEXT,
            latency_ms REAL,
            success INTEGER,
            error TEXT,
            executed_at TEXT DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS pipelines (
            id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            agent_chain TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Initialized agentforge.db")
