## ⚠️ Entry Protocol (Token-Efficiency)

**🚨 TWO NON-NEGOTIABLE RULES:**

**1. AUTO-DELEGATION IS MANDATORY**
- **3+ files affected? → DELEGATE**
- **Feature implementation? → DELEGATE**
- **NOT optional. See [NLF_PROTOCOL.md](ai-env/core-docs/NLF_PROTOCOL.md)**
- **DO NOT do it yourself.**

**2. ALWAYS COMMIT YOUR WORK**
- **Before ending: `./scripts/handoff.sh "message"`**
- **Uncommitted work = FAILED session**
- **NO exceptions.**

1. Read the **Core Essence** and **last 3 entries** of [identity.md](ai-env/soul/identity.md) before complex tasks.
2. **Check the Task Board**: Read `ai-env/tasks/BOARD.md` for cross-agent visibility (read-only for Claude).
3. **Use Native Skills**: Common operations via `/skill-name` (see `.claude/skills/` directory).
4. **DELEGATE**: Use Task tool for ANY 3+ file task or feature work.

## 📌 Context (The WHY & WHAT)
Sentient Alpha is an autonomous 2-tier trading system on Kalshi. It uses a committee of 4 Mega-Agents (Soul, Senses, Brain, Hand) to analyze and trade prediction markets.

## 📖 Persistence & Diagnostics
- **Signals**: Inter-agent persistence is handled by **Synapse** (SQLite).
- **Diagnostics**: Use the **Sentient HUD** (port 3000) for real-time state and project intuition.

## 🏃 Common Operations (The HOW)

### 🎯 Native Skills (Recommended)
Use these via `/skill-name`:
- **/health-check** - Full system diagnostics (ports, services, Synapse)
- **/inspect-signals** - View latest trade signals in Synapse
- **/run-app** - Application control (dev/prod/status/stop)
- **/sync-docs** - Synchronize documentation and AI context
- **/git-handoff** - Atomic git commits with soul snapshot

### 🔧 Direct Commands (When needed)

| Action | Command | Notes |
| :--- | :--- | :--- |
| **All-in-One Dev** | `npm run dev` | Root |
| **Build Frontend** | `npm run build` | Frontend |
| **Install Env** | `pip install -r engine/requirements.txt` | Root |

## 📖 Project Terminology
- **Synapse**: The persistent SQLite queue (`engine/ghost_memory.db`) used for inter-agent data handoff.
- **Ragnarok**: The emergency protocol to liquidate all positions and lock the vault.
- **2-Tier**: A architecture where React talks directly to Python via port 3002.
- **Autopilot Pulse**: The internal heartbeat managed by the `SoulAgent` that authorizes cycles.

## ✒️ Coding & Architectural Standards
- **Direct API**: All frontend calls must use the `/api` proxy leading to engine port 3002.
- **SSE Streams**: Subscribes to `/api/stream`. Buffer logs in the Zustand store to avoid UI lag.
- **Strict Logic**: Refactor Brain logic only if it passes `tests/verify_personas.py`.

### 🔄 Code Change Protocol
**CRITICAL**: After ANY code changes to `engine/` or `frontend/`:

1. **Engine Changes** (Python):
   ```bash
   # Kill existing process on port 3002
   npx kill-port 3002
   # Restart engine
   cd engine && python main.py
   ```
   Or use `npm run dev` from root which handles both.

2. **Frontend Changes** (React/TypeScript):
   - Vite hot-reloads automatically for most changes
   - For config changes or if issues persist: refresh browser

3. **Authentication Changes**:
   - Always restart the engine after modifying `engine/core/auth.py`
   - Refresh browser to clear stale authentication state

4. **Verification**:
   ```bash
   # Test engine is running
   curl http://localhost:3002/health
   # Test through proxy
   curl http://localhost:3000/api/health
   ```

## ⚠️ Gotchas & Constraints
- **Port 3002**: Always belongs to the Python Engine. Do not attempt to run Node.js on this port.
- **Heuristic Veto**: If variance > 0.25, the simulation MUST veto, regardless of confidence.
- **RSA Keys**: Auth requires RSA-PSS signing. Never modify the signature logic in `KalshiClient`.

## 🤝 Repository Etiquette
- **Branch**: Only work on the `main` branch.
- **Sync**: After any logic change, update relevant documentation.
- **Handoff**: Use `/git-handoff` skill or update `walkthroughs/` manually.

## 🤝 Multi-Agent Git Protocol
- **Pull First**: ALWAYS run `git pull --rebase origin main` before starting work.
- **Atomic Handoff**: Use `/git-handoff "message"` skill to sync documentation and commit atomically.
- **Linear History**: Keep a clean commit history for the next agent's context.

---
_Auto-loaded via CLAUDE.md_
