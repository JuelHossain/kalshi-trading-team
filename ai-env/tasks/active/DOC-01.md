---
id: DOC-01
title: Improve CLAUDE.md with Comprehensive Project Documentation
status: PENDING
created_by: claude-4-7
assigned_to: claude-4-7
created_at: 2026-02-05T22:15:00Z
---

## Objective
Rewrite and improve [CLAUDE.md](../../CLAUDE.md) with comprehensive project-specific documentation for the Sentient Alpha trading engine, replacing the generic workflow content.

## Acceptance Criteria

### Content Requirements
- [ ] Quick Start section with install/run/test commands
- [ ] Architecture overview of 4-Mega-Agent system (Soul, Senses, Brain, Hand)
- [ ] Key files table with clickable links
- [ ] Environment setup (.env variables) with link to .env.example
- [ ] Critical Safety Features section (hard floor, kill switches, cycle timing, trade limits)
- [ ] HTTP API endpoints table (port 3002)
- [ ] Testing commands
- [ ] Development workflow (format, lint)
- [ ] Gotchas section with non-obvious patterns

### Quality Standards
- [ ] All file paths use markdown link syntax for IDE navigation
- [ ] Commands are copy-paste ready
- [ ] Concise and human-readable
- [ ] No generic advice - project-specific only
- [ ] Current and accurate to codebase state

## Context

### Current State Assessment
**Score: 12/100 (Grade: F)**

| Criterion | Score | Notes |
|-----------|-------|-------|
| Commands/workflows | 0/20 | No build, test, or dev commands documented |
| Architecture clarity | 0/20 | No agent system explained |
| Non-obvious patterns | 0/15 | No kill switches, hard floor, or gotchas |
| Conciseness | 10/15 | Brief but minimal substance |
| Currency | 2/15 | Doesn't reflect current sophisticated system |
| Actionability | 0/15 | Vague workflow, not executable commands |

### Issues Found in Current CLAUDE.md
- Contains only generic workflow description ("follow the user command, and plan")
- Typo: "devide" should be "divide"
- Numbering skips from 6 to 8
- References non-existent `handsoff.sh`
- Missing: run/test commands, architecture, environment setup, safety features

### Codebase Profile
- **Project**: Sentient Alpha Trading Engine
- **Type**: Python 3.12 trading system
- **Entry Point**: [main.py](main.py)
- **Architecture**: 4-Mega-Agent system with supporting components
- **API**: FastAPI server on port 3002
- **Database**: SQLite (ghost_memory.db), Supabase integration
- **Testing**: pytest suite in [../tests/engine/](../tests/engine/)

## Implementation Notes

### Proposed CLAUDE.md Structure
```markdown
# Sentient Alpha Trading Engine

## Quick Start
## Architecture
## Key Files
## Environment
## Critical Safety Features
## HTTP API (Port 3002)
## Testing
## Development
## Gotchas
```

### Key Sections to Include

1. **Quick Start**
   - `pip install -r requirements.txt`
   - `cp .env.example .env`
   - `python main.py`
   - `cd .. && pytest tests/engine/ -v`

2. **Architecture - 4-Mega-Agent System**
   - SOUL (agent_id: 1) - System, Memory & Evolution
   - SENSES (agent_id: 2) - Surveillance & Signal Detection
   - BRAIN (agent_id: 3) - Intelligence & Mathematical Verification
   - HAND (agent_id: 4) - Precision Strike & Budget Sentinel
   - GATEWAY (agent_id: 5) - API gateway

3. **Critical Constants**
   - `HARD_FLOOR_CENTS = 25500` ($255 minimum)
   - `MIN_CYCLE_INTERVAL_SECONDS = 30`
   - `MAX_STAKE_CENTS = 7500` ($75 max per trade)

4. **Kill Switches (4 layers)**
   - Manual: POST /kill-switch
   - Environment: KILL_SWITCH=true
   - Vault: Auto when balance < hard floor
   - Soul Lockdown: Agent-initiated

5. **API Endpoints**
   - POST /trigger, POST /kill-switch, GET /stream, GET /health, GET /pnl, POST /auth/login

## Related
- Triggered by: `/claude-md-improver` skill
- Reference: [CLAUDE.md Improver Documentation](https://github.com/anthropics/claude-code-plugins/blob/main/plugins/claude-md-management/skills/claude-md-improver/SKILL.md)
- Quality Criteria: [quality-criteria.md](https://github.com/anthropics/claude-code-plugins/blob/main/plugins/claude-md-management/references/quality-criteria.md)