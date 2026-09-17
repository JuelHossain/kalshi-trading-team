---
description: Perform a full system health check (React + Python)
---

This workflow verifies the connectivity of the 2-tier architecture.

**Claude Code**: Use the `health-check` skill.

**Other Agents**:
1. Run diagnostic script:
```bash
python3 ai-env/skills/core-ops/scripts/health_check.py
```

2. If any service is offline, check the PM2 status:
```bash
npx pm2 status
```

## Dependencies

This workflow depends on:

- `engine/agents/base.py`
- `engine/agents/brain/`
- `engine/agents/gateway.py`
- `engine/agents/hand/`
- `engine/agents/senses/`
- *and 7 more files*

---

*Evolution Note [2026-01-29 20:34]: Auto-updated due to changes in related code.*
