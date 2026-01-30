# Hybrid Delegation Protocol

## Philosophy
Combine Claude Code's built-in Task tool (subagents) with BOARD.md persistence for automatic delegation.

## The Hybrid Workflow

### Step 1: Receive User Request
- User sends task
- Agent analyzes complexity
- **Agent decides**: Execute directly OR auto-delegate (no user choice step)

### Step 2: Automatic Hybrid Delegation
When task is non-trivial (3+ files, feature, complex):

1. **Create BOARD.md Task** (Persistence for cross-AI visibility)
   ```bash
   python3 ai-env/skills/task-delegation/scripts/task_manager.py create "Task Title"
   ```

2. **Launch Claude Code Subagent** (Execution via Task tool)
   ```python
   Task(
       prompt="""
       You are an Execution Agent. Your task: <TASK_DETAILS>

       CRITICAL INSTRUCTIONS:
       1. First, read ai-env/tasks/active/TASK-XXX.md
       2. Claim the task: python3 ai-env/skills/task-delegation/scripts/task_manager.py claim TASK-XXX
       3. Implement according to Acceptance Criteria
       4. Fill Walkthrough section in the task file
       5. Mark complete: python3 ai-env/skills/task-delegation/scripts/task_manager.py complete TASK-XXX
       6. Return a SUMMARY to the parent agent with:
          - What was implemented
          - Files modified
          - Key decisions made
          - Verification steps performed
       """,
       subagent_type="general-purpose",
       description="Execute TASK-XXX"
   )
   ```

3. **Background Collection** (Optional for non-blocking)
   ```python
   Task(
       ...,
       run_in_background=True
   )
   # Later: TaskOutput(task_id="...", block=True) to collect
   ```

### Step 3: Result Presentation
- Agent collects the subagent's result
- Presents to user with: Task ID, Summary, Files Changed
- Task is already in BOARD.md as COMPLETED

## Delegation Criteria (When to Auto-Delegate)

**Auto-delegate if ANY of these apply:**
- 3+ files affected
- Feature implementation (not just bug fix)
- Architectural decisions needed
- Multiple subsystems (frontend + backend)
- Testing infrastructure required
- Estimated time > 10 minutes

**Execute directly if ALL of these apply:**
- 1-2 files maximum
- Clear, straightforward change
- Simple bug fix
- No architectural decisions
- Estimated time < 5 minutes

**When unsure**: Delegate (safer default)

## Context Preservation Rules

Every subagent MUST:
1. Read `ai-env/tasks/BOARD.md` on start
2. Read `CLAUDE.md` for project context
3. Read `ai-env/soul/identity.md` for complex tasks
4. Update BOARD.md before returning
5. Return structured summary to parent agent

## Example Auto-Delegation

**You**: "Implement dark mode for the dashboard"

**Me**: This involves UI changes, state management, and theme system.
I'm delegating this to a specialist agent...

> 🚀 Delegating to specialist agent...

**[Background]**
> Execution Agent claims TASK-004
> Works on implementation
> Completes task
> Returns summary

**Me**: ✅ TASK-004 Complete!

> **Summary**: Implemented dark mode toggle in `Dashboard.tsx`, added theme provider in `App.tsx`, persisted preference to localStorage.
>
> **Files Modified**:
> - `frontend/src/components/Dashboard.tsx`
> - `frontend/src/App.tsx`
> - `frontend/src/hooks/useTheme.ts` (new)
>
> **Verification**: Toggle switches between light/dark, persists on reload.
>
> Task is now in COMPLETED section of BOARD.md awaiting your verification.

## Shortcut Commands

| Command | Action |
|---------|--------|
| `/status` | Show current BOARD.md state |
| `/verify` | Review completed tasks |

Note: `/delegate` and `/execute` shortcuts removed - delegation is now automatic based on task complexity.

## Key Changes from Original Protocol

**Removed:**
- ❌ "Execute now or Delegate?" question
- ❌ User decision bottleneck
- ❌ `/delegate` and `/execute` shortcuts

**Added:**
- ✅ Automatic delegation decision by agent
- ✅ Simple criteria for when to delegate
- ✅ Faster workflow (no waiting for user choice)

**Same:**
- ✅ Task tool usage for delegation
- ✅ BOARD.md persistence
- ✅ Result presentation format
- ✅ Context preservation rules
