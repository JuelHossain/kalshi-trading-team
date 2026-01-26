# NLF - Natural Language First Protocol

## What is NLF?
NLF is a smart prompting protocol where AI agents **detect** when a request might be better handled by delegation, and **ask** the user before creating a task.

## When to Trigger NLF
Agents should suggest delegation when they detect:
1. **Complexity**: The request involves multiple files or systems.
2. **Time**: The work would take significant effort.
3. **Specialization**: Another agent might be better suited.
4. **User History**: The user has previously delegated similar work.

## How to Respond (For Agents)
When NLF triggers, respond with:

```
This looks like a task that could be delegated. Would you like me to:

1. **Execute now** - I'll implement this immediately.
2. **Delegate** - I'll add it to the task board for another agent.

Just say "execute" or "delegate" (or use `/delegate` for instant delegation).
```

## User Responses
| User Says | Agent Action |
|-----------|--------------|
| "execute" / "do it" / "now" | Implement immediately |
| "delegate" / "add to board" | Create task, confirm, wait for `/execute` |
| `/delegate` | Fast-track: Create task without asking |

## Integration with /delegate
- NLF is the **soft** approach (asks first)
- `/delegate` is the **hard** approach (instant creation)
- Both use the same task queue and BOARD.md

## Example Conversation

**User**: "We need to refactor the authentication module to use JWT tokens."

**Agent (NLF triggered)**:
> This looks like a significant refactoring task. Would you like me to:
> 1. **Execute now** - I'll start the refactor immediately.
> 2. **Delegate** - I'll add it to the task board for another agent.

**User**: "Delegate"

**Agent**:
> ✅ Created TASK-003: Refactor authentication module to use JWT tokens
> I've added the details to the task board. Open an Execution Agent and type `/execute` when ready.
