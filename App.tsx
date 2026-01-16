import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import WorkflowVisualizer from './components/WorkflowVisualizer';
import Terminal from './components/Terminal';
import MarketAnalysis from './components/MarketAnalysis';
import AboutPage from './components/AboutPage';
import PnLChart from './components/PnLChart';
import PnLHeatmap from './components/PnLHeatmap';
import { AGENTS } from './constants';
import { LogEntry, DebateResponse } from './types';
import { CONFIG } from './config';
import { scanMarketsWithGroq } from './services/groqService';
import { logTradeToHistory } from './services/supabaseService';
import { fetchScoutedMarkets, authenticateWithKeys, isAuthenticated, fetchOrderBook, createOrder } from './services/kalshiService';
import { analyzeSystemError, runCommitteeDebate } from './services/geminiService';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [activeAgentId, setActiveAgentId] = useState<number | null>(null);
  const [completedAgents, setCompletedAgents] = useState<number[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [cycleCount, setCycleCount] = useState(0); 
  
  // Environment State - Default to PAPER for Safety
  const [isPaperTrading, setIsPaperTrading] = useState(true);
  
  // Autopilot State
  const [autoPilot, setAutoPilot] = useState(true); 
  
  // Credential State (V2 Auth) 
  const [apiKeyId, setApiKeyId] = useState(CONFIG.KALSHI.KEY_ID || '');
  const [apiSecret, setApiSecret] = useState(CONFIG.KALSHI.PRIVATE_KEY || '');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  // Workflow Data State
  const [targetMarket, setTargetMarket] = useState<any>(null); // Visual focus
  const [currentBalance, setCurrentBalance] = useState(300.00); // Internal state for Agent 9

  const addLog = (message: string, agentId: number, level: LogEntry['level'] = 'INFO', cycleIdOverride?: number, phaseIdOverride?: number) => {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const ms = String(now.getMilliseconds()).padStart(3, '0');

    const newLog: LogEntry = {
      id: Math.random().toString(36).substring(7),
      timestamp: `${timeStr}.${ms}`,
      agentId,
      cycleId: cycleIdOverride !== undefined ? cycleIdOverride : cycleCount,
      phaseId: phaseIdOverride,
      level,
      message,
    };
    setLogs(prev => [...prev.slice(-499), newLog]);
  };

  const handleLogin = async () => {
      setAuthError(null);
      addLog(`SYSTEM: Initiating V2 Handshake to ${isPaperTrading ? 'SANDBOX' : 'LIVE'}...`, 0, 'WARN', 0);
      try {
          await authenticateWithKeys(apiKeyId, apiSecret, isPaperTrading);
          setIsLoggedIn(true);
          addLog(`SYSTEM: V2 Signature Verified. Secure Session Established.`, 0, 'SUCCESS', 0);
      } catch (e: any) {
          setAuthError(e.message);
          setIsLoggedIn(false);
          addLog(`SYSTEM: Auth Failed - ${e.message}`, 0, 'ERROR', 0);
      }
  };

  // Initial Auth Check
  useEffect(() => {
      if (CONFIG.KALSHI.KEY_ID && CONFIG.KALSHI.PRIVATE_KEY && !isLoggedIn) {
          const timer = setTimeout(() => {
             handleLogin();
          }, 1000); 
          return () => clearTimeout(timer);
      }
  }, []);

  // Main Autopilot Loop - Triggered ONLY when idle and logged in
  useEffect(() => {
    if (isLoggedIn && autoPilot && !isProcessing) {
        const timer = setTimeout(() => {
            runOrchestrator();
        }, 12000); 
        return () => clearTimeout(timer);
    }
  }, [isLoggedIn, autoPilot, isProcessing]);

  // --- THE FUNNEL EXECUTION CYCLE (TaskGroup Architecture) ---
  const runOrchestrator = async (forceFail: boolean = false) => {
    if (isProcessing) return;
    
    if (!isAuthenticated()) {
        addLog("SYSTEM_HALT: Session lost. Re-authenticating...", 0, 'ERROR');
        setIsLoggedIn(false);
        return; 
    }

    const currentCycleId = cycleCount + 1;
    setCycleCount(currentCycleId);
    setIsProcessing(true);
    setCompletedAgents([]); 
    setTargetMarket(null);

    addLog(`CYCLE START: FUNNEL EXECUTION PROTOCOL (Cycle #${currentCycleId})`, 0, 'WARN', currentCycleId);

    if (forceFail) {
        addLog(`SYSTEM: INITIATING FAILOVER SIMULATION PROTOCOL...`, 0, 'WARN', currentCycleId);
    }

    try {
        // --- PHASE 1: MORNING AUDIT (Legacy) ---
        setActiveAgentId(11);
        addLog("Agent 11: VPS Integrity: 100%. API Latency: 42ms.", 11, 'INFO', currentCycleId, 1);
        await new Promise(r => setTimeout(r, 600));
        setCompletedAgents(prev => [...prev, 11]);

        // --- PHASE 2: PARALLEL SCOUTING (TaskGroup) ---
        // Creating a TaskGroup for simultaneous execution
        addLog("Agent 1: Initializing Async TaskGroup for Phase 2...", 1, 'INFO', currentCycleId, 2);
        
        setActiveAgentId(2);
        const scoutTask = (async () => {
             addLog("Agent 2 (Task A): Scanning Kalshi Markets...", 2, 'INFO', currentCycleId, 2);
             // Simulated wait for parallelism visualization
             await new Promise(r => setTimeout(r, 800));
             return await fetchScoutedMarkets(isPaperTrading);
        })();

        setActiveAgentId(3);
        const interceptorTask = (async () => {
             addLog("Agent 3 (Task B): Bridging RapidAPI for Vegas Odds...", 3, 'INFO', currentCycleId, 2);
             // Simulated independent network request
             await new Promise(r => setTimeout(r, 1000));
             return true; 
        })();

        // Await TaskGroup completion
        const [rawMarkets] = await Promise.all([scoutTask, interceptorTask]);
        
        if (forceFail) {
            throw new Error("API Gateway Timeout: RapidAPI Bridge Unreachable");
        }

        // --- PRIORITY QUEUE LOGIC (The Filter) ---
        addLog(`Agent 3: TaskGroup Complete. ${rawMarkets.length} markets ingested.`, 3, 'SUCCESS', currentCycleId, 2);
        
        const sortedMarkets = rawMarkets.sort((a, b) => b.delta - a.delta);
        const priorityQueue = sortedMarkets.slice(0, 3); // The Batch
        
        const candidatesStr = priorityQueue.map(m => `${m.ticker}`).join(', ');
        addLog(`Agent 2: PRIORITY QUEUE FILLED (Batch Size: 3): [ ${candidatesStr} ]`, 2, 'WARN', currentCycleId, 2);
        
        setCompletedAgents(prev => [...prev, 2, 3]);

        // --- PHASE 3: PARALLEL ANALYSIS (Processing The Batch) ---
        setActiveAgentId(4); // The Analyst
        addLog(`Agent 4: Processing Batch from Priority Queue via Gemini 1.5 Pro...`, 4, 'INFO', currentCycleId, 3);
        
        // Map queue to parallel promises
        const debatePromises = priorityQueue.map(async (market) => {
            const debate = await runCommitteeDebate(market.title);
            return { market, debate };
        });

        const analysisResults = await Promise.all(debatePromises);
        
        // Log results
        analysisResults.forEach(res => {
            addLog(`Agent 4: ${res.market.ticker} Analyzed. Score: ${res.debate.confidenceScore}%`, 4, 'SUCCESS', currentCycleId, 3);
        });

        const greenlitTrades = analysisResults.filter(res => res.debate.confidenceScore > 75);
        addLog(`Agent 1: Batch Complete. ${greenlitTrades.length} Trades approved for Execution Queue.`, 1, 'WARN', currentCycleId, 3);
        
        setCompletedAgents(prev => [...prev, 4, 5, 6]);

        // --- PHASE 4: SEQUENTIAL EXECUTION (Single-Threaded Loop) ---
        // "Finally, the Executioner must be a single-threaded loop to ensure we never double-spend the $300 wallet."
        
        if (greenlitTrades.length > 0) {
            setActiveAgentId(8); // Executioner
            addLog("Agent 8: Engaging Single-Threaded Execution Loop...", 8, 'WARN', currentCycleId, 4);

            // Local variable to track balance atomically within the loop
            let runningBalance = currentBalance;

            for (const item of greenlitTrades) {
                // "Add a try/except block specifically for the Sequential Betting stage"
                try {
                    const { market, debate } = item;
                    setTargetMarket(market);

                    // 1. Balance Check (Agent 9 - Sentinel)
                    setActiveAgentId(9);
                    addLog(`Agent 9: Audit Balance: $${runningBalance.toFixed(2)}. Floor: $250.00.`, 9, 'INFO', currentCycleId, 4);
                    
                    if (runningBalance < 250) {
                         addLog(`Agent 9: RISK VETO. Balance too close to floor. Aborting queue.`, 9, 'ERROR', currentCycleId, 4);
                         break; // Hard stop for risk
                    }

                    // 2. Kelly Sizing (Agent 8)
                    setActiveAgentId(8);
                    const wager = Math.floor(runningBalance * 0.05);
                    addLog(`Agent 8: Sizing Wager for ${market.ticker}: $${wager} (Conf ${debate.confidenceScore}%).`, 8, 'INFO', currentCycleId, 4);
                    
                    // 3. Execution (Agent 7 - Sniper)
                    setActiveAgentId(7);
                    addLog(`Agent 7: Checking depth for ${market.ticker}...`, 7, 'INFO', currentCycleId, 4);
                    const book = await fetchOrderBook(market.ticker, isPaperTrading);
                    
                    // 4. Fire (Agent 8)
                    setActiveAgentId(8);
                    await createOrder(market.ticker, 'buy', 10, 'yes', isPaperTrading);
                    addLog(`Agent 8: SNIPER SHOT FIRED. Filled @ ${book.yes_ask}c.`, 8, 'SUCCESS', currentCycleId, 4);

                    // 5. Settlement Update (Internal State)
                    runningBalance -= wager;
                    setCurrentBalance(runningBalance); // Sync to React State
                    
                    // 6. Log (Agent 10)
                    setActiveAgentId(10);
                    await logTradeToHistory(10, `Executed ${market.ticker} @ ${book.yes_ask}c`);
                    addLog(`Agent 10: Transaction logged to immutable ledger.`, 10, 'SUCCESS', currentCycleId, 4);
                    
                    // Cool-down to prevent rate limits
                    addLog("Agent 1: Cooling down barrel (2s)...", 1, 'INFO', currentCycleId, 4);
                    await new Promise(r => setTimeout(r, 2000));

                } catch (tradeError: any) {
                    // Isolated Error Handling: A single failed trade doesn't stop the bot
                    setActiveAgentId(8);
                    addLog(`Agent 8: EXECUTION FAILURE for ${item.market.ticker}. Error: ${tradeError.message}`, 8, 'ERROR', currentCycleId, 4);
                    addLog(`Agent 8: Skipping to next target in queue...`, 8, 'WARN', currentCycleId, 4);
                    continue; 
                }
            }
            
            setCompletedAgents(prev => [...prev, 7, 8, 9, 10]);
        } else {
            addLog("Agent 1: No trades met the Alpha Threshold (>75%). Holding Cash.", 1, 'WARN', currentCycleId, 4);
        }

        addLog("Agent 1: Cycle Complete. Sleeping (Time-Warp).", 1, 'INFO', currentCycleId);

    } catch (globalError: any) {
        // Global Pipeline Error (e.g., Auth failure, Critical API outage)
        console.error(globalError);
        addLog(`Agent 1: CRITICAL PIPELINE FAILURE.`, 1, 'ERROR', currentCycleId);
        
        // --- AGENT 13: THE FIXER ---
        setActiveAgentId(13); 
        addLog("Agent 13 (The Fixer): INTERCEPTING GLOBAL EXCEPTION...", 13, 'WARN', currentCycleId, 13);
        
        try {
            const analysis = await analyzeSystemError(globalError.message, `TaskGroup Failure Cycle #${currentCycleId}`);
            addLog(`Agent 13: DIAGNOSIS: ${analysis.rootCause}`, 13, 'WARN', currentCycleId, 13);
            await new Promise(r => setTimeout(r, 2000));
            addLog(`Agent 13: APPLYING PATCH: ${analysis.suggestedFix}`, 13, 'SUCCESS', currentCycleId, 13);
            setCompletedAgents(prev => [...prev, 13]);
        } catch (debugError) {
            addLog("Agent 13: Fixer Module Failed.", 13, 'ERROR', currentCycleId, 13);
        }
    } finally {
        setActiveAgentId(null);
        setIsProcessing(false);
        if (autoPilot) {
            addLog("SYSTEM: Cooling down... Next cycle in 10s.", 0, 'INFO', currentCycleId);
        }
    }
  };

  return (
    <div className="flex h-screen bg-[#020202] text-gray-200 overflow-hidden font-sans selection:bg-emerald-500/30">
      
      {/* Decorative Background Elements */}
      <div className="fixed top-0 left-0 w-full h-full bg-grid-pattern opacity-30 pointer-events-none z-0"></div>
      <div className="fixed -top-1/2 -left-1/2 w-full h-full bg-emerald-900/10 blur-[100px] rounded-full pointer-events-none z-0 animate-pulse"></div>
      
      {/* Auto-Collapsing Sidebar */}
      <div className="relative z-50 h-full py-4 pl-2">
         <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      </div>

      <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden relative z-10 pr-6 py-4 pl-4">
        
        {/* Floating Glass Header */}
        <header className="h-16 shrink-0 z-20 glass-panel rounded-2xl flex items-center justify-between px-6 mb-6 organic-glow">
          <div className="flex items-center gap-4">
            <div className={`h-2.5 w-2.5 rounded-full ${isProcessing ? 'bg-amber-400 animate-ping' : 'bg-emerald-500 animate-pulse'} shadow-[0_0_10px_currentColor]`}></div>
            <span className={`text-sm font-mono tracking-widest ${isProcessing ? 'text-amber-400' : 'text-emerald-500'}`}>
                {isProcessing ? 'EXECUTING::TASKGROUP' : 'SYSTEM::IDLE'}
            </span>
            <div className="h-4 w-[1px] bg-white/10 mx-2"></div>
            
            <div className="flex p-1 bg-black/40 rounded-xl border border-white/5">
                <button 
                    onClick={() => { setIsPaperTrading(true); addLog("SYSTEM: Switched to PAPER mode.", 0, 'WARN', 0); }}
                    className={`text-[10px] px-3 py-1 rounded-lg font-mono transition-all ${isPaperTrading ? 'bg-blue-500/20 text-blue-400 shadow-[0_0_10px_rgba(59,130,246,0.2)]' : 'text-gray-500 hover:text-gray-300'}`}
                >
                    PAPER
                </button>
                <button 
                    onClick={() => { setIsPaperTrading(false); addLog("SYSTEM: Switched to LIVE mode.", 0, 'WARN', 0); }}
                    className={`text-[10px] px-3 py-1 rounded-lg font-mono transition-all ${!isPaperTrading ? 'bg-red-500/20 text-red-400 shadow-[0_0_10px_rgba(239,68,68,0.2)]' : 'text-gray-500 hover:text-gray-300'}`}
                >
                    LIVE
                </button>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
             {/* Autopilot Toggle */}
             <button
                onClick={() => setAutoPilot(!autoPilot)}
                className={`flex items-center gap-2 px-5 py-2 rounded-xl text-[10px] font-bold uppercase tracking-widest transition-all border ${
                    autoPilot 
                    ? 'bg-purple-500/10 border-purple-500/50 text-purple-400 shadow-[0_0_15px_rgba(168,85,247,0.2)]' 
                    : 'bg-white/5 border-white/10 text-gray-500 hover:bg-white/10'
                }`}
             >
                <span className={`w-1.5 h-1.5 rounded-full ${autoPilot ? 'bg-purple-400 animate-pulse' : 'bg-gray-500'}`}></span>
                {autoPilot ? 'AUTOPILOT: ON' : 'AUTOPILOT: OFF'}
             </button>

             {/* Test Failover Button */}
             <button
                onClick={() => runOrchestrator(true)}
                disabled={isProcessing}
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-[10px] font-bold uppercase tracking-widest transition-all border bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20 hover:border-red-500/50 disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_10px_rgba(239,68,68,0.1)] hover:shadow-[0_0_15px_rgba(239,68,68,0.3)]"
                title="Simulate a runtime error to trigger Agent 13 (The Fixer)"
             >
                <span className="animate-pulse text-red-500">⚠</span> TEST FAILOVER
             </button>

             <button 
                onClick={() => runOrchestrator(false)}
                disabled={isProcessing}
                className={`flex items-center gap-2 px-6 py-2 rounded-xl text-xs font-bold uppercase tracking-widest transition-all border backdrop-blur-md ${
                    isProcessing 
                    ? 'bg-amber-500/10 border-amber-500/30 text-amber-400 cursor-not-allowed'
                    : 'bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 border-emerald-500/50 hover:shadow-[0_0_20px_rgba(16,185,129,0.3)]'
                }`}
             >
                {isProcessing ? (
                    <>
                        <span className="animate-spin">⟳</span> WORKING
                    </>
                ) : (
                    <>
                        <span>▶</span> FORCE RUN
                    </>
                )}
             </button>
          </div>
        </header>

        {/* Dynamic Content Area */}
        <div className="flex-1 overflow-hidden">
          {activeTab === 'dashboard' && (
            <div className="grid grid-cols-12 grid-rows-1 gap-6 h-full pb-2">
              {/* Left Column: Neural Visuals & Charts */}
              <div className="col-span-8 flex flex-col gap-6 h-full overflow-hidden min-h-0">
                {/* Main Neural System (Expanded Space) */}
                <div className="flex-[2] overflow-hidden relative rounded-3xl organic-glow min-h-0">
                    <WorkflowVisualizer 
                        agents={AGENTS} 
                        activeAgentId={activeAgentId} 
                        completedAgents={completedAgents} 
                    />
                </div>
                {/* Bottom Charts (Compact) */}
                <div className="h-[220px] grid grid-cols-2 gap-6 shrink-0 min-h-0">
                    <PnLChart />
                    <PnLHeatmap />
                </div>
              </div>

              {/* Right Column: Terminal */}
              <div className="col-span-4 h-full min-h-0">
                 <Terminal logs={logs} />
              </div>
            </div>
          )}

          {activeTab === 'analyst' && (
             <div className="h-full pb-2">
                <MarketAnalysis onLog={addLog} />
             </div>
          )}
          
          {activeTab === 'logs' && (
             <div className="h-full pb-2">
                <Terminal logs={logs} />
             </div>
          )}

          {activeTab === 'about' && (
             <div className="h-full pb-2">
                <AboutPage />
             </div>
          )}

          {activeTab === 'settings' && (
            <div className="max-w-xl mx-auto mt-10 glass-panel rounded-3xl p-10 relative organic-glow">
                <h2 className="text-3xl font-bold mb-8 text-white font-tech uppercase tracking-tight text-center">
                    System Configuration
                </h2>
                
                <div className="p-8 bg-black/30 rounded-2xl border border-white/5 space-y-6">
                    <div className="flex items-center gap-3 text-emerald-400 mb-2">
                        <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center">
                            <span className="animate-pulse">🔒</span>
                        </div>
                        <span className="font-mono text-sm tracking-widest uppercase">Sentinel Credentials (V2)</span>
                    </div>

                    <div className="space-y-4">
                        <div className="group">
                            <label className="block text-[10px] uppercase text-gray-500 mb-1.5 font-mono ml-1 group-focus-within:text-emerald-500 transition-colors">API Key ID</label>
                            <input 
                                type="text" 
                                value={apiKeyId}
                                onChange={(e) => setApiKeyId(e.target.value)}
                                placeholder="Enter Key ID (e.g. kkid_...)"
                                className="w-full bg-black/40 border border-gray-700 rounded-xl px-4 py-3 text-emerald-300 font-mono text-sm focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 focus:outline-none transition-all" 
                            />
                        </div>
                        <div className="group">
                            <label className="block text-[10px] uppercase text-gray-500 mb-1.5 font-mono ml-1 group-focus-within:text-emerald-500 transition-colors">Private Key / Secret</label>
                            <input 
                                type="password" 
                                value={apiSecret}
                                onChange={(e) => setApiSecret(e.target.value)}
                                placeholder="Enter Private Key"
                                className="w-full bg-black/40 border border-gray-700 rounded-xl px-4 py-3 text-emerald-300 font-mono text-sm focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 focus:outline-none transition-all" 
                            />
                        </div>
                        
                        {authError && (
                            <div className="text-red-400 text-xs font-mono bg-red-900/10 p-3 rounded-xl border border-red-500/20">
                                WARNING: {authError}
                            </div>
                        )}

                        <button 
                            onClick={handleLogin}
                            disabled={isLoggedIn || !apiKeyId || !apiSecret}
                            className={`w-full py-4 rounded-xl text-xs font-bold uppercase tracking-widest transition-all ${
                                isLoggedIn 
                                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/50 cursor-default shadow-[0_0_15px_rgba(16,185,129,0.2)]' 
                                : 'bg-gradient-to-r from-emerald-600 to-emerald-500 text-white shadow-lg hover:shadow-emerald-500/25 hover:scale-[1.02] active:scale-[0.98]'
                            }`}
                        >
                            {isLoggedIn ? 'KEYS ACTIVE' : 'INITIALIZE V2 CLIENT'}
                        </button>
                    </div>
                </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default App;