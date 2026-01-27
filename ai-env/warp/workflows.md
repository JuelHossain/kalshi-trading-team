# Warp Agent - Operational Workflows

This document guides Warp on maintaining and operating the Sentient Alpha trading system.

## Core Philosophy
Warp operates as an **Agentic Development Environment** - combining terminal operations, code editing, and iterative problem-solving in a unified workflow.

## Workflow: System Initialization
**Trigger**: First-time setup or fresh clone.
1. Check environment: Verify Node.js, Python 3.12+, and git are available.
2. Install dependencies:
   ```bash
   npm install
   cd frontend && npm install && cd ..
   pip install -r engine/requirements.txt
   ```
3. Create `.env` file with required API keys (Gemini, Kalshi, Supabase).
4. Test startup: `npm run dev`

## Workflow: Platform Compatibility Fixes
**Trigger**: Errors related to OS-specific features (Windows/Unix differences).
1. Identify the incompatibility (e.g., signal handlers, file paths, encoding).
2. Add platform checks using `sys.platform` or equivalent.
3. Replace problematic characters (emojis) with ASCII alternatives.
4. Test on the target platform before committing.

## Workflow: Debug & Error Resolution
**Trigger**: Application crashes or errors during runtime.
1. Read error logs carefully - focus on stack traces and line numbers.
2. Use `read_files` to examine the problematic code.
3. Apply targeted fixes using `edit_files`.
4. Verify the fix by running the application.
5. Check for similar issues in other files using `grep`.

## Workflow: Development Cycle
**Trigger**: Making changes to the codebase.
1. Create a feature branch: `git checkout -b feature-name`
2. Make incremental changes with frequent testing.
3. Run validation:
   - Python: Check syntax with `python -m py_compile`
   - TypeScript: Run `npm run lint:frontend`
4. Commit with descriptive messages including co-author line.
5. Push to remote: `git push -u origin branch-name`

## Workflow: Git Operations
**Trigger**: Version control tasks.
1. Always check status first: `git status`
2. Use `--no-verify` flag when pre-commit hooks have unrelated failures.
3. Include co-author attribution: `Co-Authored-By: Warp <agent@warp.dev>`
4. Create PRs via provided GitHub links.

## Workflow: Testing & Validation
**Trigger**: After significant code changes.
1. Run unit tests: `pytest tests/unit/` (Python) or `npm test` (Frontend)
2. Verify personas: `python3 tests/verify_personas.py`
3. Check health: `python3 ai-env/skills/core-ops/scripts/health_check.py`
4. Monitor startup logs for errors.

## Workflow: Dependency Management
**Trigger**: Missing modules or package errors.
1. For Python: `pip install -r engine/requirements.txt`
2. For Node: `npm install` (root and frontend)
3. Verify installation by checking import errors.

## Workflow: Environment Configuration
**Trigger**: Missing or invalid API keys/configuration.
1. Check if `.env` exists in root directory.
2. Verify required variables:
   - `GEMINI_API_KEY`
   - `KALSHI_DEMO_KEY_ID` and `KALSHI_DEMO_PRIVATE_KEY`
   - `SUPABASE_URL` and `SUPABASE_KEY`
   - `IS_PRODUCTION` (default: false)
3. Never commit `.env` to version control.

## Workflow: Terminal Command Execution
**Trigger**: Running shell commands.
1. Use `run_shell_command` with appropriate parameters.
2. Set `is_risky: true` for commands that modify system state.
3. Provide clear `reason` in wait_params for output summarization.
4. For long-running processes, use `interact` mode with clear task instructions.

## Workflow: Code Analysis
**Trigger**: Understanding existing code or finding implementations.
1. Use `grep` for exact symbol/function searches.
2. Use `codebase_semantic_search` for conceptual searches.
3. Use `file_glob` for finding files by pattern.
4. Read files strategically - start with entry points and follow imports.

## Workflow: Multi-Agent Handoff
**Trigger**: Completing a task for another AI assistant to continue.
1. Update `ai-env/soul/identity.md` with a snapshot:
   - Current momentum (what's in progress)
   - Crucial logic (important findings)
   - Next move (what to do next)
2. Commit all changes with clear messages.
3. Push to remote branch.
4. Create documentation in `walkthroughs/` if it's a major change.

## Workflow: Cross-Platform Awareness
**Trigger**: Working on Windows vs Unix systems.
**Windows-specific considerations**:
- Use PowerShell commands (e.g., `Get-ChildItem`, `Test-Path`)
- Path separators: backslash `\`
- Signal handlers don't work (wrap in `sys.platform != "win32"` checks)
- Console encoding: cp1252 (avoid emojis, use ASCII)
- Line endings: CRLF (`\r\n`)

**Unix-specific considerations**:
- Use bash commands (e.g., `ls`, `cat`)
- Path separators: forward slash `/`
- Signal handlers available (SIGINT, SIGTERM)
- Console encoding: UTF-8 (emojis OK)
- Line endings: LF (`\n`)

## Integration Points
- **Skills**: Reference `ai-env/skills/` for reusable technical tools.
- **Workflows**: Common operations in `ai-env/workflows/`.
- **Schemas**: Data contracts in `ai-env/schemas/`.
- **Personas**: AI behavior models in `ai-env/personas/`.
- **Soul**: Project state/intuition in `ai-env/soul/identity.md`.

---
_Operational Context for Warp Agent_
