import { LogEntry, VaultState, SimulationState, SystemHealthData } from '@shared/types';
import { useState, useEffect, useRef } from 'react';

const BACKEND_URL = `http://${window.location.hostname}:3001`;

// Cinematic Pacing: Process one event every 250ms
const PLAYBACK_SPEED_MS = 250;

export const useOrchestrator = (isLoggedIn: boolean, isPaperTrading: boolean) => {
    // React State (The "Screen" State)
    const [activeAgentId, setActiveAgentId] = useState<number | null>(null);
    const [completedAgents, setCompletedAgents] = useState<number[]>([]);
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [isProcessing, setIsProcessing] = useState(false);
    const [cycleCount, setCycleCount] = useState(0);
    const [targetMarket, setTargetMarket] = useState<any>(null);
    const [currentBalance, setCurrentBalance] = useState(300.00);
    const [autoPilot, setAutoPilot] = useState(false);
    const [vault, setVault] = useState<VaultState | undefined>(undefined);
    const [simulation, setSimulation] = useState<SimulationState | undefined>(undefined);
    const [health, setHealth] = useState<SystemHealthData | undefined>(undefined);

    // Event Buffer
    const eventBuffer = useRef<any[]>([]);

    useEffect(() => {
        const eventSource = new EventSource(`${BACKEND_URL}/api/stream`);

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);

            // Immediate handling for Initial State
            if (data.type === 'INIT') {
                eventBuffer.current = []; // Clear buffer on init
                setLogs(data.state.logs || []);
                setIsProcessing(data.state.isProcessing);
                setActiveAgentId(data.state.activeAgentId);
                setCompletedAgents(data.state.completedAgents || []);
            } else {
                // Queue all other live events
                eventBuffer.current.push(data);
            }
        };

        eventSource.onerror = (err) => {
            console.error("SSE Connection Error (will retry):", err);
        };

        return () => eventSource.close();
    }, []);

    // Cinematic Playback Loop
    useEffect(() => {
        const interval = setInterval(() => {
            if (eventBuffer.current.length === 0) return;

            // Process TWO events per tick if backlog gets too large (>20 events)
            const count = eventBuffer.current.length > 20 ? 2 : 1;

            for (let i = 0; i < count; i++) {
                const data = eventBuffer.current.shift();
                if (!data) break;

                // console.log('[Playback] Processing:', data.type);

                if (data.type === 'LOG') {
                    setLogs(prev => [...prev.slice(-499), data.log]);
                    // Auto-set active agent based on log sender to keep UI lively
                    if (data.log.agentId) setActiveAgentId(data.log.agentId);
                } else if (data.type === 'STATE') {
                    if (data.state.isProcessing !== undefined) setIsProcessing(data.state.isProcessing);
                    if (data.state.activeAgentId !== undefined) setActiveAgentId(data.state.activeAgentId);
                    if (data.state.completedAgents !== undefined) setCompletedAgents(data.state.completedAgents);
                    if (data.state.cycleCount !== undefined) setCycleCount(data.state.cycleCount);
                } else if (data.type === 'VAULT') {
                    setVault(data.state);
                    setCurrentBalance(data.state.total);
                } else if (data.type === 'SIMULATION') {
                    setSimulation(data.state);
                } else if (data.type === 'HEALTH') {
                    setHealth(data.state);
                }
            }
        }, PLAYBACK_SPEED_MS);

        return () => clearInterval(interval);
    }, []);

    const runOrchestrator = async () => {
        console.log('[Orchestrator] runOrchestrator called');
        try {
            console.log(`[Orchestrator] POSTING to ${BACKEND_URL}/api/run`);
            const response = await fetch(`${BACKEND_URL}/api/run`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ isPaperTrading })
            });
            console.log('[Orchestrator] response status:', response.status);
            if (!response.ok) {
                const err = await response.json();
                console.error('[Orchestrator] error response:', err);
            }
        } catch (error) {
            console.error('[Orchestrator] Failed to trigger backend:', error);
        }
    };

    const handleTerminate = async () => {
        // Implement termination API if needed
        console.log("Termination requested via API");
        try {
            await fetch(`${BACKEND_URL}/api/reset`, { method: 'POST' });
        } catch (e) {
            console.error("Termination failed", e);
        }
    };

    const handleAgentTest = async (agentId: number) => {
        // Implement diagnostic API if needed
        console.log(`Diagnostic requested for Agent ${agentId}`);
    };

    return {
        activeAgentId,
        completedAgents,
        logs,
        isProcessing,
        cycleCount,
        targetMarket,
        currentBalance,
        autoPilot,
        setAutoPilot,
        runOrchestrator,
        handleTerminate,
        addLog: (msg: string, id: number, level: any) => console.log("Direct logging disabled in playback mode", msg),
        handleAgentTest,
        viewedAgentId: null,
        setViewedAgentId: () => { },
        showHealth: false,
        setShowHealth: () => { },
        vault,
        simulation,
        health
    };
};
