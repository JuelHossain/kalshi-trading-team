---
description: Check the task board and verify any completed tasks (for Planning Agents)
---

This workflow is for **Planning Agents**. Use this to verify work done by execution agents.

// turbo
1. Read the task board to see completed work:
```bash
cat ai-env/tasks/BOARD.md
```

2. For each task in the **COMPLETED** section:
   - Open the task file in `ai-env/tasks/completed/`
   - Read the **Walkthrough** section added by the execution agent
   - Verify that the acceptance criteria are met

3. If verification passes:
```bash
python3 ai-env/skills/task-delegation/scripts/task_manager.py verify <TASK-ID>
```

4. If verification fails, add comments to the task file and move it back to active:
```bash
python3 ai-env/skills/task-delegation/scripts/task_manager.py reject <TASK-ID>
```

5. The task board will be auto-updated with the new status.
