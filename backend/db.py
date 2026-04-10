import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "agentforge.db")

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            author TEXT DEFAULT 'unknown',
            version TEXT DEFAULT '1.0',
            tags TEXT DEFAULT '[]',
            input_type TEXT DEFAULT 'text',
            output_type TEXT DEFAULT 'text',
            entry TEXT DEFAULT 'agent.py',
            manifest_path TEXT,
            trust_score REAL DEFAULT 0.7,
            total_runs INTEGER DEFAULT 0,
            successful_runs INTEGER DEFAULT 0,
            avg_latency_ms REAL DEFAULT 0,
            config TEXT DEFAULT '{}',
            pricing_model TEXT DEFAULT 'free',
            price_per_run REAL DEFAULT 0.0,
            input_max_length INTEGER DEFAULT 10000,
            input_regex TEXT DEFAULT '',
            input_format_hint TEXT DEFAULT '',
            a2a_compatible INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS execution_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            pipeline_id TEXT DEFAULT 'direct',
            input_text TEXT,
            output_text TEXT,
            latency_ms REAL DEFAULT 0,
            success INTEGER DEFAULT 1,
            error TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            version TEXT NOT NULL,
            file_path TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Run migrations for existing DBs
    migrations = [
        "ALTER TABLE agents ADD COLUMN config TEXT DEFAULT '{}'",
        "ALTER TABLE agents ADD COLUMN avg_latency_ms REAL DEFAULT 0",
        "ALTER TABLE agents ADD COLUMN successful_runs INTEGER DEFAULT 0",
        "ALTER TABLE agents ADD COLUMN pricing_model TEXT DEFAULT 'free'",
        "ALTER TABLE agents ADD COLUMN price_per_run REAL DEFAULT 0.0",
        "ALTER TABLE agents ADD COLUMN input_max_length INTEGER DEFAULT 10000",
        "ALTER TABLE agents ADD COLUMN input_regex TEXT DEFAULT ''",
        "ALTER TABLE agents ADD COLUMN input_format_hint TEXT DEFAULT ''",
        "ALTER TABLE agents ADD COLUMN a2a_compatible INTEGER DEFAULT 1",
        "ALTER TABLE agents ADD COLUMN created_at TEXT DEFAULT (datetime('now'))",
    ]
    for sql in migrations:
        try:
            conn.execute(sql)
        except Exception:
            pass

    conn.commit()
    conn.close()