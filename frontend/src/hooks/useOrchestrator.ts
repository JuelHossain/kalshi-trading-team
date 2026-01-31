import { useEffect, useRef, useCallback } from 'react';
import { useStore } from '../store/useStore';
import { LogEntry, TimelineEventType, TimelineEvent } from '@shared/types';

const ENGINE_URL = '/api';
const PLAYBACK_SPEED_MS = 250;

// Helper to determine phase for data events
const getPhaseForType = (type: string, _data: any): number => {
  switch (type) {
    case 'MARKET':
      return 1; // Surveillance
    case 'SIMULATION':
      return 2; // Intelligence
    case 'INTERCEPT':
      return 2; // Intelligence
    case 'VAULT':
      return 4; // Accounting
    case 'TRADE':
      return 3; // Execution
    default:
      return 0;
  }
};

export const useOrchestrator = (isLoggedIn: boolean, isPaperTrading: boolean) => {
  const store = useStore();
  const eventBuffer = useRef<any[]>([]);
  const hasInitialized = useRef(false);
  const lastLogRef = useRef<{ signature: string; timestamp: number; count: number }>({
    signature: '',
    timestamp: 0,
    count: 0,
  });

  // Fetch autopilot status from backend on mount to sync state
  useEffect(() => {
    if (!hasInitialized.current && isLoggedIn) {
      fetch(`${ENGINE_URL}/autopilot/status`)
        .then((res) => res.json())
        .then((data) => {
          // Sync frontend state with backend reality
          store.setAutoPilot(data.autopilot_enabled || false);
          store.setKillSwitchActive(data.is_locked_down || false);
          store.setCycleCount(data.cycle_count || 0);
          store.setIsProcessing(data.is_processing || false);

          // Clear stale timeline events from previous session
          store.setTimelineEvents([]);

          console.log('[Orchestrator] Synced with backend state:', {
            autopilot: data.autopilot_enabled,
            locked: data.is_locked_down,
            cycle: data.cycle_count,
          });

          hasInitialized.current = true;
        })
        .catch((err) => {
          console.error('[Orchestrator] Failed to sync backend state:', err);
          // Still mark as initialized to avoid retry loops
          hasInitialized.current = true;
        });
    }
  }, [isLoggedIn, store]);

  // SSE Connection
  useEffect(() => {
    if (!isLoggedIn) return;

    const eventSource = new EventSource(`${ENGINE_URL}/stream`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      // LOG THROTTLING: Prevent console spam
      if (data.type === 'LOG' || data.type === 'ERROR') {
        const signature = `${data.type}:${JSON.stringify(data.log || data.error)}`;
        const now = Date.now();

        // Check if we've seen this exact log in the last 2 seconds
        if (
          lastLogRef.current.signature === signature &&
          now - lastLogRef.current.timestamp < 2000
        ) {
          lastLogRef.current.count++;
          if (lastLogRef.current.count === 10) {
            console.warn('[Orchestrator] Suppressing duplicate logs...');
          }
          return; // Skip processing duplicate
        }

        lastLogRef.current = { signature, timestamp: now, count: 1 };
      }

      console.log('[Orchestrator] SSE Event received:', data.type, data);
      eventBuffer.current.push(data);
    };

    eventSource.onerror = (err) => {
      console.error('SSE Connection Error:', err);
      // Optional: Logic to reconnect or show status
    };

    return () => eventSource.close();
  }, [isLoggedIn]);

  // Cinematic Playback Loop
  useEffect(() => {
    const interval = setInterval(() => {
      if (eventBuffer.current.length === 0) return;

      const count = eventBuffer.current.length > 20 ? 2 : 1;

      for (let i = 0; i < count; i++) {
        const rawData = eventBuffer.current.shift();
        if (!rawData) break;

        const eventType = rawData.type;
        let newEvent: TimelineEvent | null = null;
        const timestamp = new Date().toISOString();

        if (eventType === 'LOG') {
          const log = rawData.log;
          newEvent = {
            id: log.id,
            type: 'LOG',
            timestamp: log.timestamp,
            cycleId: log.cycleId,
            phaseId: log.phaseId,
            data: log,
          };
          if (log.agentId) {
            store.setActiveAgentId(log.agentId);
            // Update agent state in agentSlice for workflow visualization
            const agentMap: Record<number, string> = {
              1: 'SOUL',
              2: 'SENSES',
              3: 'BRAIN',
              4: 'HAND',
              11: 'VAULT',
              14: 'GATEWAY',
            };

            const agentName = agentMap[log.agentId] || log.agentName;
            if (agentName && ['SOUL', 'SENSES', 'BRAIN', 'HAND'].includes(agentName)) {
              store.setAgentState(log.agentId, {
                status: 'active',
                lastAction: log.message,
                lastUpdated: timestamp,
              });
            }

            // AUTO-FIX: Convert "Synapse Input" logs to MARKET events for UI
            if (
              log.message.toLowerCase().includes('synapse input:') ||
              log.message.toLowerCase().startsWith('analyzing:')
            ) {
              const ticker = log.message.split(':').pop()?.trim() || 'Unknown';
              // Create synthetic MARKET event for Logistics Center
              const marketEvent: TimelineEvent = {
                id: `market-${log.id}`,
                type: 'MARKET',
                timestamp: log.timestamp,
                cycleId: log.cycleId,
                phaseId: 1, // Surveillance Phase
                data: {
                  market: ticker,
                  ...log,
                },
              };
              // Add to store immediately
              store.addTimelineEvent(marketEvent);
            }

            if (log.agentId) {
              // Add transition for workflow visualization
              const flowTypes: Record<
                number,
                'authorization' | 'opportunity' | 'decision' | 'execution'
              > = {
                1: 'authorization',
                2: 'opportunity',
                3: 'decision',
                4: 'execution',
              };

              const transition = {
                id: `trans-${Date.now()}-${log.agentId}`,
                fromAgent: log.agentId,
                toAgent: log.agentId < 4 ? log.agentId + 1 : 4,
                flowType: flowTypes[log.agentId] || 'authorization',
                timestamp,
                data: { message: log.message },
                active: true,
              };

              store.addTransition(transition);

              // Set back to idle after a delay and deactivate transition
              setTimeout(() => {
                store.setAgentState(log.agentId, { status: 'idle' });
              }, 2000);
            }
          }
          // if (log.phaseId !== undefined) setCurrentPhaseId(log.phaseId); // Handled by store if needed
        } else if (['SIMULATION', 'VAULT', 'MARKET', 'INTERCEPT'].includes(eventType)) {
          const phaseId = getPhaseForType(eventType, rawData.state);
          newEvent = {
            id: `evt-${Date.now()}-${Math.random()}`,
            type: eventType as TimelineEventType,
            timestamp: timestamp,
            cycleId: store.cycleCount,
            phaseId: phaseId,
            data: rawData.state || rawData,
          };

          if (eventType === 'VAULT') store.setVault(rawData.state);
          if (eventType === 'SIMULATION') store.setSimulation(rawData.state);
        } else if (eventType === 'STATE') {
          if (rawData.state.isProcessing !== undefined)
            store.setIsProcessing(rawData.state.isProcessing);
          if (rawData.state.activeAgentId !== undefined)
            store.setActiveAgentId(rawData.state.activeAgentId);
          if (rawData.state.completedAgents !== undefined)
            store.setCompletedAgents(rawData.state.completedAgents);
          if (rawData.state.cycleCount !== undefined) store.setCycleCount(rawData.state.cycleCount);
          if (rawData.state.killSwitchActive !== undefined)
            store.setKillSwitchActive(rawData.state.killSwitchActive);
        } else if (eventType === 'HEALTH') {
          store.setHealth(rawData.state);
        } else if (eventType === 'ERROR') {
          // Handle error events from ErrorDispatcher
          const error = rawData.error;
          newEvent = {
            id: error.id,
            type: 'ERROR' as TimelineEventType,
            timestamp: error.timestamp,
            cycleId: error.cycleId,
            phaseId: error.phaseId,
            data: error,
          };
        }

        if (newEvent) {
          store.addTimelineEvent(newEvent);
        }
      }
    }, PLAYBACK_SPEED_MS);

    return () => clearInterval(interval);
  }, [store.cycleCount]); // Dependency on cycleCount if needed

  const runOrchestrator = useCallback(async () => {
    if (store.isProcessing) return;

    store.setIsProcessing(true);
    try {
      await fetch(`${ENGINE_URL}/trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ isPaperTrading }),
      });
    } catch (error) {
      console.error('[Orchestrator] Failed to trigger engine:', error);
      store.setIsProcessing(false);
    }
  }, [store.isProcessing, isPaperTrading]);

  const handleToggleAutopilot = useCallback(
    async (enabled: boolean) => {
      try {
        const endpoint = enabled ? '/autopilot/start' : '/autopilot/stop';
        const response = await fetch(`${ENGINE_URL}${endpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ isPaperTrading }),
        });

        if (response.ok) {
          // Sync local state with backend
          store.setAutoPilot(enabled);
          console.log(`[Orchestrator] Autopilot ${enabled ? 'enabled' : 'disabled'}`);
        } else {
          console.error(`[Orchestrator] Failed to ${enabled ? 'enable' : 'disable'} autopilot`);
        }
      } catch (error) {
        console.error('[Orchestrator] Autopilot toggle error:', error);
      }
    },
    [isPaperTrading, store]
  );

  // Autopilot Logic - REMOVED (Backend handles loop now)
  // The frontend should ONLY reflect state, not drive the loop.
  // This prevents the "bullet train" issue where frontend and backend both drive cycles.

  const handleCancelCycle = async () => {
    try {
      // 1. Explicitly stop autopilot on backend
      await fetch(`${ENGINE_URL}/autopilot/stop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ isPaperTrading }),
      });

      // 2. Cancel current cycle
      await fetch(`${ENGINE_URL}/cancel`, { method: 'POST' });

      // 3. Update local state immediately
      store.setAutoPilot(false);
      store.setIsProcessing(false);
    } catch (e) {
      console.error('Cancel cycle failed', e);
    }
  };

  const handleKillSwitch = async () => {
    store.setAutoPilot(false);
    try {
      await fetch(`${ENGINE_URL}/kill-switch`, { method: 'POST' });
    } catch (e) {
      console.error('Kill switch failed', e);
    }
  };

  // Backwards compatibility return object
  return {
    activeAgentId: store.activeAgentId,
    completedAgents: store.completedAgents,
    timelineEvents: store.timelineEvents,
    logs: store.timelineEvents.filter((e) => e.type === 'LOG').map((e) => e.data as LogEntry),
    isProcessing: store.isProcessing,
    cycleCount: store.cycleCount,
    currentPhaseId: store.currentPhaseId,
    autoPilot: store.autoPilot,
    setAutoPilot: handleToggleAutopilot, // Use backend-syncing function
    runOrchestrator,
    handleCancelCycle,
    handleKillSwitch,
    handleActivateKillSwitch: handleKillSwitch, // Map to same for now or implement specific if needed
    handleDeactivateKillSwitch: async () => {}, // Implement if engine supports it
    addLog: () => {},
    handleAgentTest: async () => {},
    viewedAgentId: null,
    setViewedAgentId: () => {},
    showHealth: false,
    setShowHealth: () => {},
    vault: store.vault,
    simulation: store.simulation,
    health: store.health,
    targetMarket: null,
    currentBalance: store.vault?.total || 0,
    killSwitchActive: store.killSwitchActive,
    activeTransitions: store.activeTransitions,
  };
};
