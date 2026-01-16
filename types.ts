export enum AgentStatus {
  IDLE = 'IDLE',
  WORKING = 'WORKING',
  WARNING = 'WARNING',
  CRITICAL = 'CRITICAL',
  SUCCESS = 'SUCCESS'
}

export interface Agent {
  id: number;
  name: string;
  role: string;
  description: string;
  status: AgentStatus;
  lastAction: string;
  model: string;
  hidden?: boolean;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  agentId: number;
  cycleId: number; 
  phaseId?: number; // Added to override default agent-to-phase mapping
  level: 'INFO' | 'WARN' | 'ERROR' | 'SUCCESS';
  message: string;
}

export interface MarketAnalysis {
  market: string;
  optimist: string;
  pessimist: string;
  verdict: string;
  confidence: number;
}

export interface DebateResponse {
  optimistArg: string;
  pessimistArg: string;
  judgeVerdict: string;
  confidenceScore: number;
}

export interface ErrorAnalysis {
  rootCause: string;
  suggestedFix: string;
  confidence: number;
}