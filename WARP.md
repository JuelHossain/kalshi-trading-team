# Warp Agent - Sentient Alpha Context

## ⚠️ Entry Protocol (Token-Efficiency)
Always read the **Core Essence** and the **last 3 entries** of [identity.md](./ai-env/soul/identity.md) before starting complex tasks. For simple operations (running commands, quick fixes), skip to save tokens.

## 📌 Context (The WHY & WHAT)
Sentient Alpha is an autonomous 2-tier trading system on Kalshi powered by 4 Mega-Agents (Soul, Senses, Brain, Hand). It analyzes prediction markets, debates strategies with AI, simulates outcomes via Monte Carlo, and executes precision trades.

**Architecture**:
- **Frontend**: React + Vite + Zustand (port 3000)
- **Engine**: Python 3.12 + Asyncio (port 3002)
- **Communication**: Server-Sent Events (SSE) and REST API

## 🏃 Common Commands (Quick Reference)

| Action | Command | Notes |
| :--- | :--- | :--- |
| **Run Application** | `npm run dev` | Starts both frontend and engine |
| **Install Dependencies** | `npm install && pip install -r engine/requirements.txt` | Root + Python |
| **Frontend Only** | `cd frontend && npm install && npm run dev` | Port 3000 |
| **Engine Only** | `python engine/main.py` | Port 3002 |
| **Run Tests** | `pytest tests/unit/` | Python unit tests |
| **Health Check** | `python ai-env/skills/core-ops/scripts/health_check.py` | System diagnostics |
| **Lint Code** | `npm run lint` | ESLint + Ruff + Black |

## 🛠️ Warp-Specific Workflows
Detailed operational procedures available in [ai-env/warp/workflows.md](./ai-env/warp/workflows.md).

Key workflows:
- **System Initialization**: First-time setup and dependency installation
- **Platform Compatibility**: Handling Windows/Unix differences
- **Debug & Error Resolution**: Systematic debugging approach
- **Git Operations**: Branch management and commits
- **Cross-Platform Awareness**: OS-specific considerations

## 🧱 The 4 Mega-Agents (Agent Architecture)
- **SOUL** (Agent 1): System orchestrator, autopilot controller, evolution manager
- **SENSES** (Agent 2): Market surveillance, signal detection, external context via DuckDuckGo
- **BRAIN** (Agent 3): Decision maker, AI debates (Gemini), Monte Carlo simulations
- **HAND** (Agent 4): Trade executor, capital protection, Ragnarok emergency protocol

## 📖 Project Terminology
- **Synapse**: Persistent SQLite queue (`engine/ghost_memory.db`) for inter-agent communication
- **Ragnarok**: Emergency liquidation protocol to close all positions and lock vault
- **2-Tier Architecture**: React communicates directly with Python engine (no Node.js middleware)
- **Autopilot Pulse**: Autonomous cycle loop managed by Soul Agent
- **Vault**: Capital management system with profit locking and kill-switch mechanisms
- **Ghost Engine**: The Python orchestrator managing all 4 mega-agents

## 🎯 Warp Capabilities & Approach
As an **Agentic Development Environment**, Warp excels at:
1. **Terminal Operations**: Running commands, managing processes, debugging
2. **Code Editing**: Targeted file modifications with `edit_files` tool
3. **Iterative Problem-Solving**: Diagnose → Fix → Test → Verify cycle
4. **Cross-Platform Development**: Windows and Unix compatibility
5. **Git Workflows**: Branch management, commits, and push operations
6. **Dependency Management**: Installing packages and resolving import errors

## ✒️ Coding Standards
- **Python**: PEP 8, asyncio for I/O, snake_case functions, type hints
- **TypeScript**: ESM modules, async/await, PascalCase components
- **Logging**: Use proper log levels (INFO, WARN, ERROR, SUCCESS)
- **Platform Checks**: Always use `sys.platform` for OS-specific code
- **No Emojis**: Use ASCII alternatives for Windows compatibility
- **Git Commits**: Include `Co-Authored-By: Warp <agent@warp.dev>`

