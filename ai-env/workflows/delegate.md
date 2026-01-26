---
description: Create a delegated task for another agent to execute (fast-track, no confirmation)
---

Use this workflow when you want to **instantly** create a task for another agent.

// turbo
1. Parse the user's request after `/delegate`:
   - Extract the task title and any details provided

2. Create the task file:
```bash
python3 ai-env/skills/task-delegation/scripts/task_manager.py create "TASK_TITLE_HERE"
```

3. Open the created task file in `ai-env/tasks/active/` and fill in:
   - **Objective**: What the execution agent should accomplish
   - **Acceptance Criteria**: How to verify success

4. Update the board and confirm to the user:
   - Show the task ID
   - Remind them to open an Execution Agent and type `/execute`

## Example
User says: `/delegate Implement dark mode toggle for the dashboard`

Agent responds:
> ✅ Created TASK-002: Implement dark mode toggle for the dashboard
> 
> I've added the objective and acceptance criteria. When you're ready, open another agent and type `/execute` to have it pick up this task.
