---
trigger: always_on
---

always follow this documentation if you don't know what to do: https://code.claude.com/docs.
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
