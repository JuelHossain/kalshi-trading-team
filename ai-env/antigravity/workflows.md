# Antigravity - Operational Workflows

This document guides Antigravity on how to leverage the Sentient Alpha environment.

## Workflow: Skill Discovery
**Trigger**: Starting a new technical task.
1. List available skills: `ls .opencode/skills/`.
2. Read the `SKILL.md` of the most relevant skill.
3. Use the provided scripts in `scripts/` instead of writing custom logic.

## Workflow: Signal Audit
**Trigger**: Discrepancy between UI and Engine behavior.
1. Inspect Synapse signals: `python3 .opencode/skills/market-intel/scripts/inspect_signals.py`.
2. Compare with `ai-env/schemas/synapse_schema.md`.

## Workflow: Standard Handoff (Critical)
**Trigger**: Ending a session or task.
1. Run `/sync` workflow to update documentation.
2. Execute `./scripts/handoff.sh "Your message"` to push atomically.

---
_Operational Context for Antigravity_
