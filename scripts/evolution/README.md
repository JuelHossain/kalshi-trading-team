# Sentient Alpha - Automatic Documentation Evolution System

This system provides autonomous documentation maintenance and evolution for the Sentient Alpha trading platform. It analyzes code changes on git commit and automatically updates relevant documentation.

## Overview

The evolution system consists of:

1. **Analyzer** (`analyzer.py`) - Detects and classifies code changes
2. **Orchestrator** (`orchestrator.py`) - Coordinates sync/async updates
3. **Updaters** (`updaters/`) - Update specific documentation types
4. **Database** (`database.py`) - Tracks evolution history
5. **Git Hooks** (`../hooks/`) - Triggers evolution on commit

## Quick Start

### Installation

```bash
# Install the git hooks
python scripts/evolution/install_hooks.py
```

### Manual Usage

```bash
# Analyze staged changes
python scripts/evolution/analyzer.py pre-commit

# Run synchronous updates (before commit)
python scripts/evolution/orchestrator.py sync

# Run asynchronous updates (after commit)
python scripts/evolution/orchestrator.py async --commit <hash>

# View evolution statistics
python scripts/evolution/orchestrator.py stats

# Process pending async updates
python scripts/evolution/orchestrator.py process-pending
```

## Configuration

Configuration is stored in `ai-env/evolution/config.yaml`:

```yaml
mappings:
  engine_agents:
    patterns: ["engine/agents/*.py"]
    doc_targets: ["ai-env/personas/*.md"]
    update_mode: "sync"
    triggers_soul: true

significance:
  min_lines_changed: 5
  high_value_files:
    - "engine/agents/brain.py"
```

### Configuration Options

- **patterns**: Glob patterns to match changed files
- **doc_targets**: Documentation files to update
- **update_mode**: `"sync"` (pre-commit) or `"async"` (post-commit)
- **triggers_soul**: Whether changes trigger a soul snapshot

## How It Works

### Pre-Commit (Synchronous)

1. Git `pre-commit` hook runs
2. Analyzer examines staged files
3. If significant changes detected:
   - Updaters modify relevant docs
   - Soul snapshot created (if triggered)
   - Documentation files staged
4. Commit proceeds with updated docs

### Post-Commit (Asynchronous)

1. Git `post-commit` hook runs
2. Async process spawned in background
3. Non-critical documentation updated
4. Evolution logged to database

## Database Schema

The evolution database (`ai-env/evolution.db`) tracks:

- Commit hash and message
- Changed files
- Documentation targets
- Update status
- Soul snapshots created
- Errors (if any)

## Disabling Evolution

Temporarily disable the system:

```bash
export EVOLUTION_DISABLED=1  # Unix
set EVOLUTION_DISABLED=1     # Windows
```

## Troubleshooting

### Hooks not running

Check if hooks are executable:
```bash
ls -la .git/hooks/pre-commit .git/hooks/post-commit
```

### Analyzer failing

Run manually to see errors:
```bash
python scripts/evolution/analyzer.py pre-commit
```

### Database issues

Reset the evolution database:
```bash
rm ai-env/evolution.db
```

## Architecture

```
scripts/evolution/
├── __init__.py           # Package initialization
├── analyzer.py           # Change detection engine
├── config.py             # Configuration loader
├── database.py           # SQLite evolution tracking
├── orchestrator.py       # Sync/async coordinator
├── git_utils.py          # Git operations wrapper
├── install_hooks.py      # Hook installation script
├── README.md             # This file
└── updaters/
    ├── __init__.py       # Base updater class
    ├── persona_updater.py    # Updates ai-env/personas/
    ├── schema_updater.py     # Updates ai-env/schemas/
    ├── skill_updater.py      # Updates ai-env/skills/
    ├── workflow_updater.py   # Updates ai-env/workflows/
    └── soul_updater.py       # Manages soul snapshots
```

## Integration with Existing Workflow

The evolution system integrates with the existing handoff workflow:

1. User makes changes to code
2. User runs `./scripts/handoff.sh "message"`
3. Handoff script captures mental snapshot
4. Evolution hooks analyze changes
5. Documentation auto-updates
6. Everything committed together

This ensures documentation always reflects the current code state.
