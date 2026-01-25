---
description: Synchronize project documentation and AI context files with recent code changes
---

This workflow automates the "Evolution Loop" required for cross-agent consistency.

1. **Scan**: Analyze recent Git commits and engine changes.
2. **Update**: Sync logic changes to:
   - `ai-env/personas/`
   - `ai-env/schemas/`
   - `.opencode/skills/` (Run `python3 ai-env/skills/sys-maintenance/scripts/sync_skills.py`)
3. **Verify**: Ensure context files (AGENTS.md, CLAUDE.md, GEMINI.md) are accurate and run `python3 ai-env/skills/sys-maintenance/scripts/compact_soul.py` if history is long.
4. **Log**: Record the sync in the `walkthroughs/` directory.
5. **Handoff**: Execute `./scripts/handoff.sh "chore(sync): update cross-agent context"` to finalize the session.
