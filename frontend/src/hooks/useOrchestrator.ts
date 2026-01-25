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

  // SSE Connection
  useEffect(() => {
    if (!isLoggedIn) return;

    const eventSource = new EventSource(`${ENGINE_URL}/stream`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
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
          if (log.agentId) store.setActiveAgentId(log.agentId);
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

  // Autopilot Logic
  useEffect(() => {
    let timeoutId: NodeJS.Timeout;
    if (store.autoPilot && !store.isProcessing && store.cycleCount > 0) {
      timeoutId = setTimeout(() => {
        console.log('[Autopilot] Starting next cycle...');
        runOrchestrator();
      }, 2000);
    }
    return () => clearTimeout(timeoutId);
  }, [store.autoPilot, store.isProcessing, store.cycleCount, runOrchestrator]);

  const handleCancelCycle = async () => {
    try {
      await fetch(`${ENGINE_URL}/cancel`, { method: 'POST' });
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
    setAutoPilot: store.setAutoPilot,
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
  };
};
