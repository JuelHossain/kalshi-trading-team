---
description: How to run the application locally (Central Runner)
syntax: python scripts/run.py [dev|prod|stop|status]
---

# Run Application Workflow

**Last Updated**: 2026-01-29

This workflow describes how to run the Sentient Alpha application locally using the **central runner script**.

## Prerequisites

- Python 3.11+
- Node.js 18+
- npm or yarn

## Quick Start

**Claude Code**: Use the `run-app` skill for dev/prod/status/stop operations.

**Other Agents**: Use the central runner script which handles:
- ✅ Port conflict detection and resolution
- ✅ Dependency installation (if missing)
- ✅ Environment setup
- ✅ Cross-platform support (Windows/Linux/Mac)

### Commands

```bash
# Development mode (hot reload, verbose logging)
python scripts/run.py dev

# Production mode (PM2 process manager)
python scripts/run.py prod

# Check status of services and ports
python scripts/run.py status

# Stop all running services
python scripts/run.py stop
```

## Development Mode

Development mode runs both the frontend and Python engine with hot reload:

```bash
python scripts/run.py dev
```

**What it does:**
1. Checks and installs Python dependencies (`engine/requirements.txt`)
2. Checks and installs Node dependencies (`frontend/package.json`)
3. Detects and resolves port conflicts (ports 3000 and 3002)
4. Starts the Vite dev server on http://localhost:3000
5. Starts the Python engine on http://localhost:3002
6. Runs both services concurrently with colored output

**Access URLs:**
- Frontend HUD: http://localhost:3000
- Engine API: http://localhost:3002

## Production Mode

Production mode uses PM2 for process management:

```bash
python scripts/run.py prod
```

**What it does:**
1. Builds the frontend for production
2. Starts services with PM2 process manager
3. Persists process list for auto-restart

**Access URLs:**
- Frontend: http://localhost:3000
- Engine API: http://localhost:3002

**PM2 Commands:**
```bash
npx pm2 logs          # View logs
npx pm2 monit         # Monitor processes
npx pm2 stop all      # Stop all services
npx pm2 restart all   # Restart all services
```

## Status Check

Check if services are running and which ports are in use:

```bash
python scripts/run.py status
```

This shows:
- Port occupancy (3000, 3002)
- Process IDs of running services
- Dependency installation status

## Troubleshooting

### Port Already in Use

The runner automatically detects and kills processes occupying ports 3000/3002. If this fails:

**Manual port clearing:**
```bash
# Windows
netstat -ano | findstr :3002
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:3002 | xargs kill -9
```

### Missing Dependencies

The runner auto-installs missing dependencies. To manually install:

```bash
# Python
cd engine
pip install -r requirements.txt

# Node
cd frontend
npm install
```

### Legacy Methods (Not Recommended)

If you need to use the legacy npm scripts directly:

```bash
# Requires manual port management and dependency checks
npm run dev           # Development mode via npm
npm start             # Production mode via PM2
npm run stop          # Stop PM2 services
```

## Architecture

The application uses a **2-tier architecture**:

1. **Frontend Tier** (Port 3000)
   - React + Vite + TypeScript
   - Proxies API calls to `/api` → `localhost:3002`

2. **Engine Tier** (Port 3002)
   - Python + aiohttp
   - 4 Mega-Agent system (Soul, Senses, Brain, Hand)
   - SQLite persistence via Synapse


## Dependencies

This workflow depends on:

- `engine/core/auth.py`
- `engine/core/bus.py`
- `engine/core/error_dispatcher.py`
- `engine/core/network.py`
- `engine/core/synapse.py`
- *and 25 more files*
## Health Check

After starting, verify the system:

```bash
python ai-env/skills/core-ops/scripts/health_check.py
```

Or visit: http://localhost:3000/health

---
_Last updated: 2026-01-29_

---

*Evolution Note [2026-01-29 20:34]: Auto-updated due to changes in related code.*
