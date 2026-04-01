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


@app.delete("/api/agents/{agent_id}")
async def delete_agent(agent_id: str):
    from .db import get_db
    import shutil
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Remove from DB
    conn = get_db()
    conn.execute("DELETE FROM agents WHERE id=?", (agent_id,))
    conn.commit()
    conn.close()

    # Remove from executor map
    from .executor import AGENT_MODULE_MAP
    folder = AGENT_MODULE_MAP.pop(agent_id, None)

    # Delete agent folder from disk
    if folder:
        agent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agents", folder))
        if os.path.exists(agent_dir):
            shutil.rmtree(agent_dir)

    # Remove from ChromaDB
    try:
        from .search import get_collection
        get_collection().delete(ids=[agent_id])
    except Exception as e:
        print(f"[Search] Delete from index failed: {e}")

    return {"success": True, "deleted": agent_id}

@app.put("/api/agents/{agent_id}")
async def update_agent(agent_id: str, manifest: dict):
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    data = manifest.model_dump()
    data["id"] = agent_id
    from .db import get_db
    import json as _json
    conn = get_db()
    conn.execute("""
        UPDATE agents SET name=?, description=?, author=?, version=?, tags=?, 
        input_type=?, output_type=? WHERE id=?
    """, (
        data.get("name"), data.get("description"), data.get("author"),
        data.get("version"), _json.dumps(data.get("tags",[])),
        data.get("input",{}).get("type","text"),
        data.get("output",{}).get("type","text"),
        agent_id
    ))
    conn.commit()
    conn.close()
    return {"success": True, "agent": get_agent(agent_id)}


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


@app.get("/analytics", response_class=FileResponse)
async def serve_analytics():
    return FileResponse(os.path.join(FRONTEND_DIR, "analytics.html"))

@app.get("/api/analytics")
async def get_analytics():
    from .db import get_db
    conn = get_db()
    agents = conn.execute("SELECT id, name, trust_score, total_runs, successful_runs, avg_latency_ms FROM agents ORDER BY total_runs DESC").fetchall()
    total_runs = sum(a["total_runs"] or 0 for a in agents)
    total_agents = len(agents)
    avg_trust = sum(a["trust_score"] or 0 for a in agents) / max(total_agents, 1)
    conn.close()
    return {"total_agents": total_agents, "total_runs": total_runs, "avg_trust": round(avg_trust, 3), "agents": [dict(a) for a in agents]}


# ── Model upload routes — paste after /api/agents/fetch-github ──────

class ValidateModelRequest(BaseModel):
    model_b64: str
    scaler_b64: Optional[str] = None
    n_features: int
    task: str = "classification"
    feature_names: List[str] = []
    class_labels: List[str] = []
    test_input: Optional[str] = None

class SubmitWithModelRequest(BaseModel):
    manifest: dict
    model_b64: str
    scaler_b64: Optional[str] = None
    n_features: int
    task: str = "classification"
    feature_names: List[str] = []
    class_labels: List[str] = []

def _generate_agent_wrapper(folder_name: str, n_features: int, task: str,
                             feature_names: list, class_labels: list,
                             has_scaler: bool) -> str:
    feat_str = ', '.join(feature_names) if feature_names else ', '.join(f'f{i+1}' for i in range(n_features))
    labels_str = repr(class_labels) if class_labels else '[]'
    scaler_code = """
        import joblib as _jl2
        scaler = _jl2.load(os.path.join(agent_dir, 'scaler.pkl'))
        features = scaler.transform([features])[0].tolist()""" if has_scaler else ""

    return f'''#!/usr/bin/env python3
# Auto-generated by AgentForge — sklearn model wrapper
import sys
import os
import json
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')

def main():
    raw = sys.stdin.read().strip()
    if not raw:
        print("No input provided. Send comma-separated numbers: {feat_str}")
        return

    agent_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        # Parse input — accept comma-separated or JSON array
        if raw.startswith('['):
            features = json.loads(raw)
        else:
            features = [float(x.strip().split(':')[-1]) for x in raw.split(',')]
    except Exception as e:
        print(f"Input error: {{e}}")
        print(f"Expected {n_features} comma-separated numbers: {feat_str}")
        return

    if len(features) != {n_features}:
        print(f"Expected {n_features} features, got {{len(features)}}")
        print(f"Input format: {feat_str}")
        return

    try:
        import joblib as _jl
        model = _jl.load(os.path.join(agent_dir, 'model.pkl'))
        {scaler_code}
        result = model.predict([features])[0]
        task = "{task}"
        class_labels = {labels_str}

        print("=" * 36)
        print("  MODEL PREDICTION")
        print("=" * 36)
        feat_names = {repr(feature_names) if feature_names else [f"f{{i+1}}" for i in range(n_features)]}
        for name, val in zip(feat_names, features):
            print(f"  {{name:<20}} {{val}}")
        print()
        if task == "classification":
            label = class_labels[int(result)] if class_labels and int(result) < len(class_labels) else str(result)
            print(f"  Prediction  : {{label}}")
            try:
                proba = model.predict_proba([features])[0]
                if class_labels and len(class_labels) == len(proba):
                    print(f"  Confidence  : {{max(proba)*100:.1f}}%")
                    print()
                    print("  Class probabilities:")
                    for lbl, p in zip(class_labels, proba):
                        bar = "#" * int(p * 20)
                        print(f"    {{lbl:<16}} {{bar}} {{p*100:.1f}}%")
                else:
                    print(f"  Confidence  : {{max(proba)*100:.1f}}%")
            except Exception:
                pass
        else:
            print(f"  Prediction  : {{result:.4f}}")
        print("=" * 36)

    except Exception as e:
        print(f"Model error: {{e}}")

if __name__ == "__main__":
    main()
'''

