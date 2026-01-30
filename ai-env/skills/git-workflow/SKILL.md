---
name: git-workflow
description: Engineering & Git Workflow practices for version control and development
last_modified: 2026-01-29
---

## Overview
This skill enforces the Engineering & Git Workflow pillar, ensuring clean version control and proper development practices.

## Core Rules

### Git Protocol
- **Branching**: Never commit directly to `main`
- **Working Branch**: Always work on the `opencode` branch
- **Merging**: Use PRs or direct merges from feature branches
- **Protection**: Main branch protected from direct pushes

### Clean History
- **Pull First**: Always pull with `rebase` (`git pull --rebase`) at the start of every AI session.
- **Rebasing**: Use `rebase` to keep history linear and clean for LLM scroll-back.
- **Atomic Handoff**: Group code changes and Skill/Workflows (`/sync`) into a single atomic commit.
- **Knowledge Bridge**: Update `.opencode/` and `ai-env/` folders to "enrich" the project for the next agent.
- **Conflicts**: Resolve locally via rebase.

### Atomic Refactoring
- **Commits**: Must be testable units with conventional titles
- **Titles**: Use `feat:`, `fix:`, `refactor:`, `docs:`, `style:`, `test:`
- **Scope**: Commits should affect one concern
- **Testing**: Each commit should pass tests

### Deployment Lifecycle
- **Build**: Always build after changes
- **Deploy**: Deploy to show UI changes
- **Verification**: Manual testing before marking complete
- **Rollback**: Ability to revert if issues found

### Verification
- **Testing**: Thorough testing (build/deploy/UI check)
- **Completion**: Only mark done after verification
- **Regression**: Ensure no existing functionality broken
- **Documentation**: Update docs for changes

## Implementation
- Pre-commit hooks for conventional commits
- Branch protection rules
- CI/CD for build verification
- Automated testing pipelines

## Testing
- Commits follow conventional format
- Main branch never receives direct commits
- Conflicts resolved before push
- All changes tested and deployed

## Evolution Context
### Evolution Entry [2026-01-29 20:34]
- **Trigger**: Code changes detected
- **Files**: `ai-env/workflows/delegate.md`, `ai-env/workflows/execute.md`, `ai-env/workflows/health.md`
- **Additional**: 4 more files


### Evolution Entry [2026-01-29 20:34]
- **Trigger**: Code changes detected
- **Files**: `ai-env/workflows/delegate.md`, `ai-env/workflows/execute.md`, `ai-env/workflows/health.md`
- **Additional**: 4 more files


### Evolution Entry [2026-01-29 20:34]
- **Trigger**: Code changes detected
- **Files**: `ai-env/workflows/delegate.md`, `ai-env/workflows/execute.md`, `ai-env/workflows/health.md`
- **Additional**: 4 more files


### Evolution Entry [2026-01-29 20:34]
- **Trigger**: Code changes detected
- **Files**: `ai-env/workflows/delegate.md`, `ai-env/workflows/execute.md`, `ai-env/workflows/health.md`
- **Additional**: 4 more files
