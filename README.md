# Sentient Alpha Trading Bot

**Status:** Active | **Architecture:** Monorepo (Node/React/Python)

## 📌 Project Overview

Sentient Alpha is an autonomous trading system that uses a committee of AI agents to analyze markets on Kalshi, debate strategies, simulation outcomes, and execute trades.

**For a detailed architectural breakdown, see [blueprint.md](./blueprint.md).**

## 📂 Structure

- **/frontend**: React + Vite + TailwindCSS application (The "Cockpit").
- **/backend**: Node.js + Express orchestrator (The "Nervous System").
- **/engine**: Python 3.12 + Asyncio AI Logic (The "Brain").
- **/shared**: Shared TypeScript types and constants.
- **/logs**: System logs and output streams.

## 🚀 Quick Start

### 1. Prerequisites

- Node.js (v18+)
- Python 3.12+ (with virtualenv)
- Supabase Account
- API Keys (Gemini, Groq, Kalshi) in `.env`

### 2. Setup

```bash
# Install Node dependencies (Root + Sub-packages)
npm install

# Setup Python Environment
cd engine
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..
```

### 3. Running the System

We use PM2 to orchestrate all services.

```bash
# Start Backend, Frontend, and Engine
npm run dev
```

_Access the dashboard at http://localhost:3000_
