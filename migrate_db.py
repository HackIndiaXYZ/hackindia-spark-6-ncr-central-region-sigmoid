"""
Run this ONCE from your project root to add new columns to the existing DB.
Usage: python migrate_db.py
"""
import sqlite3
import os

db_path = os.path.join("data", "agentforge.db")
if not os.path.exists(db_path):
    print("DB not found — it will be created fresh on next run.py start. No migration needed.")
    exit(0)

conn = sqlite3.connect(db_path)

migrations = [
    "ALTER TABLE agents ADD COLUMN config TEXT DEFAULT '{}'",
    "ALTER TABLE agents ADD COLUMN avg_latency_ms REAL DEFAULT 0",
    "ALTER TABLE agents ADD COLUMN successful_runs INTEGER DEFAULT 0",
]

for sql in migrations:
    try:
        conn.execute(sql)
        print(f"✓ {sql}")
    except Exception as e:
        print(f"- Skipped (already exists): {sql.split('ADD COLUMN')[1].strip().split()[0]}")

# Fix trust default — bump existing agents from 0.5 to 0.7 if they have 0 runs
conn.execute("UPDATE agents SET trust_score = 0.7 WHERE trust_score = 0.5 AND total_runs = 0")
print("✓ Trust scores updated to 0.7 for unrun agents")

conn.commit()
conn.close()
print("\nMigration complete.")
