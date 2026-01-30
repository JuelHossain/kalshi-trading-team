# Central Application Runner Implementation

## Summary

Implemented a unified, cross-platform script to run the Sentient Alpha application locally, solving port conflicts and dependency management issues.

## Problem

The previous approach had several issues:
1. **Port conflicts** - No automatic detection/resolution of port 3000/3002 conflicts
2. **Missing dependencies** - No automatic check for Python/Node dependencies
3. **Complex commands** - Users needed to know multiple npm scripts and manual steps
4. **Platform differences** - No unified approach for Windows/Linux/Mac

## Solution

Created `scripts/run.py` - a Python-based central runner that handles:

### Features
- ✅ **Port conflict detection** - Automatically finds and kills processes using ports 3000/3002
- ✅ **Dependency checking** - Verifies Python (aiohttp) and Node dependencies before starting
- ✅ **Auto-installation** - Installs missing dependencies automatically
- ✅ **Cross-platform** - Works on Windows, Linux, and macOS
- ✅ **Multiple modes** - Development (hot reload) and Production (PM2)
- ✅ **Status monitoring** - Shows running services and port occupancy

### Commands

```bash
python scripts/run.py dev       # Development mode
python scripts/run.py prod      # Production mode
python scripts/run.py status    # Check service status
python scripts/run.py stop      # Stop all services
```

### NPM Shortcuts

Added to package.json for convenience:
```bash
npm run run:dev      # python scripts/run.py dev
npm run run:prod     # python scripts/run.py prod
npm run run:status   # python scripts/run.py status
npm run run:stop     # python scripts/run.py stop
```

## Files Changed

1. **scripts/run.py** (NEW) - Central runner script
2. **ai-env/workflows/run_app.md** - Updated workflow documentation
3. **CLAUDE.md** - Updated common commands section
4. **package.json** - Added npm script shortcuts

## Testing

Verified functionality:
- Port detection works on Windows (uses netstat)
- Process termination works (taskkill on Windows)
- Status display shows correct information
- Stop command terminates services properly

## Architecture

The runner uses a 2-tier architecture approach:
- **Frontend** (Port 3000): Vite dev server or production preview
- **Engine** (Port 3002): Python aiohttp server with 4 Mega-Agents

The script uses `concurrently` to run both services with colored output prefixes.

---
_Created: 2026-01-29_
