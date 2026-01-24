# SKILL-GIT-WORKFLOW.md - Engineering & Git Workflow

## Overview
This skill enforces the Engineering & Git Workflow pillar, ensuring clean version control and proper development practices.

## Core Rules

### Git Protocol
- **Branching**: Never commit directly to `main`
- **Working Branch**: Always work on the `opencode` branch
- **Merging**: Use PRs or direct merges from feature branches
- **Protection**: Main branch protected from direct pushes

### Clean History
- **Pull First**: Always pull before pushing to prevent conflicts
- **Rebasing**: Use `rebase` to keep history linear and clean
- **Squashing**: Combine related commits when appropriate
- **Conflicts**: Resolve locally before pushing

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