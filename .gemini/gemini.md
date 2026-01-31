
## 🤖 Antigravity Delegation Protocol (Claude Code)
When a task is complex (3+ files or high-level feature), Antigravity acts as the **Architect**:
1.  **Analyze**: Break the request into logical, discrete chunks. **Conflict Prevention (Mutex)**: Assign specific files to specific chunks in `task.md`. No two active chunks can own the same file.
2.  **Plan**: Draft a `task.md` and `implementation_plan.md` in the brain directory.
3.  **Delegate**: Use `run_command` to invoke `claude` (Claude Code) in the terminal. **Operational Rule**: Use `--dangerously-skip-permissions` for headless execution to avoid blocking prompts.
4.  **Instruct**: Provide Claude with precise prompts. **Mandatory TDD**: Instruct Claude to write a reproduction script or test case *before* attempting the fix/feature.
5.  **Audit**: Review Claude's output and verify the sub-tasks are completed.
6.  **Evolution**: Actively manage the `.claude/` folder. **Skill Pruning**: Remove unused skills to maintain context hygiene. Generate new **skills**, **subagents**, and **hooks** based on project needs.
7.  **Lessons Learned**:
    *   **Mutex is Law**: Parallel agents MUST modify distinct files. Never allow two agents to touch `main.py` simultaneously.
    *   **Config Hygiene**: Verify `.claude/hooks.json` is valid before spawning agents to prevent "Settings Error" blocks.

## 🧱 The 4 Mega-Agents (Core Pillars)
*   **SOUL**: Executive Leader. Manages Autopilot Pulse and Evolution. **Mandatory AI Fallback**: Native Gemini -> OpenRouter.
*   **SENSES**: Market Observer. Real-time context retrieval via DuckDuckGo.
*   **BRAIN**: Cognitive Analyst. Multi-persona debate and Monte Carlo simulation. **Decoupled**: No direct Senses link.
*   **HAND**: Tactical Executioner. Ragnarok protocol and capital protection. **Decoupled**: No direct Brain link.

## 🛡️ Operational Laws (From Constitution)
*   **Git Protocol**: Always operate on the `opencode` branch. `git pull --rebase origin opencode` first.
*   **Safety**: If `veto: true` or `VaultState.isLocked`, terminate trade cycles.
*   **Persistence**: All handoffs must go through **Synapse** (SQLite). **Strict Decoupling**: Direct agent-to-agent references are forbidden.
*   **Safety (Error Box)**: GhostEngine monitors `Synapse.errors`. If entries exist, all cycles are halted until cleared.
*   **Communication**: Use `./scripts/handoff.sh "message"` for atomic document/git sync.

## 🖥️ Monitoring & Skills
*   **Sentient HUD**: [localhost:3000](http://localhost:3000)
*   **Specialized Skills**: Consult [ai-env/skills/](./ai-env/skills/) before refactoring core logic.
*   **Verification**: Run `python3 .opencode/skills/core-ops/scripts/health_check.py` to confirm port/service alignment.

---
_Constitution Ratified - Sentient Alpha Core (Antigravity Edition)_
