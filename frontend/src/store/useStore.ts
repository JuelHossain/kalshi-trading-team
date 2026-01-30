import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { TimelineEvent, VaultState, SimulationState, SystemHealthData } from '../../shared/types';
import { createAgentSlice, AgentSlice } from './slices/agentSlice';
import { AuthMode } from '../components/Login';

interface User {
  id: string;
  email: string;
  name: string;
}

interface AppState extends AgentSlice {
  // Auth
  user: User | null;
  isAuthenticated: boolean;
  authMode: AuthMode | null;
  setAuthMode: (mode: AuthMode | null) => void;
  setAuthenticated: (isAuthenticated: boolean) => void;
  login: () => Promise<void>;
  logout: () => void;

  // Orchestrator State
  activeAgentId: number | null;
  completedAgents: number[];
  timelineEvents: TimelineEvent[];
  isProcessing: boolean;
  cycleCount: number;
  autoPilot: boolean;
  currentPhaseId: number;
  killSwitchActive: boolean;

  // Data States
  vault: VaultState | undefined;
  simulation: SimulationState | undefined;
  health: SystemHealthData | undefined;

  // Actions
  setTimelineEvents: (events: TimelineEvent[]) => void;
  addTimelineEvent: (event: TimelineEvent) => void;
  setIsProcessing: (isProcessing: boolean) => void;
  setCycleCount: (count: number) => void;
  setActiveAgentId: (id: number | null) => void;
  setCompletedAgents: (ids: number[]) => void;
  setKillSwitchActive: (active: boolean) => void;
  setAutoPilot: (active: boolean) => void;
  setVault: (vault: VaultState) => void;
  setSimulation: (sim: SimulationState) => void;
  setHealth: (health: SystemHealthData) => void;
}

// Storage key for auth persistence
const AUTH_STORAGE_KEY = 'sentient_alpha_auth';

export const useStore = create<AppState>()(
  devtools(
    persist(
      (set, get, api) => ({
        ...createAgentSlice(set, get, api),

        // Auth
        user: null,
        isAuthenticated: false,
        authMode: null,
        setAuthMode: (mode) => {
          set({ authMode: mode });
          // Persist to localStorage for immediate access
          if (mode) {
            localStorage.setItem(`${AUTH_STORAGE_KEY}_mode`, mode);
          } else {
            localStorage.removeItem(`${AUTH_STORAGE_KEY}_mode`);
          }
        },
        setAuthenticated: (isAuthenticated) => set({ isAuthenticated }),
        login: async () => {
          // Placeholder - will be replaced by actual API call in components or a thunk
          try {
            const res = await fetch('/api/auth', { method: 'POST' });
            const data = await res.json();
            if (data.isAuthenticated) {
              set({ user: data.user, isAuthenticated: true });
            }
          } catch (e) {
            console.error('Login failed', e);
          }
        },
        logout: () => {
          set({ user: null, isAuthenticated: false, authMode: null });
          localStorage.removeItem(`${AUTH_STORAGE_KEY}_mode`);
        },

        // Orchestrator Defaults
        activeAgentId: null,
        completedAgents: [],
        timelineEvents: [],
        isProcessing: false,
        cycleCount: 0,
        autoPilot: false,
        currentPhaseId: 0,
        killSwitchActive: false,
        vault: undefined,
        simulation: undefined,
        health: undefined,

        // Actions
        setTimelineEvents: (events) => set({ timelineEvents: events }),
        addTimelineEvent: (event) =>
          set((state) => ({
            timelineEvents: [...state.timelineEvents.slice(-499), event],
          })),
        setIsProcessing: (isProcessing) => set({ isProcessing }),
        setCycleCount: (cycleCount) => set({ cycleCount }),
        setActiveAgentId: (activeAgentId) => set({ activeAgentId }),
        setCompletedAgents: (completedAgents) => set({ completedAgents }),
        setKillSwitchActive: (killSwitchActive) => set({ killSwitchActive }),
        setAutoPilot: (autoPilot) => set({ autoPilot }),
        setVault: (vault) => set({ vault }),
        setSimulation: (simulation) => set({ simulation }),
        setHealth: (health) => set({ health }),
      }),
      {
        name: 'sentient-alpha-store',
        partialize: (state) => ({
          authMode: state.authMode,
          // Don't persist sensitive auth state - we'll verify on load
        }),
      }
    )
  )
);

// Helper function to get stored auth mode
export const getStoredAuthMode = (): AuthMode | null => {
  const stored = localStorage.getItem(`${AUTH_STORAGE_KEY}_mode`);
  if (stored === 'demo' || stored === 'production') {
    return stored;
  }
  return null;
};
