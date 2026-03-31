import chromadb
import os
from .db import get_db

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "chroma")

_client = None
_collection = None

def get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
        _collection = _client.get_or_create_collection(
            name="agents",
            metadata={"hnsw:space": "cosine"}
        )
    return _collection

def index_all_agents():
    col = get_collection()
    conn = get_db()
    agents = conn.execute("SELECT id, name, description, tags FROM agents").fetchall()
    conn.close()

    if not agents:
        return

    ids, docs, metas = [], [], []
    existing_ids = set(col.get()["ids"])

    for a in agents:
        if a["id"] not in existing_ids:
            ids.append(a["id"])
            docs.append(f"{a['name']}. {a['description']} Tags: {a['tags']}")
            metas.append({"name": a["name"]})

    if ids:
        col.add(ids=ids, documents=docs, metadatas=metas)
        print(f"[Search] Indexed {len(ids)} agents.")

def semantic_search(query: str, n: int = 5):
    col = get_collection()
    try:
        results = col.query(query_texts=[query], n_results=min(n, col.count()))
        matched_ids = results["ids"][0] if results["ids"] else []

        conn = get_db()
        agents = []
        for aid in matched_ids:
            row = conn.execute("SELECT * FROM agents WHERE id = ?", (aid,)).fetchone()
            if row:
                agents.append(dict(row))
        conn.close()
        return agents
    except Exception as e:
        print(f"[Search] Error: {e}")
        return []

def add_agent_to_index(agent_id: str, name: str, description: str, tags: str):
    col = get_collection()
    existing = col.get(ids=[agent_id])
    if existing["ids"]:
        col.update(
            ids=[agent_id],
            documents=[f"{name}. {description} Tags: {tags}"],
            metadatas=[{"name": name}]
        )
    else:
        col.add(
            ids=[agent_id],
            documents=[f"{name}. {description} Tags: {tags}"],
            metadatas=[{"name": name}]
        )
