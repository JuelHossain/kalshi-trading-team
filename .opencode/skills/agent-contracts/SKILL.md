---
name: agent-contracts
description: Agent Contract & Service Boundaries for clean inter-agent communication
---

## Overview
This skill enforces the Agent Contract & Service Boundaries pillar, ensuring clean decoupled communication and validation across all agents.

## Core Rules

### Decoupled I/O
- **Communication**: Agents communicate exclusively via JSON on the `EventBus`
- **Forbidden**: Direct file mutation or global state modification outside module
- **Pattern**: Publish/subscribe pattern for all inter-agent communication
- **Validation**: Event bus messages only

### Runtime Validation
- **Schema**: Every published message must pass Zod/Pydantic validation
- **Failure**: Malformed data triggers `CRITICAL` log and cycle abortion
- **Implementation**: Schema validation before publishing
- **Logging**: Validation failures logged with full context

### Latency Budget
- **Critical Agents**: Scout, Interceptor must return within 2.5s
- **Async**: Use `asyncio` for all networking and LLM calls
- **Monitoring**: Track response times and alert on violations
- **Optimization**: Non-blocking I/O required

## Implementation
- EventBus as central communication hub
- Schema validation libraries (Zod for TS, Pydantic for Python)
- Async/await for all I/O operations
- Response time monitoring

## Testing
- Schema validation rejects invalid messages
- Cycle aborts on malformed data
- Response times under 2.5s for critical paths
- No direct state mutations between agents