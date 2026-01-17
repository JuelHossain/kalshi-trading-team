# Kalshi Command Center Dashboard

**Persona**: UI & Visuals Developer
**Mission**: Visualizing the collaborative intelligence of the trading bot swarm.

## Features
- **Dark Mode**: Hacker-aesthetic interface (Port 8501).
- **Reasoning Trace**: Real-time scrolling log of agent thoughts and trades.
- **PnL Calendar**: Visual heatmap of daily profit/loss.
- **Vault Status**: Live gauges tracking Principal vs. House Money.

## Setup
1. Ensure `python3` and `pip` are installed:
   ```bash
   sudo apt install python3-pip
   ```
2. Run the dashboard:
   ```bash
   ./run_dashboard.sh
   ```

## Configuration
- Reads `SUPABASE_URL` and `SUPABASE_KEY` from `../backend/.env`.
- Ensure the backend infrastructure is initialized so tables (`balance_history`, `trade_history`) exist.
