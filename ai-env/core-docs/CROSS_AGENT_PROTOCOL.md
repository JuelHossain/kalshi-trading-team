# CROSS-AGENT PROTOCOL (Sentient Alpha)

This project is a multi-environment AI collaboration. Whether you are **Antigravity**, **Claude Code**, **OpenCode**, or **Gemini-CLI**, you must follow this protocol for consistency.

## 1. The Global Source of Truth
- **Universal Guidelines**: [AGENTS.md](./AGENTS.md) and [CONSTITUTION.md](./CONSTITUTION.md).
- **Technical "Toolbox"**: The `.opencode/skills/` directory contains the official technical standards and diagnostic scripts. **Refer to these before implementing code.**
- **Architecture**: Always refer to [blueprint.md](./blueprint.md) to understand the 2-tier (React/Python) flow.

## 2. Handoff Protocol (The Walkthrough)
Because the USER switches between environments, the **walkthrough** is the primary way we communicate state.
- **Rule**: Every time you finish a task, create or update a file in `walkthroughs/`.
- **Reason**: If Antigravity builds a feature, and the USER then opens Claude Code, Claude will read the latest walkthrough to understand exactly what was changed and why.

## 3. Environment Specifics
- **Antigravity**: Mirror [CONSTITUTION.md](./CONSTITUTION.md) into [.gemini/gemini.md](./.gemini/gemini.md).
- **OpenCode**: All skills registered in [.opencode/skills/](./.opencode/skills/).
- **Claude/General**: Use `README.md` for environmental setup.

## 4. Signal Standardization
- **Synapse**: All persistent signals must be verified via `python3 .opencode/skills/market-intel/scripts/inspect_signals.py`.
- **Logic**: No hardcoding of personas. Load them from `.opencode/skills/agent-logic/resources/personas/`.

## 4. The Evolution Loop (MANDATORY)
Every change to logic, schema, or strategy is **incomplete** until documentation is synced:
- **Refactor**: If you change `engine/`, you MUST update the corresponding Skill in `.opencode/skills/`.
- **Strategy**: If you tune the Brain, you MUST update `ai-env/personas/`.
- **Workflow**: If you change the build/deploy process, you MUST update `CLAUDE.md` and `.agent/workflows/`.

---
_Ratified for Cross-Agent Compliance_