## 🚨 Critical Constraints
- **Port 3002**: Reserved for Python Engine (never use for Node.js)
- **Environment Variables**: Never commit `.env` file to git
- **Synapse Integrity**: All inter-agent signals must go through SQLite queues
- **Kill Switch**: Balance < 85% of principal triggers automatic halt
- **Variance Threshold**: Simulation variance > 0.25 requires automatic veto
- **Signal Handlers**: Unix-only feature, must be wrapped in platform checks
- **API Keys**: Empty keys = degraded mode (system runs but limited functionality)

## 🔧 Common Issues & Solutions

### Windows-Specific
- **Signal handlers**: Wrap in `if sys.platform != "win32"`
- **Encoding errors**: Replace emojis with ASCII characters
- **Path separators**: Use `os.path.join()` or `Path()` for cross-platform
- **PowerShell commands**: Use `Get-ChildItem`, `Test-Path`, etc.

### Dependency Issues
- **Missing aiohttp**: Run `pip install -r engine/requirements.txt`
- **Missing concurrently**: Run `npm install` in root
- **Frontend deps**: Run `npm install` in frontend directory

### Git Issues
- **Pre-commit hooks fail**: Use `--no-verify` flag for unrelated lint issues
- **Invalid branch name**: Branch names can't start with dots
- **User not configured**: Set with `git config user.email` and `user.name`

## 📂 Key Files & Directories
- `engine/main.py`: Ghost Engine entry point
- `engine/core/`: Core systems (network, vault, bus, synapse)
- `engine/agents/`: 4 Mega-Agent implementations
- `frontend/src/`: React application
- `ai-env/`: Universal AI assistant configuration
- `ai-env/warp/`: Warp-specific workflows and context
- `ai-env/soul/identity.md`: Project state and intuition
- `.env`: API keys and configuration (gitignored)

## 🤝 Multi-Agent Handoff Protocol
When completing work for another agent to continue:
1. Update `ai-env/soul/identity.md` with a snapshot:
   - **Momentum**: What's currently in progress
   - **Crucial Logic**: Important findings or gotchas
   - **Next Move**: What the next agent should do first
2. Commit all changes with clear messages
3. Push to remote branch
4. Document major changes in `walkthroughs/`

## 🔗 Integration with Existing AI Assistants
- **OpenCode**: Uses `.opencode/skills` (symlinked to `ai-env/skills`)
- **Claude Code**: Follows `CLAUDE.md` guidelines
- **Gemini CLI**: References `GEMINI.md` for agent specifics
- **Antigravity**: Uses shared `ai-env` resources
- **Warp**: This configuration + `ai-env/warp/workflows.md`

## 🛡️ Safety & Alignment
Refer to:
- [CONSTITUTION.md](./ai-env/core-docs/CONSTITUTION.md): Core safety rules
- [CROSS_AGENT_PROTOCOL.md](./CROSS_AGENT_PROTOCOL.md): Multi-agent coordination
- [AGENTS.md](./AGENTS.md): Agent-specific guidelines

## 📊 Monitoring & Diagnostics
- **Live Dashboard**: http://localhost:3000 (Sentient HUD)
- **Engine API**: http://localhost:3002
- **Health Endpoint**: GET http://localhost:3002/health
- **SSE Stream**: http://localhost:3002/stream

## 🎓 Learning Resources
- **Project Blueprint**: [blueprint.md](./blueprint.md)
- **README**: [README.md](./README.md)
- **Synapse Schema**: [ai-env/schemas/synapse_schema.md](./ai-env/schemas/synapse_schema.md)
- **AI Personas**: [ai-env/personas/](./ai-env/personas/)

---
_Auto-loaded for Warp Agent via WARP.md_
