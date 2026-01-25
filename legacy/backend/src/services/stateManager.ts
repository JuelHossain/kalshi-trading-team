import { LogEntry } from '@shared/types';
import { CONFIG } from '../config';

export interface SystemState {
  isProcessing: boolean;
  cycleCount: number;
  logs: LogEntry[];
  activeAgentId: number | null;
  completedAgents: number[];
  agentData: Record<number, any>;
  killSwitchActive: boolean;
}

export class StateManager {
  private state: SystemState;

  constructor() {
    this.state = {
      isProcessing: false,
      cycleCount: 0,
      logs: [],
      activeAgentId: null,
      completedAgents: [],
      agentData: {},
      killSwitchActive: false,
    };
  }

  getState(): SystemState {
    return { ...this.state };
  }

  updateState(updates: Partial<SystemState>): void {
    this.state = { ...this.state, ...updates };
  }

  addLog(log: LogEntry): void {
    this.state.logs = [...this.state.logs.slice(-CONFIG.LOG_LIMIT), log];
  }

  setAgentData(agentId: number, data: any): void {
    this.state.agentData[agentId] = data;
  }

  reset(): void {
    this.state.isProcessing = false;
    this.state.activeAgentId = null;
  }

  activateKillSwitch(): void {
    this.state.killSwitchActive = true;
    this.state.isProcessing = false;
    this.state.activeAgentId = null;
  }

  deactivateKillSwitch(): void {
    this.state.killSwitchActive = false;
  }
}
