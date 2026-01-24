# Design Guide for Kalshi Trading Team Project

This document outlines the design language, coding conventions, architectural patterns, and standards for the Kalshi Trading Team project (Sentient Alpha Trading Bot). It serves as a reference for all future agents and developers working on this project to ensure consistency, maintainability, and adherence to best practices.

Based on analysis of the current codebase and guidelines from OpenCode documentation, this guide establishes the "locked" design standards.

## Overview
The project is a monorepo AI-driven autonomous trading system for Kalshi prediction markets, featuring:
- **Frontend**: React + Vite + TailwindCSS dashboard
- **Backend**: Node.js + Express orchestration layer
- **Engine**: Python asyncio-based AI agent system
- **Shared**: TypeScript types and constants

## Architectural Patterns
- **Monorepo Structure**: Root-level npm management with sub-packages for frontend/backend.
- **Agent-Based AI**: Modular agents (Soul, Senses, Brain, Hand) with specific roles, communicating via event bus.
- **Event-Driven Communication**: SSE for real-time updates, async queues for decoupling.
- **Microservices-Inspired**: Separated concerns between UI, API, and core logic.
- **Security-First**: Sentinel agents for auditing, kill switches, and risk management.

## Code Style and Standards
- **TypeScript Strict Mode**: Enabled for all TS/JS code.
- **Async/Await**: Preferred over promises/callbacks.
- **Modularity**: Small, focused modules; clear separation of concerns.
- **Error Handling**: Centralized logging, recovery mechanisms.
- **Testing**: Vitest for JS/TS; consider adding pytest for Python.
- **Linting/Formatting**: Use ESLint, Prettier for JS/TS; Black for Python (add if missing).
- **Documentation**: Inline comments, docstrings, READMEs per major folder.

## Naming Conventions
- **TypeScript/JavaScript**:
  - Components/Interfaces/Enums/Types: PascalCase (e.g., `AgentCard`, `LogEntry`)
  - Variables/Functions/Hooks/Files: camelCase (e.g., `useAuth`, `handleLogin`)
  - Constants: UPPER_CASE (e.g., `AGENTS`)
- **Python**:
  - Classes: PascalCase (e.g., `BaseAgent`)
  - Functions/Variables/Modules: snake_case (e.g., `run_soul`)
- **Files**: Kebab-case for components, snake_case for Python.

## Folder Structures
- **Root**: frontend/, backend/, engine/, shared/, scripts/, configs/
- **Frontend/src**: components/, hooks/, __tests__/
- **Backend/src**: agents/, services/, supabase/
- **Engine**: agents/, core/, main.py
- **Shared**: types.ts, constants.ts

## Frontend Patterns (React/Vite/Tailwind)
- **Components**: Functional with hooks, TypeScript interfaces for props.
- **Styling**: Tailwind utility classes; custom CSS for themes (e.g., dark mode, glassmorphism).
- **State**: React hooks; custom hooks for complex logic.
- **Data Viz**: Recharts for charts.
- **APIs**: Fetch for REST, SSE for real-time.
- **Routing**: Conditional rendering (no router lib).
- **Testing**: Vitest + React Testing Library.

## Backend Patterns (Node/Express)
- **APIs**: REST with JWT auth; SSE streams.
- **Modules**: Async functions/classes; services for integrations.
- **Database**: Supabase; custom services for data.
- **Real-Time**: SSE to frontend; HTTP to Python engine.
- **Security**: JWT, API keys, Sentinel audits.

## Engine Patterns (Python)
- **Framework**: asyncio + aiohttp.
- **Agents**: Class inheritance from BaseAgent.
- **Concurrency**: Queues, event bus, periodic ticks.
- **Logging**: JSON/colored output, heartbeats.
- **APIs**: HTTP endpoints, SSE broadcasting.

## Shared Components
- **Purpose**: Common types/constants to avoid duplication.
- **Contents**: TS interfaces, enums, agent configs.
- **Imports**: Via @shared/* paths.

## Development Workflow
- **Initialization**: Run `/init` in OpenCode to generate AGENTS.md for project understanding.
- **Commits**: Follow conventional commit messages; commit AGENTS.md.
- **Deployment**: PM2 for process management.
- **Environment**: .env for secrets; paper/prod modes.
- **Version Control**: Git; consider branching strategies if missing.

## Best Practices
- No direct file mutations outside tools.
- Privacy-first: No storage of sensitive data.
- Scalability: Modular design for adding agents/features.
- Performance: Async patterns, efficient data structures.
- Accessibility: Consider in UI components.

This design guide is "locked" as the standard for this project. All future changes must adhere to these patterns. For questions or updates, refer to the project maintainers.

Generated based on codebase analysis and OpenCode best practices.