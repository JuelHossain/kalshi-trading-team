import {
    authorizeExecution,
    fetchScoutedMarkets,
    fetchVegasOdds,
    runCommitteeDebate,
    runMonteCarloSim,
    auditDecision,
    fetchOrderBook,
    createOrder,
    calculateRiskParams,
    fetchPortfolioBalance,
    logTradeToHistory,
    checkSystemHealth,
    analyzeSystemError
} from '../agents/exports';
import { isAuthenticated } from '../services/kalshiService';

export const runOrchestratorCycle = async (
    isPaperTrading: boolean,
    cycleCount: number,
    onUpdate: (data: any) => void
) => {
    const addLog = (message: string, agentId: number, level: 'INFO' | 'WARN' | 'ERROR' | 'SUCCESS' = 'INFO') => {
        const log = {
            id: Math.random().toString(36).substring(7),
            timestamp: new Date().toISOString(),
            agentId,
            cycleId: cycleCount,
            level,
            message
        };
        onUpdate({ type: 'LOG', log });
    };

    const updateState = (state: any) => {
        onUpdate({ type: 'STATE', state });
    };

    try {
        updateState({ isProcessing: true, completedAgents: [], activeAgentId: 1, cycleCount });
        addLog(`CYCLE START: Backend Execution Protocol (Cycle #${cycleCount})`, 1, 'INFO');

        if (!isAuthenticated()) {
            addLog("Auth Check Failed. Backend session not authenticated.", 0, 'ERROR');
            updateState({ isProcessing: false, activeAgentId: null });
            return;
        }

        // --- PHASE 1: SURVEILLANCE ---
        addLog("PHASE 1: Surveillance Start", 1, 'INFO');
        updateState({ activeAgentId: 2 });
        const markets = await fetchScoutedMarkets(isPaperTrading);
        addLog(`Scouted ${markets.length} markets.`, 2, 'SUCCESS');

        updateState({ activeAgentId: 3 });
        await fetchVegasOdds('american-football_nfl').catch(() => []);

        updateState({ activeAgentId: 7, completedAgents: [2, 3] });
        const greenlit = markets.slice(0, 1);
        for (const m of greenlit) {
            await fetchOrderBook(m.ticker, isPaperTrading);
        }

        // --- PHASE 2: INTELLIGENCE ---
        updateState({ activeAgentId: 4, completedAgents: [2, 3, 7] });
        for (const m of greenlit) {
            const debate = await runCommitteeDebate(m.title);
            addLog(`Analyst Verdict: ${debate.judgeVerdict}`, 4, 'SUCCESS');
        }

        addLog("Cycle Simulation Complete (Backend).", 1, 'SUCCESS');

    } catch (error: any) {
        addLog(`CRITICAL FAILURE: ${error.message}`, 13, 'ERROR');
        updateState({ activeAgentId: 13 });
        try {
            await analyzeSystemError(error.message, `Backend Cycle #${cycleCount}`);
        } catch (e) { }
    } finally {
        updateState({ isProcessing: false, activeAgentId: null });
    }
};
