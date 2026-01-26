# Task Board Protocol

This directory is the **shared workspace** for all AI agents. It eliminates manual copy-pasting between planning and execution sessions.

## 📋 How It Works

### For Planning Agents
1. Create a task file in `active/` with status `PENDING`.
2. The `BOARD.md` will be auto-updated.

### For Execution Agents
1. Check `BOARD.md` to see what's pending.
2. Claim a task, implement it, and run the completion command.
3. The task will move to `completed/` and the board updates.

### For Verification
1. Check `BOARD.md` for the `COMPLETED` section.
2. Read the walkthrough in the task file.
3. Mark as `VERIFIED` when satisfied.

## 📂 Structure
- `active/` - Tasks that are pending or in progress.
- `completed/` - Tasks that are done but awaiting verification.
- `BOARD.md` - The Kanban dashboard (auto-updated).

## 🚀 Commands
```bash
# List all tasks
python3 ai-env/skills/task-delegation/scripts/task_manager.py list

# Claim a task
python3 ai-env/skills/task-delegation/scripts/task_manager.py claim TASK-001

# Complete a task
python3 ai-env/skills/task-delegation/scripts/task_manager.py complete TASK-001

# Verify a task
python3 ai-env/skills/task-delegation/scripts/task_manager.py verify TASK-001
```

## ⚡ Workflows (Shortcuts)
Instead of typing commands, use these workflows:
- `/execute` - Check the board and work on pending tasks.
- `/verify` - Check the board and verify completed tasks.
