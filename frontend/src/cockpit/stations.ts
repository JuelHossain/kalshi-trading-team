/**
 * The four agents as the orrery sees them. Add an agent by adding a row:
 * the orbit, time axis, throw sequence and history all derive from this.
 */
import type { LucideIcon } from 'lucide-react';
import { Cpu, Eye, Send, Shield } from 'lucide-react';

export interface StationDef {
  name: string;
  role: string;
  icon: LucideIcon;
  model: string;
  /** Fallback working time in ms, used only until the agent has completed
   *  a run this session; after that the median measured time takes over. */
  dur: number;
  payload: string;
  lane: number;
  art: number;
  /** The engine's agent_id in SYSTEM_LOG events. */
  agentId: number;
}

export const STATIONS: StationDef[] = [
  {
    name: 'Soul',
    role: 'Authorization',
    icon: Shield,
    model: 'pre-flight · vault rails',
    dur: 4000,
    payload: 'authorization',
    lane: 0,
    art: 0,
    agentId: 1,
  },
  {
    name: 'Senses',
    role: 'Surveillance',
    icon: Eye,
    model: 'Kalshi markets · close window',
    dur: 20000,
    payload: 'shortlist',
    lane: 1,
    art: 1,
    agentId: 2,
  },
  {
    name: 'Brain',
    role: 'Deliberation',
    icon: Cpu,
    model: 'Gemini · search grounded',
    dur: 15000,
    payload: 'verdict',
    lane: 0,
    art: 2,
    agentId: 3,
  },
  {
    name: 'Hand',
    role: 'Execution',
    icon: Send,
    model: 'Kalshi orders',
    dur: 5000,
    payload: 'fill receipt',
    lane: 1,
    art: 3,
    agentId: 4,
  },
];

export const N = STATIONS.length;

/** Transit beats are purely visual and keep the prototype's timing. */
export const THROW_MS = 1500;
export const FLARE_MS = 560;
export const SIGNAL_MS = 1300;
export const RETRY_MS = 2100;

/** The execution queue's cap in the engine (MAX_EXECUTION_QUEUE_SIZE). */
export const STORE_CAP = 10;

export const WORK_VERBS = ['authorizing the cycle', 'sweeping the board', 'deliberating', 'placing the order'];

export const agentIndexFor = (agentId: number): number =>
  STATIONS.findIndex((s) => s.agentId === agentId);
