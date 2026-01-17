import { Agent, AgentStatus } from './types';

export const AGENTS: Agent[] = [
  { id: 1, name: 'Ghost', role: 'Strategic Authorization', description: 'Checks Kill Switch and Maintenance Windows.', status: AgentStatus.WORKING, lastAction: 'Authorizing cycles', model: 'Python 3.12' },
  { id: 2, name: 'Scout', role: 'Global Harvester', description: 'Filters active markets with >$2k liquidity.', status: AgentStatus.WORKING, lastAction: 'Scanning Kalshi', model: 'Python/Aiohttp' },
  { id: 3, name: 'Interceptor', role: 'Odds Sync', description: 'Detects Alpha vs Vegas/Shadow Odds.', status: AgentStatus.IDLE, lastAction: 'Polling RapidAPI', model: 'RapidAPI' },
  { id: 4, name: 'Analyst', role: 'Optimist Brain', description: 'Alpha Generation & Structural Reasoning.', status: AgentStatus.IDLE, lastAction: 'Ready for analysis', model: 'Gemini 1.5 Pro' },
  { id: 5, name: 'Scientist', role: 'Sim Engine', description: 'Runs 10,000 Monte Carlo iterations for EV.', status: AgentStatus.IDLE, lastAction: 'Awaiting data', model: 'NumPy' },
  { id: 6, name: 'Auditor', role: 'Pessimist Auditor', description: 'Risk Assessment & Veto Power.', status: AgentStatus.WORKING, lastAction: 'Auditing signals', model: 'Llama 3.1 70B' },
  { id: 7, name: 'Sniper', role: 'Orderbook Analyst', description: 'Depth Analysis & Spread Detection.', status: AgentStatus.WORKING, lastAction: 'Monitoring orderbook', model: 'Python/Kalshi' },
  { id: 8, name: 'Executioner', role: 'Silent Sniper', description: 'Kelly Sizing & Limit Order Execution.', status: AgentStatus.IDLE, lastAction: 'Standing by', model: 'Kalshi V2' },
  { id: 9, name: 'Accountant', role: 'Portfolio Audit', description: 'Budget monitoring & Vault updates.', status: AgentStatus.SUCCESS, lastAction: 'Balance audited', model: 'Python' },
  { id: 10, name: 'Historian', role: 'Event Archive', description: 'Archiving bus events to local history.', status: AgentStatus.WORKING, lastAction: 'Logging events', model: 'Async IO' },
  { id: 11, name: 'Mechanic', role: 'Health Monitor', description: 'System Diagnostics & Resource Tracking.', status: AgentStatus.SUCCESS, lastAction: 'Stats: CPU 12%', model: 'Psutil' },
  { id: 12, name: 'Ragnarok', role: 'Kill Switch', description: 'Global Emergency Shutdown Protocol.', status: AgentStatus.IDLE, lastAction: 'Armed', model: 'System' },
  { id: 13, name: 'Fixer', role: 'AI Debugger', description: 'Root Cause Analysis & Hotfix suggestions.', status: AgentStatus.IDLE, lastAction: 'Monitoring errors', model: 'Gemini 1.5 Pro', hidden: true },
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
  1: "GHOST: Verifying authorization and maintenance windows...",
  2: "SCOUT: Scanning Kalshi markets for high-liquidity active trades...",
  3: "INTERCEPTOR: Fetching RapidAPI shadow odds for delta discovery...",
  4: "ANALYST: Gemini Pro convening optimist alpha debate...",
  5: "SCIENTIST: NumPy running 10,000 Monte Carlo iterations...",
  6: "AUDITOR: Llama 3.1 70B performing risk audit and veto check...",
  7: "SNIPER: Analyzing orderbook depth and calculating snipe price...",
  8: "EXECUTIONER: Placing limit orders via RSA-signed V2 request...",
  9: "ACCOUNTANT: Auditing portfolio balance and daily spend limits...",
  10: "HISTORIAN: Archiving bus event stream to local cycle log...",
  11: "MECHANIC: Monitoring system resources (CPU/MEM/Latency)...",
  12: "RAGNAROK: Standing by for emergency kill signal...",
  13: "FIXER: AI-driven autonomous error recovery protocol...",
  14: "GATEWAY: Transmitting bus telemetry to dashboard bridge...",
};