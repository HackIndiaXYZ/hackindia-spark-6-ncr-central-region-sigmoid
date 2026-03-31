import json
import os
import sys
from contextlib import asynccontextmanager
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

from .db import init_db
from .registry import load_all_agents, get_agent, register_agent, seed_demo_agents
from .search import index_all_agents, semantic_search, add_agent_to_index
from .pipeline import validate_pipeline, build_execution_plan
from .executor import run_pipeline_stream, run_agent_subprocess
from .exporter import export_pipeline_json
from .trust import log_execution

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_demo_agents()
    try:
        index_all_agents()
    except Exception as e:
        print(f"[Search] ChromaDB indexing skipped: {e}")
    yield

app = FastAPI(
    title="AgentForge",
    description="Composable AI Agent Marketplace with Live Sandboxing — http://localhost:8080",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static frontend ──────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "static")), name="static")

@app.get("/", response_class=FileResponse)
async def serve_marketplace():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/builder", response_class=FileResponse)
async def serve_builder():
    return FileResponse(os.path.join(FRONTEND_DIR, "builder.html"))

@app.get("/submit", response_class=FileResponse)
async def serve_submit():
    return FileResponse(os.path.join(FRONTEND_DIR, "submit.html"))

# ── Agent registry ───────────────────────────────────────────────
@app.get("/api/agents")
async def list_agents():
    agents = load_all_agents()
    for a in agents:
        try:
            a["tags"] = json.loads(a["tags"]) if isinstance(a["tags"], str) else a["tags"]
        except Exception:
            a["tags"] = []
    return {"agents": agents, "count": len(agents)}

@app.get("/api/agents/{agent_id}")
async def agent_detail(agent_id: str):
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    try:
        agent["tags"] = json.loads(agent["tags"]) if isinstance(agent["tags"], str) else agent["tags"]
    except Exception:
        agent["tags"] = []
    return agent

class AgentManifest(BaseModel):
    id: Optional[str] = None
    name: str
    description: str
    author: str = "anonymous"
    version: str = "1.0"
    tags: List[str] = []
    input: dict = {"type": "text"}
    output: dict = {"type": "text"}
    entry: str = "agent.py"

@app.post("/api/agents/submit")
async def submit_agent(manifest: AgentManifest):
    data = manifest.model_dump()
    agent = register_agent(data)
    try:
        add_agent_to_index(agent["id"], agent["name"], agent["description"], agent.get("tags",""))
    except Exception as e:
        print(f"[Search] Index update failed: {e}")
    return {"success": True, "agent": agent}

# ── Search ───────────────────────────────────────────────────────
@app.get("/api/search")
async def search_agents(q: str, n: int = 5):
    if not q.strip():
        return {"agents": load_all_agents()[:n]}
    try:
        agents = semantic_search(q, n)
        for a in agents:
            try:
                a["tags"] = json.loads(a["tags"]) if isinstance(a["tags"], str) else a["tags"]
            except Exception:
                a["tags"] = []
        return {"agents": agents, "query": q}
    except Exception as e:
        print(f"[Search] Fallback to DB: {e}")
        all_agents = load_all_agents()
        q_lower = q.lower()
        filtered = [
            a for a in all_agents
            if q_lower in a.get("name","").lower()
            or q_lower in a.get("description","").lower()
            or q_lower in a.get("tags","").lower()
        ]
        return {"agents": filtered or all_agents[:5], "query": q}

# ── Pipeline ─────────────────────────────────────────────────────
class PipelineRequest(BaseModel):
    agent_ids: List[str]

@app.post("/api/pipeline/validate")
async def validate(req: PipelineRequest):
    result = validate_pipeline(req.agent_ids)
    return result

@app.post("/api/pipeline/plan")
async def get_plan(req: PipelineRequest):
    try:
        plan = build_execution_plan(req.agent_ids)
        return {"plan": plan}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

class RunRequest(BaseModel):
    agent_ids: List[str]
    input_text: str

@app.post("/api/pipeline/run")
async def run_pipeline(req: RunRequest):
    if not req.agent_ids:
        raise HTTPException(status_code=400, detail="No agents in pipeline")
    if not req.input_text.strip():
        raise HTTPException(status_code=400, detail="Input text is empty")

    async def event_stream():
        async for chunk in run_pipeline_stream(req.agent_ids, req.input_text):
            yield chunk

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

@app.post("/api/agent/run")
async def run_single_agent(req: RunRequest):
    if not req.agent_ids:
        raise HTTPException(status_code=400, detail="No agent specified")

    async def event_stream():
        async for chunk in run_agent_subprocess(req.agent_ids[0], req.input_text):
            import json as _json
            yield f"data: {_json.dumps({'type': 'token', 'content': chunk})}\n\n"
        yield f"data: {_json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"}
    )

# ── Export ───────────────────────────────────────────────────────
class ExportRequest(BaseModel):
    agent_ids: List[str]
    pipeline_name: str = "My Pipeline"

