---
name: design-guide
description: Architectural patterns and coding standards for the Sentient Alpha project
---

# Design Guide for Sentient Alpha Project

This skill outlines the design language, coding conventions, and architectural patterns. All agents must adhere to these standards to ensure a cohesive 2-tier system.

## Architectural Patterns

- **2-Tier Structure**: Direct communication between React Frontend and Python Engine.
- **Mega-Agent Pillars**: Core logic resides in 4 discrete agents:
  - **SOUL**: Executive Lead. Manages Autopilot Pulse and system authorization.
  - **SENSES**: Scanning and real-time market context fetching.
  - **BRAIN**: AI-driven debate and Monte Carlo simulation.
  - **HAND**: Tactical strike execution and capital protection.
- **Persistence**: **Synapse** (SQLite) for persistent inter-agent signals.
- **Safety-First**: Ragnarok Protocol and automated vetos.

## Folder Structures

- **Root**: `frontend/`, `engine/`, `shared/`, `walkthroughs/`, `legacy/`
- **Frontend/src**: `components/` (Shadcn), `store/` (Zustand), `hooks/` (Data)
- **Engine**: `agents/`, `core/` (Synapse, Bus), `diagnostics/` (Tap scripts)
- **Shared**: Common Typescript interfaces.

## Frontend Patterns (React/Vite)

- **UI Components**: Use **Shadcn UI** as the base. Maintain "Glassmorphism" aesthetic.
- **State Management**: **Zustand** is the source of truth for global state.
- **APIs**: All calls must use the relative `/api` proxy leading to port 3002.
- **SSE**: Real-time log streaming via `/api/stream`.

## Engine Patterns (Python)

- **Framework**: `asyncio` + `aiohttp.web`.
- **Communication**: Trigger events via `EventBus`. Persistent data via `Synapse`.
- **AI Stack**: Google GenAI SDK (v1.0+) using Gemini 1.5 Pro.
- **Safety**: Ragnarok liquidation protocol and Autopilot Pulse compliance.

## Naming Conventions

- **JS/TS**: PascalCase for components, camelCase for variables/functions.
- **Python**: PascalCase for classes, snake_case for methods/functions.
- **Files**: kebab-case for components, snake_case.py for engine modules.

## Development Workflow

- **Diagnostics**: Use `engine/diagnostics/` (e.g., `brain_tap.py`) for isolated tests.
- **Walkthroughs**: Record every major logic change in a new walkthrough file.
- **Safety**: Always build and deploy to verify changes in the UI.

---
_Generated based on 2-tier architectural consolidation._