---
name: task-delegation
description: Multi-agent task delegation protocol for seamless handoffs between planning and execution agents
---

## Overview
This skill enables AI agents to collaborate via a shared task queue without requiring the user to manually copy-paste task definitions or walkthroughs.

## Entry Protocol (MANDATORY)
Every agent should check the task board at the **start of each session**:
```bash
cat ai-env/tasks/BOARD.md
```
This gives instant visibility into what's pending, in progress, or awaiting verification.

## Task File Format
Tasks are stored in `ai-env/tasks/active/` with this template:
```yaml
---
id: TASK-XXX
title: Short description
status: PENDING | IN_PROGRESS | COMPLETED | VERIFIED
created_by: agent_name
assigned_to: null
created_at: YYYY-MM-DDTHH:MM:SSZ
completed_at: null
---

## Objective
[What the execution agent should accomplish]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Walkthrough (Filled by Execution Agent)
[Implementation details and proof of work]
```

## Workflows (Shortcuts)
- `/execute` - For execution agents to check and work on pending tasks.
- `/verify` - For planning agents to review completed tasks.

## Commands
```bash
# List all tasks
python3 ai-env/skills/task-delegation/scripts/task_manager.py list

# Create a new task
python3 ai-env/skills/task-delegation/scripts/task_manager.py create "Task Title"

# Claim a task
python3 ai-env/skills/task-delegation/scripts/task_manager.py claim TASK-001

# Complete a task
python3 ai-env/skills/task-delegation/scripts/task_manager.py complete TASK-001

# Verify a task
python3 ai-env/skills/task-delegation/scripts/task_manager.py verify TASK-001
```
