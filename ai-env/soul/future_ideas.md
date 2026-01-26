# Future Enhancement Ideas

## NLF - Natural Language First (Smart Prompting)
**Status**: Proposed
**Priority**: Medium

### Concept
When the planning agent detects complex work that could be delegated, it prompts the user:
> "This looks like a task for delegation. Should I add it to the board?"

### Benefits
- Low friction (no explicit "create task" command needed)
- Full user control (nothing happens without confirmation)
- Clean task board (no noise from small requests)

---

## Alternative Approaches to Explore

### 1. `/delegate` Command (Explicit Shortcut)
Instead of typing "create a task for...", you just prefix your request with `/delegate`:
```
/delegate Implement the dark mode toggle
```
**Pros**: Very clear intent, minimal typing
**Cons**: Still requires remembering the command

### 2. Session Handoff File
Instead of the full task queue, use a single `HANDOFF.md` file:
- Planning agent writes: "Next agent should do X, Y, Z"
- Execution agent reads this file at session start
**Pros**: Simpler than a full task queue
**Cons**: Only one task at a time, no status tracking

### 3. Task Tags in Chat
Use inline tags in your chat that agents recognize:
```
[DELEGATE] Implement feature X
[EXECUTE] Do this now
[PLAN] Think about this first
```
**Pros**: Very natural, inline with conversation
**Cons**: Requires training agents to recognize tags

### 4. Priority Queue with Auto-Assignment
Tasks are automatically assigned based on agent capabilities and current load.
**Pros**: Fully autonomous
**Cons**: Complex to implement, less control

---

## Current Recommendation
Stick with the **explicit task creation** for now. Then implement **NLF** as the first enhancement when the current system feels too manual.
