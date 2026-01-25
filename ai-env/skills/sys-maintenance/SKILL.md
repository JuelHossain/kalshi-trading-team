---
name: sys-maintenance
description: Automated synchronization of project documentation and AI environment context
---

## Overview
This skill ensures that the Project Intelligence (OpenCode Skills, ai-env/ personas, and Platform Configs) never desyncs from the actual Python/React code.

## The Sync Checklist
When running a sync, ensure:
1. `AGENTS.md` matches the current `engine/` pillars.
2. `CLAUDE.md` common commands are up to date.
3. `ai-env/personas/` align with the `BrainAgent` logic.
4. `.opencode/skills/` reflect new technical standards.

## Usage
Run the `/sync` workflow after any major merge or refactor.
