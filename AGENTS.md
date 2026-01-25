# AGENTS.md - Sentient Alpha Trading Project

This file provides structured context for AI agents working on the Sentient Alpha Trading Bot. Adherence to these standards is mandatory for autonomous safety and system integrity.

## 🚀 Project Overview
Sentient Alpha is an autonomous 2-tier trading system on Kalshi.
- **Backend (Engine)**: Python 3.12 (Logic, AI, Market SDK).
- **Frontend (Cockpit)**: React + Vite (Real-time HUD).
- **Architecture**: Direct SSE/REST link (No Node.js bridge).

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
- **Persistence**: Inter-agent signals (Opps -> Signals -> Execs) MUST go through **Synapse (SQLite)**.
- **State**: Use **Zustand** for global Frontend state. Avoid prop-drilling.

### Style Prefs
- **JavaScript/TS**: ESM, Async/Await, PascalCase for components.
- **Python**: PEP 8, Asyncio for I/O, snake_case for functions.
- **Logging**: Include `agent_id` or `phase_id` in all high-priority log events.

## 🛡️ Security & Safety
- **Veto Supremacy**: Any security veto terminates the cycle immediately.
- **Ragnarok Protocol**: Hand agent must execute liquidation on fatal errors.
- **Credentials**: NEVER commit `.env` or RSA keys. 

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
- **Pull First**: ALWAYS run `git pull --rebase origin opencode` before starting work.
- **Atomic Handoff**: Use `./scripts/handoff.sh "Your message"` to sync documentation and commit atomically.
- **Linear History**: Keep a clean commit history for the next agent's context.

---
_Generated for OpenCode Autonomous Performance_