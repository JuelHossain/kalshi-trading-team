---
name: resilience
description: Resilience & Scalability practices for system reliability and efficiency
---

## Overview
This skill enforces the Resilience pillar, ensuring robust operation and seamless recovery via persistence.

## Core Rules

### Crash-Recovery & Persistence
- **Persistence**: High-value signals must be stored in **Synapse** (SQLite) to survive process crashes.
- **State Restoration**: Engine must restore active cycles from Synapse on startup.
- **Reliability**: No single point of failure in data handoff.

### Defensive API Usage
- **Backoff**: Implement exponential backoff for 429/500 errors in `KalshiClient`.
- **Hibernation**: Agents should stand down after repeated API failures to protect credentials.
- **Jitter**: Use random jitter in retry timers to avoid thundering herd.

### Alpha Efficiency
- **Native Math**: Use Numpy for simulation iterations.
- **LLM Optimization**: Gemini 1.5 Pro should only analyze "Finalist" opportunities.
- **Context Injection**: Senses must supply news context to maximize Brain's probability accuracy.

### Process Management
- **PM2**: Only two primary services (Frontend and Engine) via `ecosystem.config.cjs`.
- **Monitoring**: Use `brain_tap.py` for health diagnostics.
- **Standard**: All services must be managed and monitored via PM2.

## Implementation
- Synapse SQLite persistence.
- Exponential backoff with jitter.
- PM2 process orchestration.
- News-context aware Senses agent.

## Testing
- Kill engine during a cycle and verify Synapse recovers the state.
- Verify backoff triggers on rate limits.
- Confirm news context is attached to Brain prompts.