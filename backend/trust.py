from .db import get_db

def update_trust(agent_id: str, latency_ms: float, success: bool):
    conn = get_db()
    row = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
    if not row:
        conn.close()
        return

    total = row["total_runs"] + 1
    successful = row["successful_runs"] + (1 if success else 0)
    prev_avg = row["avg_latency_ms"] or 0
    new_avg = ((prev_avg * row["total_runs"]) + latency_ms) / total

    # Trust score formula:
    # 50% success rate, 30% latency score (lower = better), 20% volume bonus
    success_rate = successful / total
    latency_score = max(0, 1 - (new_avg / 5000))  # 5s = 0, 0ms = 1
    volume_bonus = min(total / 100, 1.0) * 0.2
    trust = (success_rate * 0.5) + (latency_score * 0.3) + volume_bonus

    conn.execute("""
        UPDATE agents SET
            total_runs = ?,
            successful_runs = ?,
            avg_latency_ms = ?,
            trust_score = ?
        WHERE id = ?
    """, (total, successful, new_avg, round(trust, 4), agent_id))
    conn.commit()
    conn.close()

def log_execution(pipeline_id: str, agent_id: str, input_text: str,
                  output_text: str, latency_ms: float, success: bool, error: str = ""):
    conn = get_db()
    conn.execute("""
        INSERT INTO execution_logs
        (pipeline_id, agent_id, input_preview, output_preview, latency_ms, success, error)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        pipeline_id,
        agent_id,
        input_text[:300],
        output_text[:300],
        latency_ms,
        1 if success else 0,
        error
    ))
    conn.commit()
    conn.close()
    update_trust(agent_id, latency_ms, success)
