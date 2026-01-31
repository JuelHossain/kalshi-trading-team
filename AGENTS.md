# AGENTS.md - Sentient Alpha Trading Project

## ⚠️ CRITICAL: READ FIRST

**🛑 STOP! Before doing ANY work, answer this:**

**Am I about to modify 3+ files OR implement a feature?**
- **YES** → You MUST use Task tool to delegate. DO NOT proceed.
- **NO** → You may proceed with simple 1-2 file changes only.

**If you proceed without delegating when you should have, YOU ARE FAILING.**

---

**ALWAYS COMMIT BEFORE LEAVING:**
- `./scripts/handoff.sh "message"`
- Uncommitted work = FAILED session

---

## Entry Protocol
1. **Read identity.md**: Check `ai-env/soul/identity.md` for Core Essence first.
2. **Check Task Board**: Run `cat ai-env/tasks/BOARD.md` for pending tasks.
3. **Task Board Commands**:
   - `/status` - Show current BOARD.md state

This file provides structured context for AI agents working on the Sentient Alpha Trading Bot. Adherence to these standards is mandatory for autonomous safety and system integrity.

## 🚀 Project Overview
Sentient Alpha is an autonomous 2-tier trading system on Kalshi.
- **Backend (Engine)**: Python 3.12 (Logic, AI, Market SDK).
- **Frontend (Cockpit)**: React + Vite (Real-time HUD).
- **Architecture**: Direct SSE/REST link (No Node.js bridge).
- **Diagnostics**: **Sentient HUD** (Built-in health & soul monitor in the Cockpit).

## 🛠️ Build & Task Commands

### General
- **Initialization**: `npm install`
- **Development Mode**: `npm run dev` (Starts Frontend [3000] and Engine [3002])
- **Production Distribution**: `npm run build`

### Python Engine
- **Setup**: `pip install -r engine/requirements.txt`
- **Standard Run**: `python3 engine/main.py`
- **Isolated Tests**: `python3 engine/diagnostics/brain_tap.py`

### React Frontend
- **Setup**: `cd frontend && npm install`
- **Build Verification**: `npm run build`

## 🧪 Testing Instructions
- **Unit Tests**: Run `pytest tests/unit/` before every engine commit.
- **Persona Verification**: Run `python3 tests/verify_personas.py` after Brain logic changes.
- **Safety**: Ensure `IS_PAPER_TRADING: true` is set in `.env` for all non-monitored tests.

## ✒️ Coding & Architectural Standards

### Architecture (2-Tier Guardrails)
- **Direct Communication**: Frontend connects directly to port 3002.
- **Persistence**: Inter-agent signals (Opps -> Signals -> Execs) MUST go through **Synapse (SQLite)**. **Direct agent-to-agent data flow is strictly forbidden.**
- **Error States**: All critical failures must be logged to the **Synapse Error Box**.

### Style Prefs
- **JavaScript/TS**: ESM, Async/Await, PascalCase for components.
- **Python**: PEP 8, Asyncio for I/O, snake_case for functions.
- **Logging**: 
  - **Do NOT use `print()`**. Use `core.logger.get_logger("NAME")`.
  - **Sensitive Data**: Use `core.bus.mask_sensitives` (or relying on logger's sensitivity mask if implemented) for external logs.
  - **Colors**: Do not manually color strings (e.g. `Fore.RED`). The logger handles this.
  - **Structure**: Include `agent_id` or `phase_id` in all high-priority log events.

## 🛡️ Security & Safety
- **Veto Supremacy**: Any security veto terminates the cycle immediately.
- **Persistent Error Box**: GhostEngine halts all cycles if errors exist in `Synapse.errors`. Use `ErrorDispatcher.log_error()` to trigger.
- **Ragnarok Protocol**: Hand agent must execute liquidation on fatal errors.
- **Credentials**: NEVER commit `.env` or RSA keys.

## 📊 Data Integrity Rules (CRITICAL)
- **NEVER Use Mock Data**: All market data, signals, and trading decisions MUST use real data from the Kalshi API or verified sources. Mock data is strictly prohibited in any production code path.
- **Validate Sources**: Always verify data source authenticity before processing.
- **Fail Real**: If data is unavailable, fail explicitly rather than falling back to synthetic data. 

## 🔄 Maintenance & Evolution
- **Sync**: After any logic refactor, use the `/sync` workflow to update `.opencode/` and `ai-env/` folders.
- **Handoff**: Document every major change in `walkthroughs/`.

## 📂 Project Structure
- `engine/`: Core Python logic and 4 Mega-Agents.
- `frontend/`: React application.
- `shared/`: TypeScript type definitions.
- `walkthroughs/`: Mission history and task handoffs.
- `ai-env/`: The Universal source of truth for all AI assistants.
  - `skills/`: Centralized tools (Linked via `.opencode/skills`).
  - `workflows/`: Operational runbooks (Linked via `.agent/workflows`).
  - `core-docs/`: Constitution and Design Guides.
  - `personas/`: AI mental model definitions.

## 🤝 Multi-Agent Git Protocol
- **Pull First**: ALWAYS run `git pull --rebase origin main` before starting work.
- **Atomic Handoff**: Use `./scripts/handoff.sh "Your message"` to sync documentation and commit atomically.
- **Never Leave Uncommitted Changes**: Agents MUST commit all changes before ending their session.
- **Linear History**: Keep a clean commit history for the next agent's context.
- **Git Enforcement**: Run `python scripts/evolution/git_enforcer.py check` to verify compliance.

---
_Generated for OpenCode Autonomous Performance_