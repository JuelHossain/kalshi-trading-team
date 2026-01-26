---
description: Check the task board and work on any pending tasks (for Execution Agents)
---

This workflow is for **Execution Agents**. When you start a session, run this to pick up delegated work.

// turbo
1. Read the task board to understand the current state:
```bash
cat ai-env/tasks/BOARD.md
```

2. For each task in the **PENDING** section:
   - Open the task file in `ai-env/tasks/active/`
   - Read the **Objective** and **Acceptance Criteria**
   - Claim the task by running:
   ```bash
   python3 ai-env/skills/task-delegation/scripts/task_manager.py claim <TASK-ID>
   ```

3. Implement the task according to the acceptance criteria.

4. When done, fill in the **Walkthrough** section of the task file with:
   - What you implemented
   - How you verified it
   - Any notes for the verifier

5. Mark the task as completed:
```bash
python3 ai-env/skills/task-delegation/scripts/task_manager.py complete <TASK-ID>
```

6. Notify the user that the task is ready for verification.
