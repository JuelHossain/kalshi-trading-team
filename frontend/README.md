# 📟 Sentient Alpha HUD (Frontend)

The **Sentient Alpha HUD** is a premium, cyber-command interface designed to visualize and control the Sentient Alpha Trading Engine. It provides real-time visibility into the autonomous "funnel" process, terminal logging, and portfolio performance.

## 🌌 Visual Design System
The HUD utilizes a **"Neural Trace"** aesthetic:
- **Glassmorphism**: High-blur translucent panels with electromagnetic border glows.
- **Cyber-Terminal**: Custom monospaced logging with level-based color coding.
- **Performance Metrics**: Real-time balance, cycle counting, and PnL heatmaps.

## 🏗 Key Components
- **Terminal**: A high-performance log-streamer optimized for rapid AI output.
- **MarketAnalysis**: Deep-dive view of markets currently under "Analyst" debate.
- **SystemHealth**: Real-time status of API keys, engine connection, and agent health.

## 🔌 Connection Protocol
The frontend relies on a persistent **SSE (Server-Sent Events) Bridge** to the backend at `localhost:3001`. It remains "thin," meaning all trading logic is decoupled, allowing the UI to be highly responsive and purely focused on data visualization.

## 🛠 Tech Stack
- **Framework**: React 19
- **Build Tool**: Vite
- **Styling**: Tailwind CSS 4.0 (Modern Engine)
- **Charts**: Recharts (for PnL and Delta visualization)
- **Icons/Graphics**: Custom CSS patterns and SVG-based neural nodes.

## 🚦 Getting Started
1. Ensure the **Backend Engine** is running on `:3001`.
2. Run `npm install`.
3. Launch the HUD: `npm run dev`.
4. Open the HUD in your browser (typically `localhost:5173`).
