# Claude Code - Operational Workflows

## Workflow: Logic Verification
**Trigger**: After modifying the Brain or Hand agents.
1. Run engine unit tests: `pytest tests/unit/`.
2. Run persona check: `python3 tests/verify_personas.py`.
3. If successful, record the change in a new `walkthroughs/` document.

## Workflow: Frontend Design
**Trigger**: Implementing a new HUD component.
1. Check `DESIGN_GUIDE.md` for Shadcn/Glassmorphism standards.
2. Verify Zustand store for state hooks.
3. Verify build: `cd frontend && npm run build`.

## Workflow: Error Recovery
**Trigger**: Service crash or SSE disconnect.
1. Run Health Check: `python3 ai-env/skills/core-ops/scripts/health_check.py`.
2. Check PM2 logs: `npx pm2 logs`.
3. Restart engine if Synapse is stalling.

---
_Operational Context for Claude Code_
