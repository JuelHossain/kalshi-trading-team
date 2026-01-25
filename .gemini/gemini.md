# Multi-Agent Project Constitution

Strict standards for all Human and AI collaborators to ensure project stability, autonomous safety, and efficient scaling.

## 🛡️ PILLAR 1: Safety & Operational Security (The Anchor)

- **Veto Supremacy**: If ANY security check emits `veto: true`, the trade cycle must terminate immediately. No buy orders allowed.
- **Vault Lock**: Zero trade execution if `VaultState.isLocked` is true.
- **Paper-First**: All experimental workflows must default to `IS_PAPER_TRADING: true`.
- **Ragnarok Protocol**: Manual and automated kill-switches must trigger an immediate liquidation of all open orders.

## 🔗 PILLAR 2: Agent Contract & Service Boundaries

- **Synapse Persistence**: High-value data handoff (Opportunities -> Signals -> Executions) must go through the **Synapse Persistent Queue** (SQLite).
- **Decoupled I/O**: Agents communicate via the `EventBus` for triggers, but rely on Synapse for state persistence.
- **Latency Budget**: Market-critical tasks must use `asyncio` to prevent blocking the event loop.

## 🛠️ PILLAR 3: Engineering & Git Workflow (The Shield)

- **Git Protocol**: Never commit directly to `main`. Always work on the `opencode` branch.
- **Atomic Refactoring**: Commits must be testable units with conventional titles (`feat:`, `fix:`, `refactor:`).
- **Verification**: Test every change thoroughly (Build -> Deploy -> UI Check) before considering a task complete.
- **Proof of Work**: Every significant task must result in a `.md` walkthrough in the `walkthroughs/` folder.

## 📈 PILLAR 4: Resilience & Scalability (The Layer)

- **2-Tier Architecture**: React Frontend connects directly to the Python Engine (Port 3002). No intermediate Node.js layer.
- **AI Stack**: Use the `google-genai` SDK with Gemini 1.5 Pro.
- **Process Management**: Follow the `ecosystem.config.cjs` architecture. Services must be managed via PM2.
- **Environment**: Use `.env` for secrets; never commit keys to the repository.

---
_Constitution Ratified - Sentient Alpha Core_
