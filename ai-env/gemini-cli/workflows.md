# Gemini CLI / Antigravity - Operational Workflows

## Workflow: Persona Tuning
**Trigger**: Need to refine AI decision bias.
1. Edit target persona in `ai-env/personas/`.
2. Perform a "Brain Tap" to see the effect: `python3 engine/diagnostics/brain_tap.py`.
3. Verify via `tests/verify_personas.py`.

## Workflow: Signal Audit
**Trigger**: Unexplained trade behavior.
1. Inspect Synapse signals: `python3 ai-env/skills/market-intel/scripts/inspect_signals.py`.
2. Cross-check against news context in `ai-env/schemas/kalshi_v2.md`.

## Workflow: Ragnarok Initiation
**Trigger**: Security breach or fatal risk limit.
1. Locate hard-kill switch in `engine/core/safety.py`.
2. Execute liquidation.
3. Lock vault in `engine/core/vault.py`.

---
_Operational Context for Gemini CLI_
