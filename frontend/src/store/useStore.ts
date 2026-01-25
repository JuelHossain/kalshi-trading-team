import { create } from 'zustand';
import { TimelineEvent, VaultState, SimulationState, SystemHealthData } from '../../shared/types';

interface User {
    id: string;
    email: string;
    name: string;
}

interface AppState {
    // Auth
    user: User | null;
    isAuthenticated: boolean;
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

export const useStore = create<AppState>((set) => ({
    // Auth
    user: null,
    isAuthenticated: false,
    login: async () => {
        // Placeholder - will be replaced by actual API call in components or a thunk
        try {
            const res = await fetch('http://localhost:3002/auth', { method: 'POST' });
            const data = await res.json();
            if (data.isAuthenticated) {
                set({ user: data.user, isAuthenticated: true });
            }
        } catch (e) {
            console.error("Login failed", e);
        }
    },
    logout: () => set({ user: null, isAuthenticated: false }),

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
    addTimelineEvent: (event) => set((state) => ({
        timelineEvents: [...state.timelineEvents.slice(-499), event]
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
}));
