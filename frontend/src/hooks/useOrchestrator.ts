import { LogEntry, VaultState, SimulationState, SystemHealthData } from '@shared/types';
import { useState, useEffect } from 'react';

const BACKEND_URL = `http://${window.location.hostname}:3001`;

export const useOrchestrator = (isLoggedIn: boolean, isPaperTrading: boolean) => {
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

    useEffect(() => {
        const eventSource = new EventSource(`${BACKEND_URL}/api/stream`);

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('[SSE] Received event:', data.type);
            if (data.type === 'INIT') {
                setLogs(data.state.logs || []);
                setIsProcessing(data.state.isProcessing);
                setActiveAgentId(data.state.activeAgentId);
                setCompletedAgents(data.state.completedAgents || []);
            } else if (data.type === 'LOG') {
                setLogs(prev => [...prev.slice(-499), data.log]);
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
        };

        eventSource.onerror = (err) => {
            console.error("SSE Connection Error (will retry):", err);
        };

        return () => eventSource.close();
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
        addLog: (msg: string, id: number, level: any) => console.log("Direct logging disabled in split-mode", msg),
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
