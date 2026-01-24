# AGENTS.md - Kalshi Trading Team Project Guidelines

This file outlines the coding standards, tools, and rules for all agents and developers working on the Kalshi Trading Team project. Follow these guidelines to maintain code quality, consistency, and beauty across the entire codebase.

## Project Overview
- **Type**: Monorepo with TypeScript/JavaScript (frontend/backend/shared) and Python (engine)
- **Architecture**: AI-driven trading system with modular agents
- **Tools**: ESLint, Prettier, Ruff, Black, Husky

## Coding Standards

### General Rules
- **Language Consistency**: Use TypeScript for JS/TS parts, Python 3.12+ for engine
- **Naming**: PascalCase for components/classes, camelCase for variables/functions, snake_case for Python
- **Imports**: Absolute paths with @shared/* aliases
- **Error Handling**: Try-catch with meaningful messages, no silent failures
- **Documentation**: JSDoc for functions, inline comments for complex logic

### TypeScript/JavaScript
- **Strict Mode**: Enabled, no `any` types (warnings allowed during transition)
- **React**: Functional components with hooks, proper prop interfaces
- **Styling**: Tailwind CSS with custom utilities, consistent spacing
- **Testing**: Vitest for unit tests, follow existing patterns

### Python
- **Style**: Black formatting (100 char lines), Ruff linting
- **Async**: Use asyncio for all I/O operations
- **Typing**: Type hints required, no bare `Any`
- **Imports**: Follow PEP8, no wildcard imports

## Tools & Automation
- **Linting**: `npm run lint` (runs ESLint + Ruff)
- **Formatting**: `npm run format` (Prettier + Black)
- **Pre-commit**: Husky runs linting on commits
- **Build**: `npm run build` for all components
- **Dev**: `npm run dev` starts all services

## File Structure
- `frontend/`: React app (Vite, Tailwind)
- `backend/`: Node/Express API (TypeScript)
- `engine/`: Python AI agents (asyncio)
- `shared/`: Common types/constants
- `DESIGN_GUIDE.md`: Architectural standards

## Agent-Specific Rules
- **Frontend Agents**: Focus on UI/UX, accessibility, responsive design
- **Backend Agents**: API design, security, performance
- **Engine Agents**: AI logic, async efficiency, error resilience
- **All Agents**: Follow DESIGN_GUIDE.md, commit clean code, test changes

## Quality Gates
- No ESLint errors (warnings minimized)
- No Ruff/Black formatting issues
- Tests pass before commit
- Code reviewed for consistency

## Commands Reference
- `npm run lint`: Lint all code
- `npm run format`: Format all code
- `npm run test`: Run all tests
- `npm run dev`: Start development environment
- `npm run build`: Build for production

Follow these rules to ensure the codebase remains beautiful, flawless, and maintainable. Refer to DESIGN_GUIDE.md for detailed patterns.