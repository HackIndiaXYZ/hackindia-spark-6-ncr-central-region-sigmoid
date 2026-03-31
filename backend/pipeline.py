from typing import List, Dict, Any
from .registry import get_agent

def validate_pipeline(agent_ids: List[str]) -> Dict[str, Any]:
    """
    Validates a pipeline of agent IDs:
    - All agents must exist
    - Output type of agent N must match input type of agent N+1
    Returns {"valid": bool, "errors": [...], "agents": [...]}
    """
    errors = []
    agents = []

    for aid in agent_ids:
        agent = get_agent(aid)
        if not agent:
            errors.append(f"Agent not found: {aid}")
        else:
            agents.append(agent)

    # Check I/O compatibility between chained agents
    for i in range(len(agents) - 1):
        out_type = agents[i].get("output_type", "text")
        in_type = agents[i + 1].get("input_type", "text")
        if out_type != in_type and in_type != "text":
            errors.append(
                f"Type mismatch: {agents[i]['name']} outputs '{out_type}' "
                f"but {agents[i+1]['name']} expects '{in_type}'"
            )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "agents": agents
    }

def build_execution_plan(agent_ids: List[str]) -> List[Dict]:
    """Returns ordered list of agents with their execution metadata."""
    result = validate_pipeline(agent_ids)
    if not result["valid"]:
        raise ValueError(f"Invalid pipeline: {result['errors']}")
    return [
        {
            "step": i + 1,
            "agent_id": a["id"],
            "agent_name": a["name"],
            "input_type": a["input_type"],
            "output_type": a["output_type"],
        }
        for i, a in enumerate(result["agents"])
    ]
