#!/usr/bin/env python3
"""
Task Manager - Multi-Agent Task Delegation System
Manages the task lifecycle: create, claim, complete, verify, reject
Auto-updates the BOARD.md dashboard after every operation.
"""

import os
import sys
import re
from datetime import datetime
from pathlib import Path

TASKS_DIR = Path("ai-env/tasks")
ACTIVE_DIR = TASKS_DIR / "active"
COMPLETED_DIR = TASKS_DIR / "completed"
BOARD_FILE = TASKS_DIR / "BOARD.md"

def get_next_task_id():
    """Generate the next task ID based on existing tasks."""
    existing = list(ACTIVE_DIR.glob("TASK-*.md")) + list(COMPLETED_DIR.glob("TASK-*.md"))
    if not existing:
        return "TASK-001"
    numbers = []
    for f in existing:
        match = re.search(r'TASK-(\d+)', f.name)
        if match:
            numbers.append(int(match.group(1)))
    return f"TASK-{max(numbers) + 1:03d}"

def update_board():
    """Regenerate the BOARD.md dashboard based on current task states."""
    pending = []
    in_progress = []
    completed = []
    
    for task_file in ACTIVE_DIR.glob("TASK-*.md"):
        content = task_file.read_text()
        title_match = re.search(r'title:\s*(.+)', content)
        status_match = re.search(r'status:\s*(\w+)', content)
        assigned_match = re.search(r'assigned_to:\s*(.+)', content)
        
        title = title_match.group(1).strip() if title_match else "Untitled"
        status = status_match.group(1).strip() if status_match else "PENDING"
        assigned = assigned_match.group(1).strip() if assigned_match else "null"
        
        task_id = task_file.stem
        entry = f"- [{task_id}](./active/{task_file.name}): {title}"
        if assigned and assigned != "null":
            entry += f" (assigned to: {assigned})"
        
        if status == "PENDING":
            pending.append(entry)
        elif status == "IN_PROGRESS":
            in_progress.append(entry)
    
    for task_file in COMPLETED_DIR.glob("TASK-*.md"):
        content = task_file.read_text()
        title_match = re.search(r'title:\s*(.+)', content)
        title = title_match.group(1).strip() if title_match else "Untitled"
        task_id = task_file.stem
        completed.append(f"- [{task_id}](./completed/{task_file.name}): {title} (walkthrough ready)")
    
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    board_content = f"""# Task Board | Last Updated: {now}

## 🔴 PENDING
{chr(10).join(pending) if pending else "*No pending tasks.*"}

## 🟡 IN_PROGRESS
{chr(10).join(in_progress) if in_progress else "*No tasks in progress.*"}

## 🟢 COMPLETED (Awaiting Verification)
{chr(10).join(completed) if completed else "*No completed tasks awaiting verification.*"}

## ✅ VERIFIED
*(Archived)*

---
*This board is auto-updated by the task_manager.py script.*
"""
    BOARD_FILE.write_text(board_content)
    print(f"✅ Board updated: {BOARD_FILE}")

def create_task(title: str):
    """Create a new task with PENDING status."""
    task_id = get_next_task_id()
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    content = f"""---
id: {task_id}
title: {title}
status: PENDING
created_by: planning_agent
assigned_to: null
created_at: {now}
completed_at: null
---

## Objective
[Define the objective here]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Walkthrough (Filled by Execution Agent)
*To be filled after implementation.*
"""
    task_file = ACTIVE_DIR / f"{task_id}.md"
    task_file.write_text(content)
    print(f"✅ Created task: {task_id} - {title}")
    print(f"   File: {task_file}")
    update_board()

def claim_task(task_id: str, agent_name: str = "execution_agent"):
    """Claim a task and set status to IN_PROGRESS."""
    task_file = ACTIVE_DIR / f"{task_id}.md"
    if not task_file.exists():
        print(f"❌ Task not found: {task_id}")
        return
    
    content = task_file.read_text()
    content = re.sub(r'status:\s*\w+', 'status: IN_PROGRESS', content)
    content = re.sub(r'assigned_to:\s*.+', f'assigned_to: {agent_name}', content)
    task_file.write_text(content)
    print(f"✅ Claimed task: {task_id} (assigned to: {agent_name})")
    update_board()