@app.post("/api/agents/validate-model")
async def validate_model_upload(req: ValidateModelRequest):
    import base64, subprocess, sys, tempfile, time, os
    import json as _json

    # Decode and save model to temp dir
    tmpdir = tempfile.mkdtemp()
    try:
        model_path = os.path.join(tmpdir, "model.pkl")
        with open(model_path, "wb") as f:
            f.write(base64.b64decode(req.model_b64))

        if req.scaler_b64:
            scaler_path = os.path.join(tmpdir, "scaler.pkl")
            with open(scaler_path, "wb") as f:
                f.write(base64.b64decode(req.scaler_b64))

        # Generate wrapper agent
        wrapper = _generate_agent_wrapper(
            tmpdir, req.n_features, req.task,
            req.feature_names, req.class_labels,
            has_scaler=bool(req.scaler_b64)
        )
        agent_path = os.path.join(tmpdir, "agent.py")
        with open(agent_path, "w", encoding="utf-8") as f:
            f.write(wrapper)

        # Test input — dummy features
        test_input = req.test_input if req.test_input else ", ".join(["1.0"] * req.n_features)

        start = time.time()
        result = subprocess.run(
            [sys.executable, agent_path],
            input=test_input.encode("utf-8"),
            capture_output=True, timeout=60,
            env=os.environ.copy()
        )
        latency_ms = round((time.time() - start) * 1000)
        stdout = result.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n")
        stderr = result.stderr.decode("utf-8", errors="replace")

        if result.returncode != 0:
            return {"success": False, "error": stderr or "Model failed to run", "latency_ms": latency_ms}
        if not stdout.strip():
            return {"success": False, "error": "Model produced no output. Is sklearn installed?", "latency_ms": latency_ms}

        return {"success": True, "output": stdout, "latency_ms": latency_ms}

    except Exception as e:
        return {"success": False, "error": str(e), "latency_ms": 0}
    finally:
        import shutil
        try: shutil.rmtree(tmpdir)
        except: pass


@app.post("/api/agents/submit-with-model")
async def submit_with_model(req: SubmitWithModelRequest):
    import base64, subprocess, sys, tempfile, time, os
    import json as _json

    manifest = req.manifest
    agent_id = manifest.get("id") or manifest.get("name","agent").lower().replace(" ","-") + "-v1"
    manifest["id"] = agent_id
    folder_name = agent_id.replace("-","_").replace(".","_")
    agent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agents", folder_name))
    os.makedirs(agent_dir, exist_ok=True)

    # Save model
    with open(os.path.join(agent_dir, "model.pkl"), "wb") as f:
        f.write(base64.b64decode(req.model_b64))

    if req.scaler_b64:
        with open(os.path.join(agent_dir, "scaler.pkl"), "wb") as f:
            f.write(base64.b64decode(req.scaler_b64))

    # Generate + save wrapper
    wrapper = _generate_agent_wrapper(
        folder_name, req.n_features, req.task,
        req.feature_names, req.class_labels,
        has_scaler=bool(req.scaler_b64)
    )
    agent_py = os.path.join(agent_dir, "agent.py")
    with open(agent_py, "w", encoding="utf-8") as f:
        f.write(wrapper)

    # Final sandbox check
    test_input = ", ".join(["1.0"] * req.n_features)
    result = subprocess.run(
        [sys.executable, agent_py],
        input=test_input.encode("utf-8"),
        capture_output=True, timeout=20,
        env=os.environ.copy()
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise HTTPException(status_code=400, detail=f"Model failed sandbox: {stderr}")

    # Save manifest
    with open(os.path.join(agent_dir, "manifest.json"), "w") as f:
        _json.dump(manifest, f, indent=2)

    # Register
    from .executor import register_agent_module
    register_agent_module(agent_id, folder_name)

    agent = register_agent(manifest)
    try:
        tags = _json.dumps(manifest.get("tags", []))
        add_agent_to_index(agent_id, manifest.get("name",""), manifest.get("description",""), tags)
    except Exception as e:
        print(f"[Search] Index update failed: {e}")

    return {"success": True, "agent": agent}


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

    # ✅ FIX: use the proper registration function instead of mutating the imported dict
    from .executor import register_agent_module
    register_agent_module(agent_id, folder_name)

    # Register in registry + search index
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