@app.post("/api/pipeline/export")
async def export_pipeline(req: ExportRequest):
    spec = export_pipeline_json(req.agent_ids, req.pipeline_name)
    return spec

# ── Stats / trust ────────────────────────────────────────────────
@app.get("/api/stats")
async def platform_stats():
    from .db import get_db
    conn = get_db()
    total_agents = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
    total_runs = conn.execute("SELECT SUM(total_runs) FROM agents").fetchone()[0] or 0
    top_agents = conn.execute(
        "SELECT id, name, trust_score, total_runs FROM agents ORDER BY trust_score DESC LIMIT 3"
    ).fetchall()
    conn.close()
    return {
        "total_agents": total_agents,
        "total_runs": total_runs,
        "top_agents": [dict(a) for a in top_agents]
    }

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "AgentForge"}

# ── Agent code submission + validation ───────────────────────────
class ValidateCodeRequest(BaseModel):
    code: str
    test_input: str = "Hello world. This is a test input."

class SubmitWithCodeRequest(BaseModel):
    manifest: dict
    code: str

class FetchGithubRequest(BaseModel):
    url: str

@app.post("/api/agents/validate-code")
async def validate_code(req: ValidateCodeRequest):
    """Sandbox-run submitted code, return result without saving."""
    import subprocess, sys, tempfile, time
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(req.code)
        tmp_path = f.name
    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            input=req.test_input.encode('utf-8'),
            capture_output=True, timeout=15
        )
        latency_ms = round((time.time() - start) * 1000)
        stdout = result.stdout.decode('utf-8', errors='replace').replace('\r\n','\n')
        stderr = result.stderr.decode('utf-8', errors='replace')
        if result.returncode != 0:
            return {"success": False, "error": stderr or "Non-zero exit code", "latency_ms": latency_ms}
        if not stdout.strip():
            return {"success": False, "error": "Agent produced no output. Make sure you print() something.", "latency_ms": latency_ms}
        return {"success": True, "output": stdout, "latency_ms": latency_ms}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Agent timed out after 15 seconds.", "latency_ms": 15000}
    except Exception as e:
        return {"success": False, "error": str(e), "latency_ms": 0}
    finally:
        try: os.unlink(tmp_path)
        except: pass

@app.post("/api/agents/submit-with-code")
async def submit_with_code(req: SubmitWithCodeRequest):
    """Validate code, save agent.py to disk, register manifest."""
    import subprocess, sys, tempfile, time
    code = req.code
    manifest = req.manifest

    # Re-validate in sandbox
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            input=b"Validation test input for final check.",
            capture_output=True, timeout=15
        )
        if result.returncode != 0:
            stderr = result.stderr.decode('utf-8', errors='replace')
            raise HTTPException(status_code=400, detail=f"Code failed sandbox: {stderr}")
        if not result.stdout.strip():
            raise HTTPException(status_code=400, detail="Agent produced no output.")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=400, detail="Agent timed out.")
    finally:
        try: os.unlink(tmp_path)
        except: pass

    # Determine agent folder name
    agent_id = manifest.get("id") or manifest.get("name","agent").lower().replace(" ","-") + "-v1"
    manifest["id"] = agent_id
    folder_name = agent_id.replace("-","_").replace(".","_")
    agent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agents", folder_name))
    os.makedirs(agent_dir, exist_ok=True)

    # Save agent.py
    agent_py_path = os.path.join(agent_dir, "agent.py")
    with open(agent_py_path, "w", encoding="utf-8") as f:
        f.write(code)

    # Save manifest.json
    import json as _json
    manifest_path = os.path.join(agent_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        _json.dump(manifest, f, indent=2)

    # Register in DB + update executor map dynamically
    from .executor import AGENT_MODULE_MAP
    AGENT_MODULE_MAP[agent_id] = folder_name

    # Register in registry
    agent = register_agent(manifest)
    try:
        tags = _json.dumps(manifest.get("tags", []))
        add_agent_to_index(agent_id, manifest.get("name",""), manifest.get("description",""), tags)
    except Exception as e:
        print(f"[Search] Index update failed: {e}")

    return {"success": True, "agent": agent}

@app.post("/api/agents/fetch-github")
async def fetch_github(req: FetchGithubRequest):
    """Fetch agent code from a raw GitHub URL."""
    import httpx
    url = req.url.strip()
    if not ("raw.githubusercontent.com" in url or "raw.github.com" in url):
        raise HTTPException(status_code=400, detail="Must be a raw.githubusercontent.com URL")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, headers={"User-Agent": "AgentForge/1.0"})
        if r.status_code != 200:
            return {"success": False, "error": f"HTTP {r.status_code} from GitHub"}
        code = r.text
        lines = len(code.splitlines())
        if lines > 500:
            return {"success": False, "error": "File too large (max 500 lines)"}
        return {"success": True, "code": code, "lines": lines}
    except Exception as e:
        return {"success": False, "error": str(e)}