# CROSS-AGENT PROTOCOL (Sentient Alpha)

This project is a multi-environment AI collaboration. Whether you are **Antigravity**, **Claude Code**, **OpenCode**, or **Gemini-CLI**, you must follow this protocol for consistency.

## 1. The Global Source of Truth
- **Universal Guidelines**: [AGENTS.md](./AGENTS.md) and [CONSTITUTION.md](./CONSTITUTION.md).
- **Technical "Toolbox"**: [ai-env/skills/](./ai-env/skills/) contains the official technical standards. (Linked via `.opencode/skills/`).
- **Operational Logic**: [ai-env/workflows/](./ai-env/workflows/) defines the runbooks. (Linked via `.agent/workflows/`).

### 1.1 Branch Hierarchy (Stay Linear)
- **`main`**: The "Gold Master". Only contains stable, walkthrough-verified evolutionary states.
- **`opencode`**: The designated AI workspace. All agents MUST perform their primary execution here.
- **`promotion`**: The act of merging `opencode` to `main` signifies the end of a Mission Phase.

## 2. Handoff Protocol (The Walkthrough)
Because the USER switches between environments, the **walkthrough** is the primary way we communicate state.
- **Rule**: Every time you finish a task, create or update a file in `walkthroughs/`.
- **Reason**: If Antigravity builds a feature, and the USER then opens Claude Code, Claude will read the latest walkthrough to understand exactly what was changed and why.

## 3. Environment Specifics
- **Antigravity**: Mirror [CONSTITUTION.md](./CONSTITUTION.md) into [.gemini/gemini.md](./.gemini/gemini.md).
- **OpenCode**: Context is standardized via symlinks to `ai-env/`.
- **Claude/General**: Use `CLAUDE.md` and `README.md` for environmental setup.

## 4. Signal Standardization
- **Synapse**: All persistent signals must be verified via `python3 .opencode/skills/market-intel/scripts/inspect_signals.py`.
- **Logic**: No hardcoding of personas. Load them from `.opencode/skills/agent-logic/resources/personas/`.

## 4. The Evolution Loop (MANDATORY)
Every change to logic, schema, or strategy is **incomplete** until session state is preserved:
- **Refactor**: If you change `engine/`, you MUST update the corresponding Skill in `ai-env/skills/`.
- **Strategy**: If you tune the Brain, you MUST update `ai-env/personas/`.
- **Soul Persistence**: Use `./scripts/handoff.sh` for every commit. This mandates a **Project Soul** snapshot in `ai-env/soul/identity.md`.
- **Token Hygiene**: Run `python3 ai-env/skills/sys-maintenance/scripts/compact_soul.py` if history exceeds 10 snapshots.

---
_Ratified for Cross-Agent Compliance_
