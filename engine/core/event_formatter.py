"""
Event formatters for SSE streaming.
Consolidates formatting logic from main.py and gateway.py.
"""

import uuid
from datetime import datetime

# ==============================================================================
# EVENT FORMATTING
# ==============================================================================

def format_log_event(
    payload: dict,
    cycle_count: int,
    agent_to_phase: dict[int, int]
) -> dict:
    """
    Format a SYSTEM_LOG event for SSE streaming.

    Args:
        payload: Original log payload
        cycle_count: Current cycle ID
        agent_to_phase: Mapping of agent IDs to phase IDs

    Returns:
        Formatted event dict for SSE
    """
    agent_id = payload.get("agent_id", 1)
    phase_id = agent_to_phase.get(agent_id, 1)

    return {
        "type": "LOG",
        "log": {
            "id": f"log-{datetime.now().timestamp()}-{uuid.uuid4().hex[:8]}",
            "timestamp": payload.get("timestamp", datetime.now().isoformat()),
            "agentId": agent_id,
            "cycleId": cycle_count,
            "phaseId": phase_id,
            "message": payload.get("message", ""),
            "level": payload.get("level", "INFO"),
        },
    }


def format_vault_event(payload: dict) -> dict:
    """
    Format a VAULT_UPDATE event for SSE streaming.

    Args:
        payload: Vault state payload

    Returns:
        Formatted event dict for SSE
    """
    return {
        "type": "VAULT",
        "state": payload
    }


def format_simulation_event(payload: dict) -> dict:
    """
    Format a SIM_RESULT event for SSE streaming.

    Args:
        payload: Simulation result payload

    Returns:
        Formatted event dict for SSE
    """
    return {
        "type": "SIMULATION",
        "state": payload
    }


def format_state_event(payload: dict) -> dict:
    """
    Format a SYSTEM_STATE event for SSE streaming.

    Args:
        payload: State payload

    Returns:
        Formatted event dict for SSE
    """
    return {
        "type": "STATE",
        "state": payload
    }


def format_error_event(
    payload: dict,
    cycle_count: int,
    agent_to_phase: dict[int, int],
    agent_name_to_id: dict[str, int]
) -> dict:
    """
    Format a SYSTEM_ERROR event for SSE streaming.

    Args:
        payload: Error payload
        cycle_count: Current cycle ID
        agent_to_phase: Mapping of agent IDs to phase IDs
        agent_name_to_id: Mapping of agent names to IDs

    Returns:
        Formatted event dict for SSE
    """
    agent_name = payload.get("agent_name", "")
    agent_id = agent_name_to_id.get(agent_name, 1)
    phase_id = agent_to_phase.get(agent_id, 1)

    return {
        "type": "ERROR",
        "error": {
            "id": f"error-{datetime.now().timestamp()}-{uuid.uuid4().hex[:8]}",
            "timestamp": payload.get("timestamp", datetime.now().isoformat()),
            "agentId": agent_id,
            "cycleId": cycle_count,
            "phaseId": phase_id,
            "code": payload.get("code", "UNKNOWN_ERROR"),
            "message": payload.get("message", "An error occurred"),
            "severity": payload.get("severity", "MEDIUM"),
            "domain": payload.get("domain", "SYSTEM"),
            "hint": payload.get("hint", ""),
            "context": payload.get("context", {}),
        }
    }


def format_gateway_log_event(
    payload: dict,
    cycle_count: int,
    agent_to_phase: dict[int, int]
) -> dict:
    """
    Format a log event for Gateway (slightly different structure).

    Args:
        payload: Original log payload
        cycle_count: Current cycle ID
        agent_to_phase: Mapping of agent IDs to phase IDs

    Returns:
        Formatted event dict for SSE
    """
    sender = payload.get("agent_name")
    agent_id = payload.get("agent_id", 0)
    phase_id = agent_to_phase.get(agent_id, 0)

    return {
        "id": f"log-{datetime.now().timestamp()}",
        "timestamp": payload.get("timestamp", datetime.now().isoformat()),
        "agentId": agent_id,
        "cycleId": cycle_count,
        "phaseId": phase_id,
        "level": payload.get("level", "INFO"),
        "message": payload.get("message", ""),
    }
