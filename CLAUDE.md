# Sentient Alpha - Claude Code Onboarding Manual

This guide provides Claude Code with the necessary context to maintain the Sentient Alpha trading bot autonomously.

## 📌 Context (The WHY & WHAT)
Sentient Alpha is an autonomous 2-tier trading system on Kalshi. It uses a committee of 4 Mega-Agents (Soul, Senses, Brain, Hand) to analyze and trade prediction markets.

## 🏃 Common Commands (The HOW)

| Action | Command | Directory |
| :--- | :--- | :--- |
| **All-in-One Dev** | `npm run dev` | Root |
| **Build Frontend** | `npm run build` | Frontend |
| **Install Env** | `pip install -r engine/requirements.txt` | Root |
| **Inspect DB** | `python3 .opencode/skills/market-intel/scripts/inspect_signals.py` | Root |
| **Health Check** | `python3 .opencode/skills/core-ops/scripts/health_check.py` | Root |

## 📖 Project Terminology
- **Synapse**: The persistent SQLite queue (`engine/ghost_memory.db`) used for inter-agent data handoff.
- **Ragnarok**: The emergency protocol to liquidate all positions and lock the vault.
- **2-Tier**: A architecture where React talks directly to Python via port 3002.
- **Autopilot Pulse**: The internal heartbeat managed by the `SoulAgent` that authorizes cycles.

## ✒️ Coding & Architectural Standards
- **Direct API**: All frontend calls must use the `/api` proxy leading to engine port 3002.
- **SSE Streams**: Subscribes to `/api/stream`. Buffer logs in the Zustand store to avoid UI lag.
- **Strict Logic**: Refactor Brain logic only if it passes `tests/verify_personas.py`.

## ⚠️ Gotchas & Constraints
- **Port 3002**: Always belongs to the Python Engine. Do not attempt to run Node.js on this port.
- **Heuristic Veto**: If variance > 0.25, the simulation MUST veto, regardless of confidence.
- **RSA Keys**: Auth requires RSA-PSS signing. Never modify the signature logic in `KalshiClient`.

## 🤝 Repository Etiquette
- **Branch**: Only work on the `opencode` branch.
- **Sync**: After any logic change, update `CLAUDE.md` and `ai-env/workflows/` (via `.agent/workflows/`) to reflect the new state.
- **Handoff**: Finish every task by updating a file in `walkthroughs/`.

## 🤝 Multi-Agent Git Protocol
- **Pull First**: ALWAYS run `git pull --rebase origin opencode` before starting work.
- **Atomic Handoff**: Use `./scripts/handoff.sh "Your message"` to sync documentation and commit atomically.
- **Linear History**: Keep a clean commit history for the next agent's context.

---
_Auto-loaded via CLAUDE.md_
