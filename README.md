# AgentForge

> Composable AI Agent Marketplace with Live Sandboxing

**HackIndia Spark 6 · NIT Delhi · April 2026**

---

## What It Does

AgentForge is a marketplace where developers publish AI agents and users compose them into live pipelines — without writing glue code.

**Three things that make it different:**
1. **Live sandbox execution** — agents actually run in isolated subprocesses, not just listed
2. **Pipeline composer** — chain agents visually; Agent A's output becomes Agent B's input
3. **Trust score system** — computed from latency, success rate, and run volume

---

## Quick Start

### 1. Clone and install

```bash
git clone <repo>
cd agentforge
pip install -r requirements.txt
```

### 2. Set your Groq API key (free at console.groq.com)

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 3. Run

```bash
python run.py
```

Open: http://localhost:8000

---

## Project Structure

```
agentforge/
├── backend/
│   ├── main.py          # FastAPI app + all API routes
│   ├── executor.py      # Subprocess sandbox + SSE streaming
│   ├── registry.py      # Agent CRUD + SQLite
│   ├── search.py        # ChromaDB semantic search
│   ├── trust.py         # Trust score engine
│   ├── pipeline.py      # Validation + scheduler
│   ├── exporter.py      # LangGraph export
│   └── db.py            # DB init + schema
├── agents/
│   ├── summarizer/      # Text summarization (Groq)
│   ├── code_explainer/  # Code → plain English (Groq)
│   ├── web_scraper/     # URL → extracted text
│   └── email_drafter/   # Text → professional email (Groq)
├── frontend/
│   ├── index.html       # Marketplace + agent cards
│   ├── builder.html     # Pipeline composer
│   └── submit.html      # Developer submission flow
├── data/                # SQLite + ChromaDB (auto-created)
├── manifests/           # Agent JSON manifests (auto-created)
└── run.py               # Entrypoint
```

---

## Agent Standard

Every agent is a Python script that:
- Reads input from `stdin`
- Writes output to `stdout`
- Declares a `manifest.json`

```python
#!/usr/bin/env python3
import sys

def main():
    input_text = sys.stdin.read().strip()
    # ... your logic ...
    print(result)

if __name__ == "__main__":
    main()
```

This makes any script composable in a pipeline.

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/agents` | GET | List all agents |
| `/api/agents/{id}` | GET | Agent detail |
| `/api/agents/submit` | POST | Register new agent |
| `/api/search?q=` | GET | Semantic agent search |
| `/api/pipeline/validate` | POST | Check pipeline compatibility |
| `/api/pipeline/run` | POST | Run pipeline (SSE stream) |
| `/api/pipeline/export` | POST | Export as LangGraph spec |
| `/api/agent/run` | POST | Run single agent (SSE) |
| `/api/stats` | GET | Platform stats |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + uvicorn |
| Streaming | Server-Sent Events (SSE) |
| Agent execution | asyncio subprocess sandbox |
| Semantic search | ChromaDB |
| LLM backbone | Groq (llama-3.1-8b-instant) |
| Storage | SQLite |
| Frontend | Vanilla HTML/CSS/JS |

All free tier. No Docker required.

---

## Demo Flow (5 minutes)

1. Open marketplace — 4 agents with trust scores
2. Search "summarize text" — semantic search finds Summarizer
3. Open Pipeline Builder — drag Summarizer → Email Drafter
4. Paste a long article, hit Run
5. Watch tokens stream: summary appears, then email draft
6. Click Export → download LangGraph JSON spec
7. Show trust score updating in real time

---

## Built By

Rehaan AK · Team Sigmoid · HackIndia Spark 6 · NIT Delhi 2026
