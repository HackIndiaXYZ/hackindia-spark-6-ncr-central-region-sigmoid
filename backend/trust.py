from .db import get_db

def log_execution(pipeline_id: str, agent_id: str, input_text: str,
                  output_text: str, latency_ms: float, success: bool, error: str = ""):
    conn = get_db()

    # Update trust score stats
    row = conn.execute(
        "SELECT total_runs, successful_runs, avg_latency_ms FROM agents WHERE id = ?",
        (agent_id,)
    ).fetchone()

    if row:
        total = (row["total_runs"] or 0) + 1
        successful = (row["successful_runs"] or 0) + (1 if success else 0)
        prev_avg = row["avg_latency_ms"] or 0
        new_avg = ((prev_avg * (total - 1)) + latency_ms) / total

        success_rate = successful / total
        latency_score = max(0, 1 - new_avg / 5000)
        volume_bonus = min(total / 100, 1.0) * 0.2
        trust = (success_rate * 0.5) + (latency_score * 0.3) + volume_bonus

        conn.execute("""
            UPDATE agents
            SET total_runs = ?, successful_runs = ?, avg_latency_ms = ?, trust_score = ?
            WHERE id = ?
        """, (total, successful, new_avg, trust, agent_id))

    # Write to execution_logs (keep last 100 per agent)
    conn.execute("""
        INSERT INTO execution_logs (agent_id, pipeline_id, input_text, output_text, latency_ms, success, error)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        agent_id, pipeline_id,
        (input_text or "")[:500],   # truncate for storage
        (output_text or "")[:1000],
        latency_ms,
        1 if success else 0,
        error[:200] if error else ""
    ))

    # Prune old logs — keep last 100 per agent
    conn.execute("""
        DELETE FROM execution_logs WHERE agent_id = ? AND id NOT IN (
            SELECT id FROM execution_logs WHERE agent_id = ?
            ORDER BY created_at DESC LIMIT 100
        )
    """, (agent_id, agent_id))

    conn.commit()
    conn.close()

def update_trust(agent_id: str):
    """Recalculate trust from scratch based on current stats."""
    conn = get_db()
    row = conn.execute(
        "SELECT total_runs, successful_runs, avg_latency_ms FROM agents WHERE id = ?",
        (agent_id,)
    ).fetchone()
    if row and row["total_runs"]:
        total = row["total_runs"]
        successful = row["successful_runs"] or total
        avg_lat = row["avg_latency_ms"] or 0
        success_rate = successful / total
        latency_score = max(0, 1 - avg_lat / 5000)
        volume_bonus = min(total / 100, 1.0) * 0.2
        trust = (success_rate * 0.5) + (latency_score * 0.3) + volume_bonus
        conn.execute("UPDATE agents SET trust_score = ? WHERE id = ?", (trust, agent_id))
        conn.commit()
    conn.close()