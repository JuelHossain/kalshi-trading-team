import { Agent, AgentStatus } from './types';

export const AGENTS: Agent[] = [
  { id: 1, name: 'The Team Lead', role: 'Orchestrator', description: 'Manages loop & Recursive Vault. Locks $300 principal at $50 profit.', status: AgentStatus.WORKING, lastAction: 'Monitoring profit target', model: 'Python Asyncio' },
  { id: 2, name: 'The Scout', role: 'Harvester', description: 'Filters active markets with >$2k Open Interest.', status: AgentStatus.WORKING, lastAction: 'Scanning Kalshi WS', model: 'Groq/Llama 3.1 70B' },
  { id: 3, name: 'Signal Interceptor', role: 'Scraper', description: 'Detects Delta > 5% vs Pinnacle/Vegas odds.', status: AgentStatus.IDLE, lastAction: 'Comparing implied probs', model: 'RapidAPI' },
  { id: 4, name: 'The Analyst', role: 'Gemini Brain', description: 'Context Assembly & Chain-of-Thought Scoring.', status: AgentStatus.IDLE, lastAction: 'Ready for hypothesis', model: 'Gemini 1.5 Pro' },
  { id: 5, name: 'Sim Scientist', role: 'Simulator', description: 'Runs 10,000 Monte Carlo iterations for EV.', status: AgentStatus.IDLE, lastAction: 'Awaiting hypothesis', model: 'Numpy/Github Actions' },
  { id: 6, name: 'The Auditor', role: 'Pessimist', description: 'Trap Detection & Veto Power (Prob < 60%).', status: AgentStatus.WORKING, lastAction: 'Auditing spreads', model: 'Llama 3.1 405B' },
  { id: 7, name: 'The Sniper', role: 'Order Book', description: 'Whale Watching & Resistance Analysis.', status: AgentStatus.WORKING, lastAction: 'Monitoring depth', model: 'Python/WS' },
  { id: 8, name: 'The Executioner', role: 'Assassin', description: 'Kelly Criterion Sizing & Limit Orders.', status: AgentStatus.IDLE, lastAction: 'Awaiting kill command', model: 'Kalshi API' },
  { id: 9, name: 'The Accountant', role: 'Sentinel', description: 'Token counting & Budget audit (< $1.15/day).', status: AgentStatus.SUCCESS, lastAction: 'Spend: $0.42 today', model: 'Logic' },
  { id: 10, name: 'The Historian', role: 'Memory', description: 'Post-Mortem analysis & RAG updates.', status: AgentStatus.WORKING, lastAction: 'Indexing trade #4029', model: 'Supabase' },
  { id: 11, name: 'The Mechanic', role: 'Healer', description: 'Heartbeat, Key Rotation & Auto-Restart.', status: AgentStatus.SUCCESS, lastAction: 'API Health 100%', model: 'System' },
  { id: 12, name: 'The Visualist', role: 'UI Engineer', description: 'Interactive PnL Calendar, Live Trace & Vault Gauge.', status: AgentStatus.WORKING, lastAction: 'Rendering Dashboard', model: 'React/Streamlit' },
  { id: 13, name: 'The Fixer', role: 'Debugger', description: 'Runtime Exception Interceptor. Deploys Hotfixes.', status: AgentStatus.IDLE, lastAction: 'Standby (Hidden)', model: 'Gemini 3 Flash', hidden: true },
];

export const MOCK_LOGS: string[] = [
  "Agent 2: Scanned 42 active markets. Found 3 candidates > $2k liquidity.",
  "Agent 3: Shadow Odds Alert! Kalshi 45% vs Vegas 52%. Delta +7%.",
  "Agent 9: Current daily spend $0.42. Budget operating at 36%.",
  "Agent 6: VETO. Market #291 has irregular whale movement. Suspected trap.",
  "Agent 5: Simulating 10,000 runs... EV: +$12.50. Variance: 14%.",
  "Agent 7: Sniper entry found at $0.46. Front-running order ID #992.",
  "Agent 1: Profit target $50.00 hit. Locking $300 Principal. Trading House Money.",
  "Agent 11: Rate limit warning. Rotating to Backup API Key C.",
  "Agent 4: Hypothesis confirmed. Injuries weight 40% favors YES.",
  "Agent 10: RAG updated. 'Avoid low liquidity NBA props' rule added.",
];

export const WORKFLOW_STEPS: Record<number, string> = {
  1: "Orchestrating new trade cycle. Waking up the Squad...",
  2: "Scanning 150+ markets for liquidity > $2k...",
  3: "Cross-referencing Vegas Odds. Delta found: +6.5%...",
  4: "Convening Committee Debate (Optimist vs Pessimist)...",
  5: "Running 10k Monte Carlo Sims. EV Score: 8.2...",
  6: "Auditing for Bull Traps. No manipulation detected...",
  7: "Scanning Order Book. Wall detected at 48c...",
  8: "Kelly Criterion Sizing. Executing Limit Order @ 47c...",
  9: "Auditing token usage. Cost: $0.0012...",
  10: "Logging transaction #4092 to Supabase Memory...",
  11: "Health Check Passed. Rotating API Key...",
  12: "Re-rendering Dashboard with live stats...",
  13: "INTERCEPTING ERROR. Analyzing Stack Trace & Patching...",
};