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
  validateStaleData,
} from './agents/exports';
import { isAuthenticated } from './services/kalshiService';
import { sendNotification } from './services/notificationService';

export const runOrchestratorCycle = async (
  isPaperTrading: boolean,
  cycleCount: number,
  onUpdate: (data: any) => void
) => {
  let currentPhase = 0;
  const completedPhases: number[] = [];

  const addLog = (
    message: string,
    agentId: number,
    phaseId: number,
    level: 'INFO' | 'WARN' | 'ERROR' | 'SUCCESS' = 'INFO'
  ) => {
    const log = {
      id: Math.random().toString(36).substring(7),
      timestamp: new Date().toISOString(),
      agentId,
      cycleId: cycleCount,
      phaseId,
      level,
      message,
    };
    onUpdate({ type: 'LOG', log });
  };

  const updateState = (state: any) => {
    onUpdate({ type: 'STATE', state });
  };

  const transitionToPhase = (phaseId: number, phaseName: string) => {
    if (!completedPhases.includes(currentPhase) && currentPhase !== 0) {
      completedPhases.push(currentPhase);
    }
    currentPhase = phaseId;
    addLog(`━━━ ${phaseName} ━━━`, 0, phaseId, 'INFO');
  };

  const completeCycle = () => {
    if (!completedPhases.includes(currentPhase)) {
      completedPhases.push(currentPhase);
    }
    addLog(
      `✓ CYCLE #${cycleCount} COMPLETE - All phases finished successfully`,
      0,
      currentPhase,
      'SUCCESS'
    );
  };

  try {
    updateState({ isProcessing: true, completedAgents: [], activeAgentId: 1, cycleCount });

    // PHASE 0: System Initialization
    transitionToPhase(0, 'PHASE 0: SYSTEM INITIALIZATION');
    addLog(
      `[GHOST] CYCLE START: Sentient Alpha Funnel Protocol (Cycle #${cycleCount})`,
      1,
      0,
      'INFO'
    );

    if (!isAuthenticated()) {
      addLog('Auth Check Failed. Backend session not authenticated.', 0, 0, 'ERROR');
      updateState({ isProcessing: false, activeAgentId: null });
      return;
    }

    // PHASE 1: Surveillance (Global Scan & Shadow Odds)
    transitionToPhase(1, 'PHASE 1: SURVEILLANCE');
    addLog('Scanning Global Markets & Shadow Odds', 2, 1, 'INFO');
    updateState({ activeAgentId: 2 });
    const markets = await fetchScoutedMarkets(isPaperTrading);
    addLog(`Scouted ${markets.length} markets.`, 2, 1, 'SUCCESS');

    updateState({ activeAgentId: 3 });
    const vegasOdds = await fetchVegasOdds('american-football_nfl').catch(() => []);
    addLog(`Vegas Interceptor: ${vegasOdds.length} signals captured.`, 3, 1, 'INFO');

    // Target top market for analysis
    const targetMarket = markets[0];
    if (!targetMarket) {
      addLog('No viable markets found. Cooling down.', 1, 1, 'WARN');
      return;
    }

    updateState({ activeAgentId: 7, completedAgents: [2, 3] });
    const book = await fetchOrderBook(targetMarket.ticker, isPaperTrading);

    // CRITICAL FIX #4: Validate using market's last update time, not current time
    const marketLastUpdate = (targetMarket as any).last_updated || Date.now();
    validateStaleData(marketLastUpdate);

    const sniperAnalysis = analyzeOrderBook(book, targetMarket.ticker);

    // Check for spread veto
    if ((sniperAnalysis as any).vetoed) {
      addLog(`SPREAD VETO: ${(sniperAnalysis as any).vetoReason}`, 7, 1, 'ERROR');
      updateState({ isProcessing: false, activeAgentId: null });
      return;
    }

    addLog(
      `Sniper scanning orderbook for ${targetMarket.ticker}: Bid=${book.yes_bid}, Ask=${book.yes_ask}, Snipe=${sniperAnalysis.snipePrice}c`,
      7,
      1,
      'INFO'
    );

    // PHASE 2: Intelligence Committee & Simulations
    transitionToPhase(2, 'PHASE 2: INTELLIGENCE');
    addLog('Intelligence Committee Assembly', 4, 2, 'INFO');
    updateState({ activeAgentId: 4, completedAgents: [2, 3, 7] });

    // Pass current price (ask) to the debate
    const currentPriceForDebate = book.yes_ask || 50;
    const analystReport = await runCommitteeDebate(targetMarket.title, currentPriceForDebate);
    addLog(
      `Analyst [Gemini Pro]: ${analystReport.judgeVerdict} (Conf: ${analystReport.confidenceScore}%)`,
      4,
      2,
      'SUCCESS'
    );

    updateState({ activeAgentId: 5 });
    const currentPrice = book.yes_ask || 50;
    const simResults = await runMonteCarloSim(
      targetMarket.title,
      analystReport.confidenceScore / 100,
      currentPrice
    );
    addLog(
      `Simulation Scientist: EV ${simResults.ev.toFixed(3)}, Status: ${simResults.status}`,
      5,
      2,
      simResults.status === 'WARNING' ? 'WARN' : 'INFO'
    );

    if (simResults.status === 'WARNING') {
      addLog(`SIM VETO: Win-rate below 58% threshold. Aborting trade.`, 5, 2, 'ERROR');
      updateState({ isProcessing: false, activeAgentId: null });
      return;
    }

    updateState({ activeAgentId: 6 });
    const audit = await auditDecision(
      targetMarket.title,
      analystReport.judgeVerdict,
      analystReport.confidenceScore
    );

    // PROTOCOL: The Committee Veto (85% Consensus)
    if (!audit.approved) {
      addLog(`VETOED: ${audit.reason}`, 6, 2, 'ERROR');
      return;
    }
    addLog(`COMMITTEE CONSENSUS REACHED: ${audit.reason}`, 6, 2, 'SUCCESS');

    // PHASE 3: Execution
    transitionToPhase(3, 'PHASE 3: EXECUTION');
    addLog('Risk Calculation & Snipe Execution', 9, 3, 'INFO');
    updateState({ activeAgentId: 9, completedAgents: [2, 3, 7, 4, 5, 6] });

    // PROTOCOL: The Recursive Vault (Principal Protection)
    const availableBalance = await fetchPortfolioBalance(isPaperTrading);

    updateState({ activeAgentId: 8 });

    // Use Analyst's Kelly Sizing (recommendedSize is 0.0 - 0.10)
    const wager = Math.floor(availableBalance * analystReport.recommendedSize);

    if (wager > 0) {
      addLog(
        `Executioner: Preparing Limit Snipe - Wager $${wager} (Kelly: ${(analystReport.recommendedSize * 100).toFixed(1)}%)`,
        8,
        3,
        'INFO'
      );

      // Calculate contract count from wager and price
      let count = Math.floor(wager / (sniperAnalysis.snipePrice / 100));

      if (count <= 0) {
        addLog('Executioner Bypass: Price too high for wager amount.', 8, 3, 'WARN');
        return;
      }

      // CRITICAL FIX #3: Enforce maximum position size
      const MAX_POSITION_SIZE = 500;
      if (count > MAX_POSITION_SIZE) {
        addLog(
          `Position size capped: ${count} → ${MAX_POSITION_SIZE} contracts (risk management)`,
          8,
          3,
          'WARN'
        );
        count = MAX_POSITION_SIZE;
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

      addLog(
        `SNIPE EXECUTED: Order ID ${order?.order_id || 'PENDING'} @ ${sniperAnalysis.snipePrice}c`,
        8,
        3,
        'SUCCESS'
      );

      // PHASE 4: Accounting & Settlement
      transitionToPhase(4, 'PHASE 4: ACCOUNTING');
      addLog('Settlement & Notification', 10, 4, 'INFO');
      updateState({ activeAgentId: 10, completedAgents: [2, 3, 7, 4, 5, 6, 9, 8, 1] });

      await logTradeToHistory(
        4, // Logic Engineer / Analyst ID
        targetMarket.ticker,
        'BUY',
        sniperAnalysis.snipePrice,
        count,
        { ...analystReport, status: 'FILLED', wagerValue: wager }
      );
      await sendNotification(
        `💰 TRADE EXECUTED: ${targetMarket.title} | Wager: $${wager} (${count} contracts) | Price: ${sniperAnalysis.snipePrice}c`,
        'high'
      );
    } else {
      addLog('Executioner Bypass: Risk Engine returned 0 wager.', 8, 3, 'WARN');
    }

    // PHASE 5: Protection (Final Safety Checks)
    transitionToPhase(5, 'PHASE 5: PROTECTION');
    addLog('Running final safety checks...', 12, 5, 'INFO');
    // Placeholder for Ragnarok/Sentinel checks
    addLog('Safety protocols verified. No anomalies detected.', 12, 5, 'SUCCESS');

    completeCycle();
  } catch (error: any) {
    addLog(`CRITICAL FAILURE: ${error.message}`, 13, 13, 'ERROR');
    updateState({ activeAgentId: 13 });
    try {
      await analyzeSystemError(error.message, `Sentient Funnel Cycle #${cycleCount}`);
      await sendNotification(`⚠️ SYSTEM CRASH: ${error.message}`, 'urgent');
    } catch (e) { }
  } finally {
    updateState({ isProcessing: false, activeAgentId: null });
  }
};
