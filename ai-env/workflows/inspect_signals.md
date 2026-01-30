---
description: Inspect the latest persistent trade signals in Synapse
---

This workflow allows you to see the "Thinking" output of the Brain agent stored in SQLite.

**Claude Code**: Use the `inspect-signals` skill.

**Other Agents**:
1. Run signal inspector:
```bash
python3 ai-env/skills/market-intel/scripts/inspect_signals.py
```

## Dependencies

This workflow depends on:

- `engine/agents/base.py`
- `engine/agents/brain.py`
- `engine/agents/gateway.py`
- `engine/agents/hand.py`
- `engine/agents/senses.py`
- *and 1 more files*

---

*Evolution Note [2026-01-29 20:34]: Auto-updated due to changes in related code.*
