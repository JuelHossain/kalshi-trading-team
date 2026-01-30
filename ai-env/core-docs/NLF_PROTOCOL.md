# NLF - Natural Language First Protocol

## What is NLF?
NLF is a smart prompting protocol where AI agents **automatically delegate** non-trivial work to specialist subagents using Claude Code's Task tool, without asking the user for permission.

## Decision Tree: When to Delegate vs Execute Directly

```
USER REQUEST
    │
    ├─ Simple explanation/question?
    │  └─ YES → Answer directly
    │
    ├─ Code changes needed?
    │  └─ YES → Check complexity:
    │      │
    │      ├─ 1-2 files, simple bug fix?
    │      │  └─ YES → Execute directly
    │      │
    │      ├─ 3+ files OR feature OR complex?
    │      │  └─ YES → Auto-delegate via Task tool
    │      │
    │      └─ Unsure?
    │         └─ Delegate (safer)
    │
    └─ Documentation only?
       └─ Execute directly
```

## Auto-Delegate Criteria

**Auto-delegate if ANY of these apply:**
- 3 or more files affected
- Feature implementation (not just bug fix)
- Architectural decisions needed
- Multiple subsystems involved (frontend + backend)
- Testing infrastructure required
- Estimated time > 10 minutes

**Execute directly if ALL of these apply:**
- 1-2 files maximum
- Clear, straightforward change
- Simple bug fix
- No architectural decisions needed
- Estimated time < 5 minutes

## How to Respond (For Agents)

### When Delegating (Non-Trivial Tasks)

```
This involves [brief complexity explanation: file count, systems involved].
I'm delegating this to a specialist agent...

[Launch Task tool]

✅ [Task] complete!

**Summary**: [What was implemented]

**Files Modified**:
- [List files changed]

**Verification**: [What was tested]
```

### When Executing Directly (Trivial Tasks)

```
I'll handle this directly.

[Make changes]

✅ [Brief summary of change]
```

## Example Conversations

### Example 1: Simple Task (Direct Execution)

**User**: "Fix the typo in the dashboard header"

**Agent**: I'll fix that directly.

[Agent edits `frontend/src/components/Dashboard.tsx` line 42]

**Agent**: ✅ Fixed typo in Dashboard.tsx line 42.

---

### Example 2: Complex Task (Auto-Delegate)

**User**: "Implement dark mode for the dashboard"

**Agent**: This involves UI changes, state management, and theme system (5+ files).
I'm delegating this to a specialist agent...

[Agent launches Task tool with subagent]

**Agent**: ✅ Dark mode implementation complete!

**Summary**: Implemented dark mode toggle in `Dashboard.tsx`, added theme provider in `App.tsx`, persisted preference to localStorage.

**Files Modified**:
- `frontend/src/components/Dashboard.tsx`
- `frontend/src/App.tsx`
- `frontend/src/hooks/useTheme.ts` (new)

**Verification**: Toggle switches between light/dark, persists on reload.

---

### Example 3: Very Complex (Multi-System)

**User**: "Refactor the authentication module to use JWT tokens and add OAuth2 support"

**Agent**: This is a major refactoring involving multiple systems (engine auth, frontend login, state management).
I'm delegating this to a specialist agent...

[Agent launches Task tool]

**Agent**: ✅ Authentication refactoring complete!

**Summary**: Migrated to JWT tokens, added OAuth2 support, updated all API endpoints.

**Files Modified**:
- `engine/core/auth.py` (refactored)
- `frontend/src/store/useStore.ts` (token management)
- `frontend/src/components/Login.tsx` (OAuth2 flow)
- Plus 5 more files...

**Breaking Changes**: API endpoints now require Bearer token in Authorization header.

## Key Principles

1. **No User Choice Bottleneck**: Agent decides automatically based on complexity
2. **Transparent Communication**: Always inform user what's happening
3. **Smart Defaults**: When unsure, delegate (safer than blocking on user input)
4. **Fast Execution**: Simple tasks done immediately without overhead

## Edge Cases

### User Explicitly Requests Direct Execution
If user says "do this yourself" or "don't delegate", agent honors that preference.

### Delegation Failure
If Task tool fails or subagent errors, agent should:
1. Retry once with different approach
2. If still failing, inform user and offer to execute directly

### Trivial Requests
If task takes < 2 minutes (e.g., "what's this function do?"), just answer directly.
