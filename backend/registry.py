import json
import os
import uuid
from typing import List, Optional
from .db import get_db

MANIFESTS_DIR = os.path.join(os.path.dirname(__file__), "..", "manifests")
AGENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "agents")

def load_all_agents() -> List[dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM agents ORDER BY trust_score DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_agent(agent_id: str) -> Optional[dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def register_agent(manifest: dict) -> dict:
    agent_id = manifest.get("id", str(uuid.uuid4()))
    tags = json.dumps(manifest.get("tags", []))
    manifest_path = os.path.join(MANIFESTS_DIR, f"{agent_id}.json")
    os.makedirs(MANIFESTS_DIR, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    pricing = manifest.get("pricing", {})
    pricing_model = pricing.get("model", manifest.get("pricing_model", "free"))
    price_per_run = float(pricing.get("price_per_run", manifest.get("price_per_run", 0.0)))

    validation = manifest.get("validation", {})
    input_max_length = int(validation.get("max_length", manifest.get("input_max_length", 10000)))
    input_regex = validation.get("regex", manifest.get("input_regex", ""))
    input_format_hint = validation.get("format_hint", manifest.get("input_format_hint", ""))

    conn = get_db()
    conn.execute("""
        INSERT OR REPLACE INTO agents
        (id, name, description, author, version, tags, input_type, output_type, entry,
         manifest_path, trust_score, pricing_model, price_per_run,
         input_max_length, input_regex, input_format_hint, a2a_compatible)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (
        agent_id,
        manifest.get("name", "Unnamed Agent"),
        manifest.get("description", ""),
        manifest.get("author", "unknown"),
        manifest.get("version", "1.0"),
        tags,
        manifest.get("input", {}).get("type", "text"),
        manifest.get("output", {}).get("type", "text"),
        manifest.get("entry", "agent.py"),
        manifest_path,
        0.7,
        pricing_model,
        price_per_run,
        input_max_length,
        input_regex,
        input_format_hint,
    ))
    conn.commit()
    conn.close()
    return get_agent(agent_id)

def seed_demo_agents():
    demos = [
        {
            "id": "summarizer-v1",
            "name": "Text Summarizer",
            "description": "Summarizes long text into concise bullet-point highlights using LLM reasoning.",
            "author": "AgentForge",
            "version": "1.0",
            "tags": ["NLP", "text", "summarization", "highlights"],
            "input": {"type": "text", "max_length": 10000},
            "output": {"type": "text"},
            "entry": "agent.py",
            "pricing_model": "free",
            "price_per_run": 0.0,
        },
        {
            "id": "code-explainer-v1",
            "name": "Code Explainer",
            "description": "Takes any code snippet and explains what it does in plain English, line by line.",
            "author": "AgentForge",
            "version": "1.0",
            "tags": ["code", "explanation", "developer", "education"],
            "input": {"type": "text", "max_length": 5000},
            "output": {"type": "text"},
            "entry": "agent.py",
            "pricing_model": "free",
            "price_per_run": 0.0,
        },
        {
            "id": "web-scraper-v1",
            "name": "Web Scraper",
            "description": "Fetches a URL and extracts the main text content, stripping HTML and boilerplate.",
            "author": "AgentForge",
            "version": "1.0",
            "tags": ["web", "scraping", "extraction", "data"],
            "input": {"type": "url"},
            "output": {"type": "text"},
            "entry": "agent.py",
            "pricing_model": "free",
            "price_per_run": 0.0,
        },
        {
            "id": "email-drafter-v1",
            "name": "Email Drafter",
            "description": "Takes any text or summary and drafts a professional email around it with subject and body.",
            "author": "AgentForge",
            "version": "1.0",
            "tags": ["email", "writing", "professional", "communication"],
            "input": {"type": "text", "max_length": 5000},
            "output": {"type": "text"},
            "entry": "agent.py",
            "pricing_model": "free",
            "price_per_run": 0.0,
        },
    ]
    for d in demos:
        existing = get_agent(d["id"])
        if not existing:
            register_agent(d)
    print("[Registry] Demo agents seeded.")