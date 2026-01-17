import { useState, useEffect } from 'react';
import { LogEntry } from '../types';

const BACKEND_URL = 'http://localhost:3001';

export const useOrchestrator = (isLoggedIn: boolean, isPaperTrading: boolean) => {
    const [activeAgentId, setActiveAgentId] = useState<number | null>(null);
    const [completedAgents, setCompletedAgents] = useState<number[]>([]);
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [isProcessing, setIsProcessing] = useState(false);
    const [cycleCount, setCycleCount] = useState(0);
    const [targetMarket, setTargetMarket] = useState<any>(null);
    const [currentBalance, setCurrentBalance] = useState(300.00);
    const [autoPilot, setAutoPilot] = useState(false);

    useEffect(() => {
        const eventSource = new EventSource(`${BACKEND_URL}/api/stream`);

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
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
            }
        };

        eventSource.onerror = (err) => {
            console.error("SSE Connection Error:", err);
            eventSource.close();
        };

        return () => eventSource.close();
    }, []);

    const runOrchestrator = async () => {
        try {
            await fetch(`${BACKEND_URL}/api/run`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ isPaperTrading })
            });
        } catch (error) {
            console.error('Failed to trigger backend:', error);
        }
    };

    const handleTerminate = async () => {
        // Implement termination API if needed
        console.log("Termination requested via API");
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
        setShowHealth: () => { }
    };
};
