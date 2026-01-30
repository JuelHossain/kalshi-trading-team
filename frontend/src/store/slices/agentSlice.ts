import { StateCreator } from 'zustand';

export type AgentStatus = 'idle' | 'active' | 'error' | 'veto' | 'processing';

export interface AgentState {
  agentId: number;
  name: string;
  role: string;
  status: AgentStatus;
  metrics: Record<string, number | string>;
  lastAction: string;
  lastUpdated: string;
  color: string;
}

export interface DataFlowTransition {
  id: string;
  fromAgent: number;
  toAgent: number;
  flowType: 'authorization' | 'opportunity' | 'decision' | 'execution';
  timestamp: string;
  data?: any;
  active: boolean;
}

export interface AgentSlice {
  agentStates: Record<number, AgentState>;
  activeTransitions: DataFlowTransition[];
  setAgentState: (agentId: number, updates: Partial<AgentState>) => void;
  addTransition: (transition: DataFlowTransition) => void;
  clearTransitions: () => void;
  getActiveAgent: () => AgentState | null;
  initializeAgents: () => void;
}

export const createAgentSlice: StateCreator<AgentSlice> = (set, get) => ({
  agentStates: {
    1: {
      agentId: 1,
      name: 'SOUL',
      role: 'Executive Director',
      status: 'idle',
      metrics: { balance: 0, cyclesCompleted: 0 },
      lastAction: 'System ready',
      lastUpdated: new Date().toISOString(),
      color: '#f59e0b',
    },
    2: {
      agentId: 2,
      name: 'SENSES',
      role: 'Surveillance',
      status: 'idle',
      metrics: { marketsScanned: 0, opportunitiesFound: 0 },
      lastAction: 'Awaiting cycle',
      lastUpdated: new Date().toISOString(),
      color: '#06b6d4',
    },
    3: {
      agentId: 3,
      name: 'BRAIN',
      role: 'Intelligence',
      status: 'idle',
      metrics: { confidence: 0, simulationsRun: 0 },
      lastAction: 'Awaiting opportunities',
      lastUpdated: new Date().toISOString(),
      color: '#a855f7',
    },
    4: {
      agentId: 4,
      name: 'HAND',
      role: 'Execution',
      status: 'idle',
      metrics: { ordersExecuted: 0, pendingOrders: 0 },
      lastAction: 'Standing by',
      lastUpdated: new Date().toISOString(),
      color: '#10b981',
    },
  },
  activeTransitions: [],

  setAgentState: (agentId, updates) =>
    set((state) => ({
      agentStates: {
        ...state.agentStates,
        [agentId]: {
          ...state.agentStates[agentId],
          ...updates,
          lastUpdated: new Date().toISOString(),
        },
      },
    })),

  addTransition: (transition) =>
    set((state) => ({
      activeTransitions: [...state.activeTransitions.slice(-49), transition],
    })),

  clearTransitions: () => set({ activeTransitions: [] }),

  getActiveAgent: () => {
    const states = Object.values(get().agentStates);
    return states.find((a) => a.status === 'active' || a.status === 'processing') || null;
  },

  initializeAgents: () =>
    set({
      agentStates: {
        1: {
          agentId: 1,
          name: 'SOUL',
          role: 'Executive Director',
          status: 'idle',
          metrics: { balance: 0, cyclesCompleted: 0 },
          lastAction: 'System ready',
          lastUpdated: new Date().toISOString(),
          color: '#f59e0b',
        },
        2: {
          agentId: 2,
          name: 'SENSES',
          role: 'Surveillance',
          status: 'idle',
          metrics: { marketsScanned: 0, opportunitiesFound: 0 },
          lastAction: 'Awaiting cycle',
          lastUpdated: new Date().toISOString(),
          color: '#06b6d4',
        },
        3: {
          agentId: 3,
          name: 'BRAIN',
          role: 'Intelligence',
          status: 'idle',
          metrics: { confidence: 0, simulationsRun: 0 },
          lastAction: 'Awaiting opportunities',
          lastUpdated: new Date().toISOString(),
          color: '#a855f7',
        },
        4: {
          agentId: 4,
          name: 'HAND',
          role: 'Execution',
          status: 'idle',
          metrics: { ordersExecuted: 0, pendingOrders: 0 },
          lastAction: 'Standing by',
          lastUpdated: new Date().toISOString(),
          color: '#10b981',
        },
      },
    }),
});
