## Overview
This skill centralizes repository health and branch management. It ensures that the Universal AI Environment stays functional and that git state never blocks autonomous agents.

## Maintenance Protocol
1. **Garbage Collection**: Run `python3 ai-env/skills/git-ops/scripts/git_maintenance.py` to optimize the `.git` directory.
2. **Branch Promotion**: Always merge stable `opencode` work into `main` after a mission walkthrough is approved.
3. **Linear History**: Never use `git merge` if it creates "train tracks". Prefer `git pull --rebase`.

## Hierarchy
- **main**: The "Gold Master". Only contains stable, walkthrough-verified evolutionary states.
- **opencode**: The designated AI workspace. All agents MUST perform their primary execution here.

## Maintenance Commands
- **Full Refresh**: `git fetch --all --prune`
- **Promotion**: `git checkout main && git merge opencode && git push origin main && git checkout opencode`
- **Clean Fix**: `git gc --prune=now --aggressive`
