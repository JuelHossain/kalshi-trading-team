# Task Board Protocol

This directory is the **shared workspace** for all AI agents. It eliminates manual copy-pasting between planning and execution sessions.

## 📋 How It Works

### For Claude Code
- **Task Tool**: Use the native Task tool for subagent delegation and complex multi-step work.
- **BOARD.md**: Read-only reference for cross-agent visibility.

### For Other AI Agents (Gemini, OpenCode, etc.)
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

## 🚀 Commands (For non-Claude agents)
```bash
# List all tasks
cat ai-env/tasks/BOARD.md

# Claim a task
# Edit the task file in active/, set status to IN_PROGRESS

# Complete a task
# Edit the task file, fill the Walkthrough section, move to completed/

# Verify a task
# Edit the task file, set status to VERIFIED
```

## ⚡ Claude Skills (Native)
Claude Code uses native skills defined in `.claude/skills/`:
- `health-check` - Full system diagnostics
- `inspect-signals` - View trade signals in Synapse
- `run-app` - Application control (dev/prod/status/stop)
- `sync-docs` - Documentation synchronization
- `git-handoff` - Atomic git commits with soul snapshot
