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
  /** Expected working time in ms. Drives the progress arc until the real
   *  completion event arrives; the engine's own timing is what History shows. */
  dur: number;
  payload: string;
  /** How many items a completed throw leaves in the store. */
  depth: number;
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
    model: 'vault rails · pre-flight',
    dur: 4000,
    payload: 'authorization',
    depth: 1,
    lane: 0,
    art: 0,
    agentId: 1,
  },
  {
    name: 'Senses',
    role: 'Surveillance',
    icon: Eye,
    model: 'kalshi-rest · close window',
    dur: 20000,
    payload: 'shortlist',
    depth: 10,
    lane: 1,
    art: 1,
    agentId: 2,
  },
  {
    name: 'Brain',
    role: 'Deliberation',
    icon: Cpu,
    model: 'gemini-3.8-flash · grounded',
    dur: 15000,
    payload: 'verdict',
    depth: 1,
    lane: 0,
    art: 2,
    agentId: 3,
  },
  {
    name: 'Hand',
    role: 'Execution',
    icon: Send,
    model: 'kalshi-rest · paper fills',
    dur: 5000,
    payload: 'fill receipt',
    depth: 0,
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
