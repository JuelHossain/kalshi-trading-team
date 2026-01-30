---
name: agent-logic
description: Reasoning frameworks and personas for AI decision making
last_modified: 2026-01-29
---

## Overview
This skill defines the cognitive framework for the **Brain** agent. It contains the personas used in the Optimist vs Critic debate.

## Personas
- **Optimist**: Located in `ai-env/personas/optimist.md`. Focuses on positive Expected Value and news alignment.
- **Critic**: Located in `ai-env/personas/critic.md`. Focuses on variance, slippage, and liquidity risks.

## Decision Gate
A trade must pass the following checks within this skill's logic:
1. **Debate Consensus**: Judge finds the Optimist's case more compelling.
2. **Confidence**: Min 85%.
3. **Variance**: Max 0.25 in Monte Carlo simulation.

## Usage
Agents should load these personas when generating prompts for the Brain's Gemini cycle.

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
