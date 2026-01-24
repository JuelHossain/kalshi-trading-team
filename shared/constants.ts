import { Agent, AgentStatus } from './types';

// 4 MEGA-AGENTS: The Pillars of Profit
export const AGENTS: Agent[] = [
  {
    id: 1,
    name: 'Soul',
    role: 'System, Memory & Evolution',
    description: 'Executive Director. Pre-flight, self-optimization, safety enforcement.',
    status: AgentStatus.WORKING,
    lastAction: 'System initialization',
    model: 'Gemini 1.5 Pro',
  },
  {
    id: 2,
    name: 'Senses',
    role: 'Surveillance & Signal Detection',
    description: '24/7 Observer. Passive scanning, odds sync, value gap detection.',
    status: AgentStatus.IDLE,
    lastAction: 'Scanning markets',
    model: 'Python/Asyncio',
  },
  {
    id: 3,
    name: 'Brain',
    role: 'Intelligence & Decision',
    description: 'Decision Maker. AI debate, Monte Carlo simulation, confidence scoring.',
    status: AgentStatus.IDLE,
    lastAction: 'Awaiting opportunities',
    model: 'Gemini 1.5 Pro',
  },
  {
    id: 4,
    name: 'Hand',
    role: 'Precision Strike & Vault',
    description: 'Tactical Executioner. Snipe, Kelly sizing, execution, vault lock.',
    status: AgentStatus.IDLE,
    lastAction: 'Standing by',
    model: 'Kalshi V2',
  },
];

export const MOCK_LOGS: string[] = [
  'Soul: Pre-flight handshake complete. All APIs online.',
  'Soul: Loaded 24h history. 3 wins, 1 loss. Evolving instructions...',
  'Senses: Scanning 42 active markets. Zero token cost.',
  'Senses: Value Gap Alert! Kalshi 45% vs Vegas 52%. Delta +7%.',
  'Brain: Opportunity queued. Running internal debate...',
  'Brain: Confidence 87%. Simulation variance 14%. Pushing to execution.',
  'Hand: Snipe check passed. Entry at $0.46 with zero slippage.',
  'Hand: Order executed. Profit $12.50. Vault locked at $350.',
];

export const WORKFLOW_STEPS: Record<number, string> = {
  1: 'SOUL: Pre-flight handshake, evolution, safety enforcement...',
  2: 'SENSES: Passive surveillance, odds sync, value gap detection...',
  3: 'BRAIN: AI debate, Monte Carlo simulation, decision scoring...',
  4: 'HAND: Snipe check, Kelly sizing, execution, vault lock...',
};

// 4-Phase Configuration (One per Mega-Agent)
export const PHASE_ORDER = [1, 2, 3, 4] as const;

export interface PhaseConfig {
  id: number;
  title: string;
  subtitle: string;
  color: string;
  borderColor: string;
  icon: string;
  bg: string;
  requiredAgents: number[];
}

export const PHASES: Record<number, PhaseConfig> = {
  1: {
    id: 1,
    title: 'SOUL',
    subtitle: 'System & Evolution',
    color: 'text-purple-400',
    borderColor: 'border-purple-500/30',
    icon: '👁️',
    bg: 'bg-purple-900/10',
    requiredAgents: [1],
  },
  2: {
    id: 2,
    title: 'SENSES',
    subtitle: 'Surveillance',
    color: 'text-blue-400',
    borderColor: 'border-blue-500/30',
    icon: '📡',
    bg: 'bg-blue-900/10',
    requiredAgents: [2],
  },
  3: {
    id: 3,
    title: 'BRAIN',
    subtitle: 'Intelligence',
    color: 'text-pink-400',
    borderColor: 'border-pink-500/30',
    icon: '🧠',
    bg: 'bg-pink-900/10',
    requiredAgents: [3],
  },
  4: {
    id: 4,
    title: 'HAND',
    subtitle: 'Execution',
    color: 'text-emerald-400',
    borderColor: 'border-emerald-500/30',
    icon: '✋',
    bg: 'bg-emerald-900/10',
    requiredAgents: [4],
  },
};

// Emergency intervention phase (error handling)
export const INTERVENTION_PHASE: PhaseConfig = {
  id: 99,
  title: 'INTERVENTION',
  subtitle: 'Error Recovery',
  color: 'text-red-500',
  borderColor: 'border-red-500/50',
  icon: '🔧',
  bg: 'bg-red-900/20',
  requiredAgents: [],
};
