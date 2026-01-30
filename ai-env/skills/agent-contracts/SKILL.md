---
name: agent-contracts
description: Agent Contract & Service Boundaries for clean inter-agent communication
last_modified: 2026-01-29
---

## Overview
This skill enforces the Agent Contract & Service Boundaries pillar, ensuring clean decoupled communication, persistence, and validation across all 4 Mega-Agents.

## Core Rules

### Persistence & Synapse
- **Data Handoff**: High-value data (Opportunities -> Signals -> Executions) must go through the **Synapse Persistent Queue** (SQLite).
- **Crash Recovery**: Agents must rely on Synapse to recover state and ensure no data loss during engine restarts.
- **Verification**: Inter-agent data must be queryable via the database for diagnostics.

### Decoupled I/O
- **Triggers**: Agents communicate via JSON on the `EventBus` for lightweight triggers (e.g., `CYCLE_START`, `EXECUTION_READY`).
- **Autopilot**: All agents must respect the **Autopilot Pulse** managed by the `SoulAgent`.
- **Forbidden**: Direct file mutation or global state modification outside your specific module.

### Runtime Validation
- **Schema**: Every published message or persisted record must pass Pydantic validation.
- **Failure**: Malformed data must trigger a `CRITICAL` log and cycle abortion to prevent faulty trading.
- **Logging**: Validation failures must be logged with the full payload context.

### Latency Budget
- **Critical Agents**: Senses and Brain must return data (or persist it) within 2.5s.
- **Async**: Use `asyncio` for all networking, database, and LLM calls.
- **Optimization**: Non-blocking I/O is strictly required; avoid time.sleep().

## Implementation
- EventBus for event triggers.
- Synapse (SQLite) for persistent data handoff.
- Pydantic for Python schema validation.
- SoulAgent as the executive pulse controller.

## Testing
- Verify data persistence in `ghost_memory.db` after a cycle.
- Ensure cycle aborts correctly on malformed Synapse records.
- Response times under 2.5s for critical paths.
- No direct state mutations between agents.

## Evolution Context
### Evolution Entry [2026-01-29 20:34]
- **Trigger**: Code changes detected
- **Files**: `engine/agents/base.py`, `engine/agents/brain.py`, `engine/agents/gateway.py`
- **Additional**: 2 more files


### Evolution Entry [2026-01-29 20:34]
- **Trigger**: Code changes detected
- **Files**: `engine/agents/base.py`, `engine/agents/brain.py`, `engine/agents/gateway.py`
- **Additional**: 2 more files


### Evolution Entry [2026-01-29 20:34]
- **Trigger**: Code changes detected
- **Files**: `engine/agents/base.py`, `engine/agents/brain.py`, `engine/agents/gateway.py`
- **Additional**: 2 more files


### Evolution Entry [2026-01-29 20:34]
- **Trigger**: Code changes detected
- **Files**: `engine/agents/base.py`, `engine/agents/brain.py`, `engine/agents/gateway.py`
- **Additional**: 2 more files
