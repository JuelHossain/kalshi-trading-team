# OpenCode - Operational Workflows

This document guides OpenCode on maintaining the project infrastructure.

## Workflow: Skill Augmentation
**Trigger**: Identifying a missing technical automation.
1. Create a new skill folder in `.opencode/skills/`.
2. Define a `SKILL.md` with frontmatter and instructions.
3. Add helper scripts to `scripts/`.

## Workflow: Workflow Sync
**Trigger**: Updating `/sync` or adding a new slash command.
1. Update `.agent/workflows/` markdown files.
2. Sync the changes to `ai-env/opencode/workflows.md`.

## Workflow: Persona Alignment
**Trigger**: Changes in agent behavior requirements.
1. Update definitions in `ai-env/personas/`.
2. Verify cross-platform impact via `tests/verify_personas.py`.

---
_Operational Context for OpenCode_
