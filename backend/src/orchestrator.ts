import {
    fetchScoutedMarkets,
    fetchVegasOdds,
    runCommitteeDebate,
    runMonteCarloSim,
    auditDecision,
    fetchOrderBook,
    analyzeOrderBook,
    createOrder,
    fetchPortfolioBalance,
    logTradeToHistory,
    analyzeSystemError,
    validateStaleData
} from '../agents/exports';
import { isAuthenticated } from '../services/kalshiService';
import { sendNotification } from '../services/notificationService';

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
        addLog(`[GHOST] CYCLE START: Sentient Alpha Funnel Protocol (Cycle #${cycleCount})`, 1, 'INFO');

        if (!isAuthenticated()) {
            addLog("Auth Check Failed. Backend session not authenticated.", 0, 'ERROR');
            updateState({ isProcessing: false, activeAgentId: null });
            return;
        }

        // --- STAGE 1: GLOBAL SCAN & SHADOW ODDS (Agents 2, 3, 7) ---
        addLog("STAGE 1: Scanning Global Markets & Shadow Odds", 2, 'INFO');
        updateState({ activeAgentId: 2 });
        const markets = await fetchScoutedMarkets(isPaperTrading);
        addLog(`Scouted ${markets.length} markets.`, 2, 'SUCCESS');

        updateState({ activeAgentId: 3 });
        const vegasOdds = await fetchVegasOdds('american-football_nfl').catch(() => []);
        addLog(`Vegas Interceptor: ${vegasOdds.length} signals captured.`, 3, 'INFO');

        // Target top market for analysis
        const targetMarket = markets[0];
        if (!targetMarket) {
            addLog("No viable markets found. Cooling down.", 1, 'WARN');
            return;
        }

        updateState({ activeAgentId: 7, completedAgents: [2, 3] });
        const book = await fetchOrderBook(targetMarket.ticker, isPaperTrading);

        // Agent 14 check: Stale Data
        // If Kalshi doesn't provide a timestamp, we might need to store it ourselves or check if book is default 0/99
        // For now, if bid and ask are both 0/99 or extreme, we can flag it.
        // Assuming targetMarket has a timestamp if normalized, or we check if book is valid.
        validateStaleData(Date.now()); // Placeholder for real market timestamp if available

        const sniperAnalysis = analyzeOrderBook(book, targetMarket.ticker);
        addLog(`Sniper scanning orderbook for ${targetMarket.ticker}: Bid=${book.yes_bid}, Ask=${book.yes_ask}, Snipe=${sniperAnalysis.snipePrice}c`, 7, 'INFO');

        // --- STAGE 2: INTELLIGENCE COMMITTEE & SIMS (Agents 4, 5, 6) ---
        addLog("STAGE 2: Intelligence Committee Assembly", 4, 'INFO');
        updateState({ activeAgentId: 4, completedAgents: [2, 3, 7] });

        // Pass current price (ask) to the debate
        const currentPriceForDebate = book.yes_ask || 50;
        const analystReport = await runCommitteeDebate(targetMarket.title, currentPriceForDebate);
        addLog(`Analyst [Gemini Pro]: ${analystReport.judgeVerdict} (Conf: ${analystReport.confidenceScore}%)`, 4, 'SUCCESS');

        updateState({ activeAgentId: 5 });
        const currentPrice = book.yes_ask || 50;
        const simResults = await runMonteCarloSim(targetMarket.title, analystReport.confidenceScore / 100, currentPrice);
        addLog(`Simulation Scientist: EV ${simResults.ev.toFixed(3)}, Status: ${simResults.status}`, 5, simResults.status === 'WARNING' ? 'WARN' : 'INFO');

        if (simResults.status === 'WARNING') {
            addLog(`SIM VETO: Win-rate below 58% threshold. Aborting trade.`, 5, 'ERROR');
            updateState({ isProcessing: false, activeAgentId: null });
            return;
        }

        updateState({ activeAgentId: 6 });
        const audit = await auditDecision(targetMarket.title, analystReport.judgeVerdict, analystReport.confidenceScore);

        // PROTOCOL: The Committee Veto (85% Consensus)
        if (!audit.approved) {
            addLog(`VETOED: ${audit.reason}`, 6, 'ERROR');
            return;
        }
        addLog(`COMMITTEE CONSENSUS REACHED: ${audit.reason}`, 6, 'SUCCESS');

        // --- STAGE 3: RISK & SNIPE (Agents 1, 8, 9) ---
        addLog("STAGE 3: Risk Calculation & Snipe Execution", 9, 'INFO');
        updateState({ activeAgentId: 9, completedAgents: [2, 3, 7, 4, 5, 6] });

        // PROTOCOL: The Recursive Vault (Principal Protection)
        const availableBalance = await fetchPortfolioBalance(isPaperTrading);

        updateState({ activeAgentId: 8 });

        // Use Analyst's Kelly Sizing (recommendedSize is 0.0 - 0.10)
        const wager = Math.floor(availableBalance * analystReport.recommendedSize);

        if (wager > 0) {
            addLog(`Executioner: Preparing Limit Snipe - Wager $${wager} (Kelly: ${(analystReport.recommendedSize * 100).toFixed(1)}%)`, 8, 'INFO');

            // Calculate contract count from wager and price
            const count = Math.floor(wager / (sniperAnalysis.snipePrice / 100));

            if (count <= 0) {
                addLog("Executioner Bypass: Price too high for wager amount.", 8, 'WARN');
                return;
            }

            // PROTOCOL: The Silent Sniper (Limit Orders Only)
            const order = await createOrder(
                targetMarket.ticker,
                'buy',
                count,
                'yes',
                sniperAnalysis.snipePrice,
                isPaperTrading
            );

            addLog(`SNIPE EXECUTED: Order ID ${order?.order_id || 'PENDING'} @ ${sniperAnalysis.snipePrice}c`, 8, 'SUCCESS');

            // --- STAGE 4: SETTLEMENT (Agents 10, 12, 9) ---
            addLog("STAGE 4: Settlement & Notification", 10, 'INFO');
            updateState({ activeAgentId: 10, completedAgents: [2, 3, 7, 4, 5, 6, 9, 8, 1] });

            await logTradeToHistory(
                4, // Logic Engineer / Analyst ID
                targetMarket.ticker,
                'BUY',
                sniperAnalysis.snipePrice,
                count,
                { ...analystReport, status: 'FILLED', wagerValue: wager }
            );
            await sendNotification(`💰 TRADE EXECUTED: ${targetMarket.title} | Wager: $${wager} (${count} contracts) | Price: ${sniperAnalysis.snipePrice}c`, 'high');
        } else {
            addLog("Executioner Bypass: Risk Engine returned 0 wager.", 8, 'WARN');
        }

        addLog("Funnel Cycle Completed Successfully.", 1, 'SUCCESS');

    } catch (error: any) {
        addLog(`CRITICAL FAILURE: ${error.message}`, 13, 'ERROR');
        updateState({ activeAgentId: 13 });
        try {
            await analyzeSystemError(error.message, `Sentient Funnel Cycle #${cycleCount}`);
            await sendNotification(`⚠️ SYSTEM CRASH: ${error.message}`, 'urgent');
        } catch (e) { }
    } finally {
        updateState({ isProcessing: false, activeAgentId: null });
    }
};

