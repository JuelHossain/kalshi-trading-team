# Design Guide - Sentient Alpha

This document defines the architecture, design language, and coding conventions for the Sentient Alpha Trading Bot.

## 1. Architectural Patterns

### 2-Tier Reality
The system is strictly divided into two layers:
1.  **Passive/Autonomous Engine (Python)**: Handles all market surveillance, AI decision-making (Gemini 1.5 Pro), and trade execution.
2.  **Interactive Interface (React)**: Provides real-time visibility into the Engine's internal states and allows manual overrides.

### The 4 Mega-Agents
All core logic must reside within one of the 4 Pillars:
- **SOUL**: Project Executive. Manages **Autopilot Logic**, system-wide authorization, and Gemini self-evolution.
- **SENSES**: Scanning, Surveillance, and Market Context Retrieval.
- **BRAIN**: AI Debates (Optimist/Critic) and Monte Carlo Simulation.
- **HAND**: Tactical Execution, Capital Sizing, and Safety Protocol.

## 2. Frontend Standards

- **State Management**: **Zustand**. Do not use `useState` for global orchestrator state.
- **Components**: **Shadcn UI**. Standardized cards, buttons, and layouts for a "Cinematic Terminal" feel.
- **Styling**: Tailwind CSS + custom glassmorphism.
- **Visualization**: Recharts for PnL and Heatmaps.
- **Real-time**: Unidirectional SSE stream from Engine port 3002.

## 3. Engine Standards (Python)

- **Framework**: `asyncio` for all I/O, `aiohttp.web` for API endpoints.
- **Persistence**: **Synapse** (Persistent SQLite Queue) for inter-agent signals (Opps/Signals).
- **Communication**: Internal `EventBus` for triggers; Synapse for data handoff.
- **Diagnostics**: Independent agent taps (e.g., `brain_tap.py`) for isolated testing.
- **Safety**: Ragnarok Protocol and Autopilot Control managed via the Executive (Soul).

## 4. Coding Conventions

| Context | Pattern |
| :--- | :--- |
| **Classes** | `PascalCase` |
| **Functions/Vars** | `camelCase` (JS) / `snake_case` (Python) |
| **Constants** | `UPPER_SNAKE_CASE` |
| **File Names** | `kebab-case.tsx` / `snake_case.py` |

## 5. Deployment Lifecycle

1.  **Development**: `npm run dev` (starts Frontend on 3000, Engine on 3002).
2.  **Production**: Managed via `ecosystem.config.cjs` using PM2.
3.  **Environment**: Secrets loaded from `.env` (managed by `Soul` agent variables).

---
_Design Standards Locked - Sentient Alpha Core_
