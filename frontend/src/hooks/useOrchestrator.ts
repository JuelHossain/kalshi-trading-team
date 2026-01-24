import {
  LogEntry,
  VaultState,
  SimulationState,
  SystemHealthData,
  TimelineEvent,
  TimelineEventType,
} from '@shared/types';
import { useState, useEffect, useRef } from 'react';

const BACKEND_URL = `http://${window.location.hostname}:3001`;
const PLAYBACK_SPEED_MS = 250;

// Helper to determine phase for data events
const getPhaseForType = (type: string, data: any): number => {
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
  const [activeAgentId, setActiveAgentId] = useState<number | null>(null);
  const [completedAgents, setCompletedAgents] = useState<number[]>([]);

  // Unified Timeline State
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);

  const [isProcessing, setIsProcessing] = useState(false);
  const [cycleCount, setCycleCount] = useState(0);
  const [autoPilot, setAutoPilot] = useState(false);
  const [currentPhaseId, setCurrentPhaseId] = useState(0);

  // Specific states for quick access if needed (optional)
  const [vault, setVault] = useState<VaultState | undefined>(undefined);
  const [simulation, setSimulation] = useState<SimulationState | undefined>(undefined);
  const [health, setHealth] = useState<SystemHealthData | undefined>(undefined);

  const eventBuffer = useRef<any[]>([]);

  useEffect(() => {
    const eventSource = new EventSource(`${BACKEND_URL}/api/stream`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'INIT') {
        eventBuffer.current = [];
        // Initialize with logs converted to unified events
        const initLogs: LogEntry[] = data.state.logs || [];
        const initEvents: TimelineEvent[] = initLogs.map((l) => ({
          id: l.id,
          type: 'LOG',
          timestamp: l.timestamp,
          cycleId: l.cycleId,
          phaseId: l.phaseId,
          data: l,
        }));

        setTimelineEvents(initEvents);
        setIsProcessing(data.state.isProcessing);
        setActiveAgentId(data.state.activeAgentId);
        setCompletedAgents(data.state.completedAgents || []);
      } else {
        eventBuffer.current.push(data);
        if (data.type === 'STATE') {
          setIsProcessing(data.state.isProcessing);
          setActiveAgentId(data.state.activeAgentId);
          setCompletedAgents(data.state.completedAgents || []);
        }
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE Connection Error (will retry):', err);
    };

    return () => eventSource.close();
  }, []);

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
          if (log.agentId) setActiveAgentId(log.agentId);
          if (log.phaseId !== undefined) setCurrentPhaseId(log.phaseId);
        } else if (['SIMULATION', 'VAULT', 'MARKET', 'INTERCEPT'].includes(eventType)) {
          // Inject synthetic phase ID
          const phaseId = getPhaseForType(eventType, rawData.state);
          newEvent = {
            id: `evt-${Date.now()}-${Math.random()}`,
            type: eventType as TimelineEventType,
            timestamp: timestamp,
            cycleId: cycleCount, // Use current known cycle
            phaseId: phaseId,
            data: rawData.state || rawData, // Handle structure differences
          };

          // Side effects
          if (eventType === 'VAULT') setVault(rawData.state);
          if (eventType === 'SIMULATION') setSimulation(rawData.state);
        } else if (eventType === 'STATE') {
          // State updates don't become timeline events, just state
          if (rawData.state.isProcessing !== undefined) setIsProcessing(rawData.state.isProcessing);
          if (rawData.state.activeAgentId !== undefined)
            setActiveAgentId(rawData.state.activeAgentId);
          if (rawData.state.completedAgents !== undefined)
            setCompletedAgents(rawData.state.completedAgents);
          if (rawData.state.cycleCount !== undefined) setCycleCount(rawData.state.cycleCount);
        } else if (eventType === 'HEALTH') {
          setHealth(rawData.state);
        }

        if (newEvent) {
          setTimelineEvents((prev) => [...prev.slice(-499), newEvent!]);
        }
      }
    }, PLAYBACK_SPEED_MS);

    return () => clearInterval(interval);
  }, [cycleCount]); // Dependency on cycleCount for synthetic events

  const runOrchestrator = async () => {
    setIsProcessing(true);
    try {
      await fetch(`${BACKEND_URL}/api/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ isPaperTrading }),
      });
    } catch (error) {
      console.error('[Orchestrator] Failed to trigger backend:', error);
      setIsProcessing(false);
    }
  };

  const handleKillSwitch = async () => {
    try {
      await fetch(`${BACKEND_URL}/api/kill-switch`, { method: 'POST' });
    } catch (e) {
      console.error('Kill switch activation failed', e);
    }
  };

  const handleAgentTest = async (agentId: number) => {
    // Implement diagnostic API if needed
    console.log(`Diagnostic requested for Agent ${agentId}`);
  };

  return {
    activeAgentId,
    completedAgents,
    timelineEvents, // EXPORTED NOW
    logs: timelineEvents.filter((e) => e.type === 'LOG').map((e) => e.data as LogEntry), // Backwards compat
    isProcessing,
    cycleCount,
    currentPhaseId,
    autoPilot,
    setAutoPilot,
    runOrchestrator,
    handleKillSwitch,
    addLog: (msg: string, id: number, level: any) =>
      console.log('Direct logging disabled in playback mode', msg),
    handleAgentTest,
    viewedAgentId: null,
    setViewedAgentId: () => {},
    showHealth: false,
    setShowHealth: () => {},
    vault,
    simulation,
    health,
    targetMarket: null,
    currentBalance: vault?.total || 0,
  };
};
