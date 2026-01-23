# Multi-Agent Project Constitution
Strict standards for all Human and AI collaborators to ensure project stability, autonomous safety, and efficient scaling.

## 🛡️ PILLAR 1: Safety & Operational Security (The Anchor)
*   **Veto Supremacy**: If ANY security agent (Auditor, Sim Scientist) emits `veto: true` or `verdict: VETO`, the trade cycle must terminate immediately. No buy orders allowed.
*   **Vault Lock**: Zero trade execution if `VaultState.isLocked` is true.
*   **Paper-First**: All new agents and experimental workflows must default to `IS_PAPER_TRADING: true`.
*   **Credential Shield**: Never commit `.env` or `.env.local`. Use provided `update-env` workflow for key rotation.

## 🔗 PILLAR 2: Agent Contract & Service Boundaries
*   **Decoupled I/O**: Agents communicate *exclusively* via JSON on the `EventBus`. No direct file mutation or global state modification outside of your specific module.
*   **Runtime Validation**: Every published message must pass schema validation (Zod/Pydantic). Malformed data must trigger a `CRITICAL` log and cycle abortion.
*   **Latency Budget**: Market-critical agents (Scout, Interceptor) must return data within **2.5s**. No blocking I/O; use `asyncio` for all networking and LLM calls.

## 🛠️ PILLAR 3: Engineering & Git Workflow (The Shield)
*   **Git Protocol**: Never commit directly to `main`. Always work on the `antigravity` branch.
*   **Clean History**: Always pull before pushing to prevent merge conflicts. Use `rebase` to keep history clean.
*   **Atomic Refactoring**: Commits must be testable units with conventional titles (`feat:`, `fix:`, `refactor:`).
*   **Deployment Lifecycle**: Always build and deploy after every walkthrough so the user can see changes in the UI.
*   **Verification**: Test every change thoroughly (build/deploy/UI check) before considering a task done or pushing code.

## 📈 PILLAR 4: Resilience & Scalability (The Layer)
*   **Defensive API Usage**: Implement **Exponential Backoff** for 429/500 errors. Agents should "Hibernate" after 5 failures to protect API reputation.
*   **Determinism**: Log enough context to recreate decisions using the `replay-debug` workflow.
*   **Alpha Efficiency**: Heavy math/filtering belongs in Python/Numpy. LLMs are reserved for high-value "Finalist" tickers only.
*   **Process Management**: Follow the `ecosystem.config.cjs` architecture. All services (Backend, Frontend, Engine) must be managed via PM2.

