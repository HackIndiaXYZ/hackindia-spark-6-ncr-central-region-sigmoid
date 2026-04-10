import asyncio
import concurrent.futures
import json
import os
import subprocess
import sys
import time
import uuid
from typing import AsyncGenerator, List
from .trust import log_execution

AGENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "agents")


AGENT_MODULE_MAP = {
    "summarizer-v1":       "summarizer",
    "code-explainer-v1":   "code_explainer",
    "web-scraper-v1":      "web_scraper",
    "email-drafter-v1":    "email_drafter",
    "password-checker-v1": "password_checker",
    "url-analyzer-v1":     "url_analyzer",
}

def _get_script(agent_id: str):
    """Resolve agent script path. Checks map first, then falls back to folder scan."""
    folder = AGENT_MODULE_MAP.get(agent_id)
    if folder:
        path = os.path.abspath(os.path.join(AGENTS_DIR, folder, "agent.py"))
        if os.path.exists(path):
            return path

    # Fallback: derive folder name from agent_id (hyphens/dots → underscores)
    derived = agent_id.replace("-", "_").replace(".", "_")
    path = os.path.abspath(os.path.join(AGENTS_DIR, derived, "agent.py"))
    if os.path.exists(path):
        AGENT_MODULE_MAP[agent_id] = derived  # cache it for next time
        return path

    return None

def register_agent_module(agent_id: str, folder_name: str):
    """Called by main.py after saving a new agent to disk. Updates the live map."""
    AGENT_MODULE_MAP[agent_id] = folder_name

def _blocking_run(script: str, input_text: str):
    env = os.environ.copy()
    start = time.time()
    result = subprocess.run(
        [sys.executable, script],
        input=input_text.encode("utf-8"),
        capture_output=True,
        timeout=30,
        env=env
    )
    latency_ms = (time.time() - start) * 1000
    stdout = result.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    stderr = result.stderr.decode("utf-8", errors="replace")
    return stdout, stderr, result.returncode == 0, latency_ms

async def _run_agent(agent_id: str, input_text: str):
    """Run agent in thread pool, returns (stdout, stderr, success, latency_ms)."""
    script = _get_script(agent_id)
    if not script:
        return "", f"Agent '{agent_id}' not found. It may not have been saved correctly.", False, 0
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, _blocking_run, script, input_text)

async def run_agent_subprocess(agent_id: str, input_text: str) -> AsyncGenerator[str, None]:
    stdout, stderr, success, latency_ms = await _run_agent(agent_id, input_text)
    if not success:
        yield f"[ERROR] {stderr or 'Unknown error'}\n"
    else:
        chunk_size = 80
        for i in range(0, len(stdout), chunk_size):
            yield stdout[i:i+chunk_size]
            await asyncio.sleep(0.01)
    log_execution("direct", agent_id, input_text, stdout, latency_ms, success, stderr)

async def run_pipeline_stream(agent_ids: List[str], initial_input: str) -> AsyncGenerator[str, None]:
    pipeline_id = str(uuid.uuid4())[:8]
    current_input = initial_input

    for i, agent_id in enumerate(agent_ids):
        step = i + 1
        yield f"data: {json.dumps({'type': 'step_start', 'step': step, 'agent_id': agent_id, 'total': len(agent_ids)})}\n\n"

        stdout, stderr, success, latency_ms = await _run_agent(agent_id, current_input)

        if not success:
            error_msg = stderr or "Unknown error"
            yield f"data: {json.dumps({'type': 'token', 'step': step, 'agent_id': agent_id, 'content': f'[ERROR] {error_msg}'})}\n\n"
            yield f"data: {json.dumps({'type': 'error', 'step': step, 'message': error_msg})}\n\n"
            return

        chunk_size = 80
        for j in range(0, len(stdout), chunk_size):
            chunk = stdout[j:j+chunk_size]
            yield f"data: {json.dumps({'type': 'token', 'step': step, 'agent_id': agent_id, 'content': chunk})}\n\n"
            await asyncio.sleep(0.01)

        log_execution(pipeline_id, agent_id, current_input, stdout, latency_ms, success, stderr)
        yield f"data: {json.dumps({'type': 'step_done', 'step': step, 'agent_id': agent_id, 'latency_ms': round(latency_ms)})}\n\n"
        yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        current_input = stdout

    yield f"data: {json.dumps({'type': 'pipeline_done', 'pipeline_id': pipeline_id})}\n\n"