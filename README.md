# Sentient Alpha Trading Bot

**Status:** Active | **Architecture:** 2-Tier (React/Python)

## 📌 Project Overview

Sentient Alpha is an autonomous trading system that uses a committee of 4 Mega-Agents (Soul, Senses, Brain, Hand) to analyze markets on Kalshi, debate strategies, simulate outcomes, and execute precision trades.

**For a detailed architectural breakdown, see [blueprint.md](./blueprint.md).**

## 📂 Structure

- **/frontend**: React + Vite + Zustand logic (The "Cockpit"). Displays real-time logs and PnL.
- **/engine**: Python 3.12 + Asyncio AI Logic (The "Brain"). Handles SSE streaming and REST API.
- **/shared**: Shared TypeScript types and constants.
- **/walkthroughs**: Historical proof-of-work and task documentations.
- **/legacy**: Archived components (old Node.js backend).

## 🚀 Quick Start

### 1. Prerequisites

- Node.js (v20+)
- Python 3.12+ 
- Supabase Account
- API Keys (Gemini, Kalshi) in `.env`

### 2. Setup

```bash
# Install Frontend dependencies
cd frontend
npm install
cd ..

# Setup Python Engine (Recommended in a venv)
pip install -r engine/requirements.txt
```

### 3. Running the System

We use PM2 to orchestrate the services.

```bash
# Start Frontend and Engine simultaneously
npm run dev
```

_Access the dashboard at http://localhost:3000_
_Engine API available at http://localhost:3002_

---
**Strict Compliance**: All agents must follow the [CONSTITUTION.md](./CONSTITUTION.md) and [AGENTS.md](./AGENTS.md).
