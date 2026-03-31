#!/usr/bin/env python3
"""
Quick debug script - run with: python test_agents.py
"""
import subprocess, sys, os

AGENTS = {
    "summarizer-v1":     "agents/summarizer/agent.py",
    "code-explainer-v1": "agents/code_explainer/agent.py",
    "web-scraper-v1":    "agents/web_scraper/agent.py",
    "email-drafter-v1":  "agents/email_drafter/agent.py",
}

TEST_INPUT = "The Transformer architecture uses self-attention to process sequences in parallel. It was introduced in the paper Attention Is All You Need and has since become the foundation for models like GPT and BERT."

print("=" * 60)
print("AgentForge - Agent Debug Test")
print("=" * 60)

for agent_id, script_path in AGENTS.items():
    print(f"\n[TEST] {agent_id}")
    print(f"  script: {script_path}")

    if not os.path.exists(script_path):
        print(f"  ERROR: script not found!")
        continue

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            input=TEST_INPUT.encode("utf-8"),
            capture_output=True,
            timeout=20
        )
        stdout = result.stdout.decode("utf-8", errors="replace").strip()
        stderr = result.stderr.decode("utf-8", errors="replace").strip()

        print(f"  returncode: {result.returncode}")
        print(f"  stdout ({len(stdout)} chars): {stdout[:200]!r}")
        if stderr:
            print(f"  stderr: {stderr[:300]!r}")
        else:
            print(f"  stderr: (none)")

    except subprocess.TimeoutExpired:
        print(f"  ERROR: timed out after 20s")
    except Exception as e:
        print(f"  ERROR: {e}")

print("\n" + "=" * 60)
print("Done.")