def complete_task(task_id: str):
    """Mark a task as COMPLETED and move to completed directory."""
    task_file = ACTIVE_DIR / f"{task_id}.md"
    if not task_file.exists():
        print(f"❌ Task not found in active: {task_id}")
        return
    
    content = task_file.read_text()
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    content = re.sub(r'status:\s*\w+', 'status: COMPLETED', content)
    content = re.sub(r'completed_at:\s*.+', f'completed_at: {now}', content)
    
    new_file = COMPLETED_DIR / f"{task_id}.md"
    new_file.write_text(content)
    task_file.unlink()
    
    print(f"✅ Completed task: {task_id}")
    print(f"   Moved to: {new_file}")
    update_board()

def verify_task(task_id: str):
    """Mark a task as VERIFIED (archive it)."""
    task_file = COMPLETED_DIR / f"{task_id}.md"
    if not task_file.exists():
        print(f"❌ Task not found in completed: {task_id}")
        return
    
    content = task_file.read_text()
    content = re.sub(r'status:\s*\w+', 'status: VERIFIED', content)
    task_file.write_text(content)
    print(f"✅ Verified task: {task_id}")
    update_board()

def reject_task(task_id: str):
    """Reject a task and move it back to active with PENDING status."""
    task_file = COMPLETED_DIR / f"{task_id}.md"
    if not task_file.exists():
        print(f"❌ Task not found in completed: {task_id}")
        return
    
    content = task_file.read_text()
    content = re.sub(r'status:\s*\w+', 'status: PENDING', content)
    content = re.sub(r'assigned_to:\s*.+', 'assigned_to: null', content)
    
    new_file = ACTIVE_DIR / f"{task_id}.md"
    new_file.write_text(content)
    task_file.unlink()
    
    print(f"🔄 Rejected task: {task_id} (moved back to active)")
    update_board()

def list_tasks(status_filter: str = None):
    """List all tasks, optionally filtered by status."""
    print("\n📋 TASK BOARD\n" + "="*40)
    
    all_tasks = list(ACTIVE_DIR.glob("TASK-*.md")) + list(COMPLETED_DIR.glob("TASK-*.md"))
    
    for task_file in sorted(all_tasks):
        content = task_file.read_text()
        title_match = re.search(r'title:\s*(.+)', content)
        status_match = re.search(r'status:\s*(\w+)', content)
        
        title = title_match.group(1).strip() if title_match else "Untitled"
        status = status_match.group(1).strip() if status_match else "UNKNOWN"
        
        if status_filter and status.upper() != status_filter.upper():
            continue
        
        status_icon = {"PENDING": "🔴", "IN_PROGRESS": "🟡", "COMPLETED": "🟢", "VERIFIED": "✅"}.get(status, "⚪")
        print(f"{status_icon} [{task_file.stem}] {title}")
    
    print("="*40)

def main():
    if len(sys.argv) < 2:
        print("Usage: task_manager.py <command> [args]")
        print("Commands: list, create, claim, complete, verify, reject")
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        status_filter = sys.argv[2] if len(sys.argv) > 2 else None
        list_tasks(status_filter)
    elif command == "create":
        if len(sys.argv) < 3:
            print("Usage: task_manager.py create 'Task Title'")
            return
        create_task(sys.argv[2])
    elif command == "claim":
        if len(sys.argv) < 3:
            print("Usage: task_manager.py claim TASK-001")
            return
        agent = sys.argv[3] if len(sys.argv) > 3 else "execution_agent"
        claim_task(sys.argv[2], agent)
    elif command == "complete":
        if len(sys.argv) < 3:
            print("Usage: task_manager.py complete TASK-001")
            return
        complete_task(sys.argv[2])
    elif command == "verify":
        if len(sys.argv) < 3:
            print("Usage: task_manager.py verify TASK-001")
            return
        verify_task(sys.argv[2])
    elif command == "reject":
        if len(sys.argv) < 3:
            print("Usage: task_manager.py reject TASK-001")
            return
        reject_task(sys.argv[2])
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
