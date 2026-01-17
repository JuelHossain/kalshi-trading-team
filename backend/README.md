# 🧠 Sentient Alpha Engine (Backend)

The **Sentient Alpha Engine** is a headless autonomous trading intelligence designed for the **Kalshi V2 API**. It orchestrates 13 specialized AI agents through a multi-phase trading funnel, utilizing Google Gemini for advanced reasoning and RSA-SHA256 for secure transaction signing.

## 🚀 Core Architecture

The backend operates as a standalone Node.js service that handles the "heavy lifting" of market analysis, risk management, and execution.

### 🎭 The 13 Specialized Agents
1.  **Ghost (Agent 1)**: The Security Protocol. Authorizes all final executions.
2.  **Scout (Agent 2)**: Surveillance specialist. Scans Kalshi for high-probability markets.
3.  **Interceptor (Agent 3)**: Signal Intelligence. Monitors external data (Vegas Odds, News etc.).
4.  **Analyst (Agent 4)**: The Brain. Conducts internal debates between "Optimist" and "Pessimist" personas.
5.  **Scientist (Agent 5)**: The Simulator. Runs Monte Carlo simulations for probability edge.
6.  **Auditor (Agent 6)**: Compliance & Logic. Peer-reviews the Analyst's verdict.
7.  **Sniper (Agent 7)**: Liquidity Expert. Analyzes order books for slippage and spread.
8.  **Executioner (Agent 8)**: The Trader. Manages RSA authentication and order placement.
9.  **Accountant (Agent 9)**: Portfolio Manager. Monitors bankroll and position sizing.
10. **Historian (Agent 10)**: Memory Module. Logs all activities to Supabase for long-term learning.
11. **Mechanic (Agent 11)**: System Health. Monitors API connectivity and latency.
12. **Ragnarok (Agent 12)**: The Fail-Safe. Liquidates positions in catastrophic scenarios.
13. **Fixer (Agent 13)**: Self-Healing. Analyzes system errors and suggests real-time code fixes.

## 🛠 Tech Stack
- **Runtime**: Node.js (ESM)
- **Language**: TypeScript
- **API Framework**: Express
- **Security**: jsrsasign (RSA-SHA256 Signing)
- **AI Models**: Google Generative AI (Gemini 3 Flash)
- **Database**: Supabase (PostgreSQL)

## 📡 API Endpoints
- `GET /api/stream`: SSE (Server-Sent Events) endpoint for real-time log and state streaming.
- `POST /api/run`: Triggers a new autonomous trading cycle.

## 🚦 Getting Started
1. Ensure your `.env` is configured with `KALSHI_PROD_KEY_ID` and `KALSHI_PROD_PRIVATE_KEY`.
2. Run `npm install`.
3. Start the engine: `npm run dev`.
