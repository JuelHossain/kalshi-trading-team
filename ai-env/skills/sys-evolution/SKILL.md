# Skill: System Evolution (Self-Healing)
---
description: Autonomous generation and maintenance of project skills.
last_modified: 2026-01-29
---

This skill enables AI assistants to extend the technical capabilities of Sentient Alpha by creating new skills in `ai-env/skills/`.

## 🛠️ Usage
1. Identify a repeatable technical task or logic pattern.
2. Run `python3 scripts/create_skill.py "skill-name" "description"` (to be implemented).
3. The script will generate a compliant `SKILL.md` and folder structure.

## 📜 Standard Template
Every skill MUST follow the structure defined in [SKILL_TEMPLATE.md](./scripts/SKILL_TEMPLATE.md).

## 🛡️ Safety Guardrails
- NEVER modify existing core skills (`git-workflow`, `sys-maintenance`) without explicit user review.
- Always sync new skills to the root `ai-env/skills/` via symlink protocol.

## Evolution Context
### Evolution Entry [2026-01-29 20:34]
- **Trigger**: Code changes detected
- **Files**: `.claude/skills/test-generator/scripts/generate_test.py`, `ai-env/skills/task-delegation/scripts/task_manager.py`, `scripts/evolution/README.md`
- **Additional**: 21 more files


### Evolution Entry [2026-01-29 20:34]
- **Trigger**: Code changes detected
- **Files**: `.claude/skills/test-generator/scripts/generate_test.py`, `ai-env/skills/task-delegation/scripts/task_manager.py`, `scripts/evolution/README.md`
- **Additional**: 21 more files


### Evolution Entry [2026-01-29 20:34]
- **Trigger**: Code changes detected
- **Files**: `.claude/skills/test-generator/scripts/generate_test.py`, `ai-env/skills/task-delegation/scripts/task_manager.py`, `scripts/evolution/README.md`
- **Additional**: 21 more files


### Evolution Entry [2026-01-29 20:34]
- **Trigger**: Code changes detected
- **Files**: `.claude/skills/test-generator/scripts/generate_test.py`, `ai-env/skills/task-delegation/scripts/task_manager.py`, `scripts/evolution/README.md`
- **Additional**: 21 more files
