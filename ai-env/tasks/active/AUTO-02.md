---
id: AUTO-02
title: Claude Code Automation Recommendations - Engine Focus (2026-02-05)
status: PENDING
created_by: claude-automation-recommender
assigned_to: claude-4-7
created_at: 2026-02-05T22:20:00Z
---

## Objective
Implement the automation recommendations from the fresh Claude Code automation analysis focused on the engine directory and 4-Mega-Agent architecture.

## Acceptance Criteria

### 🔌 MCP Servers
- [ ] **Playwright MCP**: Install for HTTP API ([http_api/routes.py](http_api/routes.py)) testing
  - Install: `claude mcp add playwright`
  - Use for: Dashboard UI testing, API endpoint verification
- [ ] **GitHub MCP**: Install for issue/PR workflow integration
  - Install: `claude mcp add github`
  - Prerequisite: `gh` CLI installed

### 🎯 Skills
- [ ] **error-investigate**: Create `.claude/skills/error-investigate.yaml`
  - Investigate errors by code (e.g., BRAIN-001)
  - Recent errors with domain/severity filtering
  - Uses [error_manager.py](core/error_manager.py) and [error_dispatcher.py](core/error_dispatcher.py)
- [ ] **agent-status**: Create `.claude/skills/agent-status.yaml`
  - Quick status check for Soul, Senses, Brain, Hand agents
  - State, cycles info without full HUD startup
- [ ] **migration-create**: Create `.claude/skills/migration-create.yaml`
  - Scaffold Supabase migrations with timestamp
  - Template with up/down blocks and rollback safety

### ⚡ Hooks
- [ ] **Restore Black/Ruff formatting**: Activate from [hooks.json.bak](../.claude/hooks.json.bak)
  - PostToolUse: `python -m black {file}` for `*.py`
  - PostToolUse: `python -m ruff check {file} --fix` for `*.py`
  - Location: `.claude/settings.json` or parent
- [ ] **Post-edit test runner**: Run pytest after file changes
  - Pattern: `agents/**/*.py` → `pytest tests/engine/agents/`
  - Pattern: `core/**/*.py` → `pytest tests/engine/core/`
- [ ] **Pre-edit protection**: Block sensitive file edits
  - Pattern: `core/vault.py` → Warning about HARD_FLOOR_CENTS
  - Pattern: `.env` → Block with "use .env.example" message

### 🤖 Subagents
- [ ] **trading-logic-reviewer**: Create `.claude/agents/trading-logic-reviewer.md`
  - Validates [brain/agent.py](agents/brain/agent.py) changes preserve safety rules
  - Checks: variance veto (0.25), confidence threshold (85%), EV accuracy
  - Triggers on: `agents/brain/*.py`, simulation logic, config changes
- [ ] **security-auditor**: Create `.claude/agents/security-auditor.md`
  - Audits [auth.py](core/auth.py), [vault.py](core/vault.py), gateway
  - Checks: RSA-PSS integrity, credential storage, vault access controls
  - Triggers on: auth, vault, Hand agent, credential handling changes
- [ ] **test-coverage-analyzer**: Create `.claude/agents/test-coverage-analyzer.md`
  - Identifies untested code paths after changes
  - Checks: new functions, edge cases, error paths, integration tests

### 🔌 Plugins
- [ ] **pr-review-toolkit**: Install for comprehensive PR reviews
  - Install: `claude plugin add pr-review-toolkit`
  - Use with: `/pr-review` command

## Context

### Codebase Profile
- **Project**: Sentient Alpha Trading Engine v3.0
- **Type**: Python 3.12 async project with aiohttp
- **Architecture**: 4-Mega-Agent system (Soul, Senses, Brain, Hand)
- **Entry Point**: [main.py](main.py)
- **API**: HTTP on port 3002 ([http_api/routes.py](http_api/routes.py))
- **Database**: SQLite (ghost_memory.db), Supabase integration
- **Testing**: pytest in [../tests/engine/](../tests/engine/)
- **Formatting**: black + ruff configured

### Existing Automation
- **MCP Servers**: context7, supabase (configured in parent `.claude/mcp.json`)
- **Skills**: vault-status, simulate-trade, test-generator, health-check, run-app, sync-docs, git-handoff, inspect-signals
- **Hooks**: hooks.json.bak exists (black/ruff) but not active
- **Agents**: ux-dashboard-architect (for dashboard design)

### Critical Constants (from [config.py](config.py))
- `HARD_FLOOR_CENTS = 25500` ($255 minimum vault balance)
- `MAX_STAKE_CENTS = 7500` ($75 max per trade)
- `CONFIDENCE_THRESHOLD = 0.85` (85% minimum)
- `MAX_VARIANCE = 0.25` (veto threshold)

### Agent Architecture
| Agent | ID | Purpose |
|-------|-----|---------|
| SOUL | 1 | System, Memory & Evolution |
| SENSES | 2 | Surveillance & Signal Detection |
| BRAIN | 3 | Intelligence & Mathematical Verification |
| HAND | 4 | Precision Strike & Budget Sentinel |
| GATEWAY | 5 | API gateway |

## Implementation Priority

### High Impact (Do First)
1. Restore Black/Ruff hooks - Already written, just needs activation
2. trading-logic-reviewer subagent - Critical for Brain agent safety
3. security-auditor subagent - Financial/security critical

### Medium Impact
4. error-investigate skill - Streamlines debugging workflow
5. Post-edit test runner hook - Catches issues early
6. Pre-edit protection hooks - Prevents accidents

### Lower Impact (Enhancement)
7. Playwright MCP - For UI testing
8. GitHub MCP - For issue/PR workflow
9. agent-status skill - Convenience
10. migration-create skill - Developer workflow

## Implementation Notes

### Files to Create
```
.claude/
├── skills/
│   ├── error-investigate.yaml      (NEW)
│   ├── agent-status.yaml           (NEW)
│   └── migration-create.yaml       (NEW)
├── agents/
│   ├── trading-logic-reviewer.md   (NEW)
│   ├── security-auditor.md         (NEW)
│   └── test-coverage-analyzer.md   (NEW)
└── settings.json                   (UPDATE - restore hooks)
```

### Hook Configuration Template
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "pattern": "*.py",
        "command": "python -m black {file}",
        "name": "Format Python with Black"
      },
      {
        "pattern": "*.py",
        "command": "python -m ruff check {file} --fix",
        "name": "Lint Python with Ruff"
      },
      {
        "pattern": "agents/**/*.py",
        "command": "python -m pytest tests/engine/agents/ -v --tb=short",
        "name": "Run agent tests",
        "condition": "file_modified"
      }
    ],
    "PreToolUse": [
      {
        "pattern": "core/vault.py",
        "command": "echo 'WARNING: Editing vault.py - ensure HARD_FLOOR_CENTS preserved'",
        "name": "Warn before editing vault"
      }
    ]
  }
}
```

## Related
- Previous: [AUTO-01](./AUTO-01.md) (COMPLETED - 2026-01-29)
- Analysis: Fresh automation analysis via `/claude-automation-recommender`
- Parent config: [../.claude/mcp.json](../.claude/mcp.json)
- Hooks backup: [../.claude/hooks.json.bak](../.claude/hooks.json.bak)