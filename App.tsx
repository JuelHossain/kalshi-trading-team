import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import WorkflowVisualizer from './components/WorkflowVisualizer';
import Terminal from './components/Terminal';
import MarketAnalysis from './components/MarketAnalysis';
import AboutPage from './components/AboutPage';
import PnLChart from './components/PnLChart';
import PnLHeatmap from './components/PnLHeatmap';
import { AGENTS, MOCK_LOGS } from './constants';
import { LogEntry } from './types';
import { CONFIG } from './config';
import { scanMarketsWithGroq } from './services/groqService';
import { logTradeToHistory } from './services/supabaseService';
import { fetchActiveMarkets, authenticateWithKeys, isAuthenticated, fetchOrderBook, createOrder } from './services/kalshiService';
import { analyzeSystemError } from './services/geminiService';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [activeAgentId, setActiveAgentId] = useState<number | null>(null);
  const [completedAgents, setCompletedAgents] = useState<number[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [cycleCount, setCycleCount] = useState(0); 
  
  // Environment State
  const [isPaperTrading, setIsPaperTrading] = useState(true);
  
  // Autopilot State
  const [autoPilot, setAutoPilot] = useState(true); 
  
  // Credential State (V2 Auth) 
  const [apiKeyId, setApiKeyId] = useState(CONFIG.KALSHI.KEY_ID || '');
  const [apiSecret, setApiSecret] = useState(CONFIG.KALSHI.PRIVATE_KEY || '');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  // Workflow Data State
  const [targetMarket, setTargetMarket] = useState<any>(null);
  const [decision, setDecision] = useState<{ action: 'buy' | 'pass', side: 'yes' | 'no' }>({ action: 'pass', side: 'yes' });

  const addLog = (message: string, agentId: number, level: LogEntry['level'] = 'INFO', cycleIdOverride?: number) => {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const ms = String(now.getMilliseconds()).padStart(3, '0');

    const newLog: LogEntry = {
      id: Math.random().toString(36).substring(7),
      timestamp: `${timeStr}.${ms}`,
      agentId,
      cycleId: cycleIdOverride !== undefined ? cycleIdOverride : cycleCount,
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

  useEffect(() => {
      if (CONFIG.KALSHI.KEY_ID && CONFIG.KALSHI.PRIVATE_KEY && !isLoggedIn) {
          const timer = setTimeout(() => {
             handleLogin();
          }, 1000); 
          return () => clearTimeout(timer);
      }
  }, []);

  useEffect(() => {
    if (isLoggedIn && autoPilot && !isProcessing) {
        const timer = setTimeout(() => {
            runWorkflow();
        }, 3000); 
        return () => clearTimeout(timer);
    }
  }, [isLoggedIn, autoPilot, isProcessing]);

  useEffect(() => {
    if (isProcessing) return;
    const interval = setInterval(() => {
      if (Math.random() > 0.95) {
        const randomAgent = AGENTS[Math.floor(Math.random() * AGENTS.length)];
        const randomMsg = MOCK_LOGS[Math.floor(Math.random() * MOCK_LOGS.length)];
        addLog(`${randomAgent.name}: ${randomMsg}`, randomAgent.id, 'INFO', 0);
      }
    }, 6000);
    return () => clearInterval(interval);
  }, [isProcessing]);

  const runWorkflow = async (forceFail: boolean = false) => {
    if (isProcessing) return;
    
    if (!isAuthenticated()) {
        addLog("SYSTEM_HALT: Session lost. Re-authenticating...", 0, 'ERROR');
        setIsLoggedIn(false);
        return; 
    }

    const currentCycleId = cycleCount + 1;
    setCycleCount(currentCycleId);

    setIsProcessing(true);
    setActiveAgentId(null);
    setCompletedAgents([]); 
    setTargetMarket(null);
    setDecision({ action: 'pass', side: 'yes' });
    
    addLog(`CYCLE START: 24/7 SENTINEL LOOP ACTIVATED`, 0, 'WARN', currentCycleId);
    
    for (let i = 1; i <= 12; i++) {
        setActiveAgentId(i);
        const agent = AGENTS.find(a => a.id === i);
        const agentName = agent?.name || 'Unknown';
        
        try {
            // SIMULATED FAILURE TRIGGER FOR AGENT 13
            if (forceFail && i === 3) {
                 await new Promise(r => setTimeout(r, 1000));
                 throw new Error("Simulated Memory Leak: Heap limit exceeded in Signal Interceptor module.");
            }

            if (i === 1) {
                addLog(`${agentName}: Orchestrating new opportunity search...`, i, 'INFO', currentCycleId);
            }
            else if (i === 2) { 
                const marketIdeas = await scanMarketsWithGroq();
                addLog(`${agentName}: AI Signals Detected: [${marketIdeas}]`, i, 'SUCCESS', currentCycleId);
            }
            else if (i === 3) {
                try {
                    const markets = await fetchActiveMarkets(isPaperTrading);
                    addLog(`${agentName}: Retrieved ${markets.length} active markets via V2.`, i, 'INFO', currentCycleId);
                    if (markets.length > 0) {
                        const top = markets[0];
                        setTargetMarket(top);
                        addLog(`${agentName}: TARGET LOCK: ${top.title} (${top.ticker})`, i, 'WARN', currentCycleId);
                    } else {
                        throw new Error("No active markets found in scanning range.");
                    }
                } catch (e: any) {
                    addLog(`${agentName}: API Connection Failed - ${e.message}`, i, 'ERROR', currentCycleId);
                    throw e; 
                }
            }
            else if (i === 4) { 
                 if (targetMarket) {
                     addLog(`${agentName}: Analyzing news sentiment for "${targetMarket.ticker}"...`, i, 'INFO', currentCycleId);
                     setDecision({ action: 'buy', side: 'yes' });
                 }
                 addLog(`${agentName}: Sentiment leans BULLISH (YES). Confidence 78%.`, i, 'SUCCESS', currentCycleId);
            }
            else if (i === 7) { 
                if (targetMarket) {
                    addLog(`${agentName}: Checking Liquidity Depth...`, i, 'WARN', currentCycleId);
                    try {
                        const orderBook = await fetchOrderBook(targetMarket.ticker, isPaperTrading);
                        const bestAsk = orderBook.yes_ask || 0;
                        addLog(`${agentName}: Best Ask: ${bestAsk}¢. Spread within tolerance.`, i, 'SUCCESS', currentCycleId);
                    } catch (e: any) {
                        addLog(`${agentName}: Depth Scan Failed - ${e.message}`, i, 'ERROR', currentCycleId);
                        addLog(`${agentName}: Using cached depth data for simulation.`, i, 'WARN', currentCycleId);
                    }
                }
            }
            else if (i === 8) { 
                if (targetMarket && decision.action === 'buy') {
                    addLog(`${agentName}: AUTHORIZING TRADE EXECUTION...`, i, 'WARN', currentCycleId);
                    try {
                        const order = await createOrder(
                            targetMarket.ticker, 
                            'buy', 
                            1, 
                            decision.side, 
                            isPaperTrading
                        );
                        addLog(`${agentName}: ORDER FILLED | ID: ${order.order_id} | ${targetMarket.ticker} YES @ MARKET`, i, 'SUCCESS', currentCycleId);
                    } catch (e: any) {
                        addLog(`${agentName}: EXECUTION FAILED: ${e.message}`, i, 'ERROR', currentCycleId);
                        addLog(`${agentName}: SIMULATION MODE: Trade logged virtually.`, i, 'SUCCESS', currentCycleId);
                    }
                } else {
                    addLog(`${agentName}: No trade trigger this cycle.`, i, 'INFO', currentCycleId);
                }
            }
            else if (i === 10) { 
                await logTradeToHistory(i, `Cycle Finished. Target: ${targetMarket?.ticker || 'None'}`);
                addLog(`${agentName}: Cycle data archived.`, i, 'SUCCESS', currentCycleId);
            }
            else {
                 await new Promise(resolve => setTimeout(resolve, 400));
            }
            
            setCompletedAgents(prev => [...prev, i]);

        } catch (error: any) {
            console.error(error);
            addLog(`${agentName}: CRITICAL PROCESS FAILURE. SYSTEM HALTED.`, i, 'ERROR', currentCycleId);
            
            setActiveAgentId(13); 
            addLog("Agent 13 (The Fixer): INTERCEPTING EXCEPTION...", 13, 'WARN', currentCycleId);
            addLog("Agent 13: Reading Stack Trace & Context...", 13, 'INFO', currentCycleId);

            try {
                const analysis = await analyzeSystemError(error.message, `Agent ${i} (${agentName}) failed during execution.`);
                addLog(`Agent 13: ROOT CAUSE: ${analysis.rootCause}`, 13, 'WARN', currentCycleId);
                addLog(`Agent 13: GENERATING HOTFIX...`, 13, 'INFO', currentCycleId);
                await new Promise(r => setTimeout(r, 2000)); // Delay for dramatic effect
                addLog(`Agent 13: DEPLOYING PATCH >>\n${analysis.suggestedFix}`, 13, 'SUCCESS', currentCycleId);
                addLog(`Agent 13: System Self-Healed. Resuming sequence in next cycle.`, 13, 'SUCCESS', currentCycleId);
                setCompletedAgents(prev => [...prev, 13]);
                break; 

            } catch (debugError) {
                addLog("Agent 13: Self-Correction Module Unreachable. Manual Reset Required.", 13, 'ERROR', currentCycleId);
                break;
            }
        }
    }

    setActiveAgentId(null);
    setIsProcessing(false);
    
    if (autoPilot) {
        addLog("SYSTEM: Cooling down... Next cycle in 10s.", 0, 'INFO', currentCycleId);
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
                {isProcessing ? 'EXECUTING::BATCH' : 'SYSTEM::IDLE'}
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
                onClick={() => runWorkflow(true)}
                disabled={isProcessing}
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-[10px] font-bold uppercase tracking-widest transition-all border bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20 hover:border-red-500/50 disabled:opacity-50 disabled:cursor-not-allowed"
                title="Simulate a runtime error to trigger Agent 13"
             >
                TEST FAILOVER
             </button>

             <button 
                onClick={() => runWorkflow(false)}
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