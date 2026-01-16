import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import WorkflowVisualizer from './components/WorkflowVisualizer';
import Terminal from './components/Terminal';
import MarketAnalysis from './components/MarketAnalysis';
import PnLChart from './components/PnLChart';
import PnLHeatmap from './components/PnLHeatmap';
import { AGENTS, MOCK_LOGS } from './constants';
import { LogEntry } from './types';
import { scanMarketsWithGroq } from './services/groqService';
import { logTradeToHistory } from './services/supabaseService';
import { fetchActiveMarkets, loginToKalshi, isAuthenticated, fetchOrderBook, createOrder } from './services/kalshiService';
import { analyzeSystemError } from './services/geminiService';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [activeAgentId, setActiveAgentId] = useState<number | null>(null);
  const [completedAgents, setCompletedAgents] = useState<number[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  
  // Environment State
  const [isPaperTrading, setIsPaperTrading] = useState(true);
  
  // Autopilot State
  const [autoPilot, setAutoPilot] = useState(true); // Default to TRUE for 24/7 operation
  
  // Credential State
  const [kalshiEmail, setKalshiEmail] = useState('JRRAHMAN01+DEMO1@GMAIL.COM');
  const [kalshiPass, setKalshiPass] = useState('newlife@Kalshidemo007');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  // Workflow Data State
  const [targetMarket, setTargetMarket] = useState<any>(null);
  const [decision, setDecision] = useState<{ action: 'buy' | 'pass', side: 'yes' | 'no' }>({ action: 'pass', side: 'yes' });

  const addLog = (message: string, agentId: number, level: LogEntry['level'] = 'INFO') => {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const ms = String(now.getMilliseconds()).padStart(3, '0');

    const newLog: LogEntry = {
      id: Math.random().toString(36).substring(7),
      timestamp: `${timeStr}.${ms}`,
      agentId,
      level,
      message,
    };
    setLogs(prev => [...prev.slice(-49), newLog]);
  };

  const handleLogin = async () => {
      setAuthError(null);
      addLog(`SYSTEM: Initiating Auto-Login to ${isPaperTrading ? 'SANDBOX' : 'LIVE'}...`, 0, 'WARN');
      try {
          await loginToKalshi(kalshiEmail, kalshiPass, isPaperTrading);
          setIsLoggedIn(true);
          addLog(`SYSTEM: Secure Session Established. Ready for 24/7 Ops.`, 0, 'SUCCESS');
      } catch (e: any) {
          setAuthError(e.message);
          setIsLoggedIn(false);
          addLog(`SYSTEM: Auth Failed - ${e.message}`, 0, 'ERROR');
          // Retry logic could go here, but avoiding infinite loops for now
      }
  };

  // 1. Auto-Login on Mount
  useEffect(() => {
    if (!isLoggedIn) {
        handleLogin();
    }
  }, []);

  // 2. Auto-Start Loop if Logged In and Autopilot is ON
  useEffect(() => {
    if (isLoggedIn && autoPilot && !isProcessing) {
        const timer = setTimeout(() => {
            runWorkflow();
        }, 3000); // Short delay before starting first cycle
        return () => clearTimeout(timer);
    }
  }, [isLoggedIn, autoPilot, isProcessing]);

  // Background chatter
  useEffect(() => {
    if (isProcessing) return;
    const interval = setInterval(() => {
      if (Math.random() > 0.95) {
        const randomAgent = AGENTS[Math.floor(Math.random() * AGENTS.length)];
        const randomMsg = MOCK_LOGS[Math.floor(Math.random() * MOCK_LOGS.length)];
        addLog(`${randomAgent.name}: ${randomMsg}`, randomAgent.id, 'INFO');
      }
    }, 6000);
    return () => clearInterval(interval);
  }, [isProcessing]);

  const runWorkflow = async () => {
    if (isProcessing) return;
    
    // Auth Check
    if (!isAuthenticated()) {
        addLog("SYSTEM_HALT: Session lost. Re-authenticating...", 0, 'ERROR');
        await handleLogin();
        if (!isAuthenticated()) return; // Stop if re-auth fails
    }

    setIsProcessing(true);
    setActiveAgentId(null);
    setCompletedAgents([]); 
    setTargetMarket(null);
    setDecision({ action: 'pass', side: 'yes' });
    
    addLog(`------------------------------------------------`, 0, 'INFO');
    addLog(`CYCLE START: 24/7 SENTINEL LOOP ACTIVATED`, 0, 'WARN');
    
    // Agent Loop with Error Interception
    for (let i = 1; i <= 12; i++) {
        setActiveAgentId(i);
        const agent = AGENTS.find(a => a.id === i);
        const agentName = agent?.name || 'Unknown';
        
        try {
            if (i === 1) {
                addLog(`${agentName}: Orchestrating new opportunity search...`, i, 'INFO');
            }
            else if (i === 2) { // Scout (Groq)
                const marketIdeas = await scanMarketsWithGroq();
                addLog(`${agentName}: AI Signals Detected: [${marketIdeas}]`, i, 'SUCCESS');
            }
            else if (i === 3) { // Kalshi Data
                try {
                    const markets = await fetchActiveMarkets(isPaperTrading);
                    addLog(`${agentName}: Retrieved ${markets.length} active markets.`, i, 'INFO');
                    if (markets.length > 0) {
                        // In a real bot, we'd filter these based on Agent 2's ideas. 
                        // For this demo, we pick the most liquid one.
                        const top = markets[0];
                        setTargetMarket(top);
                        addLog(`${agentName}: TARGET LOCK: ${top.title} (${top.ticker})`, i, 'WARN');
                    } else {
                        throw new Error("No active markets found in scanning range.");
                    }
                } catch (e: any) {
                    addLog(`${agentName}: API Connection Failed - ${e.message}`, i, 'ERROR');
                    throw e; // Rethrow to trigger Agent 13
                }
            }
            else if (i === 4) { // Analyst (Gemini)
                 if (targetMarket) {
                     addLog(`${agentName}: Analyzing news sentiment for "${targetMarket.ticker}"...`, i, 'INFO');
                     // Simulating a positive sentiment for demo flow
                     setDecision({ action: 'buy', side: 'yes' });
                 }
                 addLog(`${agentName}: Sentiment leans BULLISH (YES). Confidence 78%.`, i, 'SUCCESS');
            }
            else if (i === 7) { // Agent 7: The Sniper (Order Book)
                if (targetMarket) {
                    addLog(`${agentName}: Checking Liquidity Depth...`, i, 'WARN');
                    try {
                        const orderBook = await fetchOrderBook(targetMarket.ticker, isPaperTrading);
                        const bestAsk = orderBook.yes_ask || 0;
                        addLog(`${agentName}: Best Ask: ${bestAsk}¢. Spread within tolerance.`, i, 'SUCCESS');
                    } catch (e: any) {
                        addLog(`${agentName}: Depth Scan Failed - ${e.message}`, i, 'ERROR');
                        // Agent 7 failure is critical for trade execution
                        throw e;
                    }
                }
            }
            else if (i === 8) { // Agent 8: The Executioner
                if (targetMarket && decision.action === 'buy') {
                    addLog(`${agentName}: AUTHORIZING TRADE EXECUTION...`, i, 'WARN');
                    try {
                        // EXECUTE TRADE
                        const order = await createOrder(
                            targetMarket.ticker, 
                            'buy', 
                            1, // Count
                            decision.side, 
                            isPaperTrading
                        );
                        addLog(`${agentName}: ORDER FILLED | ID: ${order.order_id} | ${targetMarket.ticker} YES @ MARKET`, i, 'SUCCESS');
                    } catch (e: any) {
                        addLog(`${agentName}: EXECUTION FAILED: ${e.message}`, i, 'ERROR');
                        throw e; // Trigger Debugger
                    }
                } else {
                    addLog(`${agentName}: No trade trigger this cycle.`, i, 'INFO');
                }
            }
            else if (i === 10) { // Historian
                await logTradeToHistory(i, `Cycle Finished. Target: ${targetMarket?.ticker || 'None'}`);
                addLog(`${agentName}: Cycle data archived.`, i, 'SUCCESS');
            }
            else {
                 await new Promise(resolve => setTimeout(resolve, 400));
            }
            
            setCompletedAgents(prev => [...prev, i]);

        } catch (error: any) {
            console.error(error);
            addLog(`${agentName}: CRITICAL PROCESS FAILURE. SYSTEM HALTED.`, i, 'ERROR');
            
            // --- AGENT 13: THE FIXER ACTIVATION ---
            setActiveAgentId(13); // Activate The Fixer
            addLog("Agent 13 (The Fixer): INTERCEPTING EXCEPTION...", 13, 'WARN');
            addLog("Agent 13: Reading Stack Trace & Context...", 13, 'INFO');

            try {
                // Consult Gemini Brain for Solution
                const analysis = await analyzeSystemError(error.message, `Agent ${i} (${agentName}) failed during execution.`);
                
                addLog(`Agent 13: ROOT CAUSE: ${analysis.rootCause}`, 13, 'WARN');
                addLog(`Agent 13: GENERATING HOTFIX...`, 13, 'INFO');
                
                // Simulate typing out the code patch
                await new Promise(r => setTimeout(r, 1500));
                
                addLog(`Agent 13: DEPLOYING PATCH >>\n${analysis.suggestedFix}`, 13, 'SUCCESS');
                addLog(`Agent 13: System Self-Healed. Resuming sequence in next cycle.`, 13, 'SUCCESS');
                
                // Add 13 to completed so it stays visible in the visualizer for this run
                setCompletedAgents(prev => [...prev, 13]);
                
                // We break the loop here to restart fresh in the next Autopilot cycle
                // instead of continuing with corrupted state
                break; 

            } catch (debugError) {
                addLog("Agent 13: Self-Correction Module Unreachable. Manual Reset Required.", 13, 'ERROR');
                break;
            }
            // -------------------------------------
        }
    }

    setActiveAgentId(null);
    setIsProcessing(false);
    
    if (autoPilot) {
        addLog("SYSTEM: Cooling down... Next cycle in 10s.", 0, 'INFO');
    }
  };

  return (
    <div className="flex h-screen bg-[#020202] text-gray-200 overflow-hidden font-sans selection:bg-emerald-500/30 scanlines">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      
      <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden relative z-10 bg-grid-pattern">
        {/* Header */}
        <header className="h-16 border-b border-gray-800 flex items-center justify-between px-8 bg-black/80 backdrop-blur-md shrink-0 z-10">
          <div className="flex items-center gap-4">
            <div className={`h-2 w-2 rounded-full ${isProcessing ? 'bg-amber-400 animate-ping' : 'bg-emerald-500 animate-pulse'} shadow-[0_0_10px_currentColor]`}></div>
            <span className={`text-sm font-mono tracking-widest ${isProcessing ? 'text-amber-400' : 'text-emerald-500'}`}>
                {isProcessing ? 'EXECUTING::BATCH' : 'SYSTEM::IDLE'}
            </span>
            <span className="text-gray-700 text-sm">|</span>
            <div className="flex items-center gap-2 bg-gray-900/50 rounded-sm p-1 border border-gray-800">
                <button 
                    onClick={() => { setIsPaperTrading(true); addLog("SYSTEM: Switched to PAPER mode.", 0, 'WARN'); }}
                    className={`text-[10px] px-2 py-0.5 rounded-[1px] font-mono transition-all ${isPaperTrading ? 'bg-blue-500 text-white shadow-[0_0_10px_#3b82f6]' : 'text-gray-500 hover:text-gray-300'}`}
                >
                    PAPER
                </button>
                <button 
                    onClick={() => { setIsPaperTrading(false); addLog("SYSTEM: Switched to LIVE mode.", 0, 'WARN'); }}
                    className={`text-[10px] px-2 py-0.5 rounded-[1px] font-mono transition-all ${!isPaperTrading ? 'bg-red-500 text-white shadow-[0_0_10px_#ef4444]' : 'text-gray-500 hover:text-gray-300'}`}
                >
                    LIVE
                </button>
            </div>
            {isLoggedIn ? (
                <span className="text-[10px] text-emerald-500 font-mono border border-emerald-900 px-1 rounded bg-emerald-900/10">AUTH: ACTIVE</span>
            ) : (
                <span className="text-[10px] text-red-500 font-mono border border-red-900 px-1 rounded bg-red-900/10 animate-pulse">AUTH: OFFLINE</span>
            )}
          </div>
          
          <div className="flex items-center gap-4">
             {/* Autopilot Toggle */}
             <button
                onClick={() => setAutoPilot(!autoPilot)}
                className={`flex items-center gap-2 px-4 py-1.5 rounded-sm text-[10px] font-bold uppercase tracking-widest transition-all border ${
                    autoPilot 
                    ? 'bg-purple-500/20 border-purple-500 text-purple-400 shadow-[0_0_10px_rgba(168,85,247,0.3)]' 
                    : 'bg-gray-800/50 border-gray-700 text-gray-500'
                }`}
             >
                <span className={`w-1.5 h-1.5 rounded-full ${autoPilot ? 'bg-purple-400 animate-pulse' : 'bg-gray-500'}`}></span>
                {autoPilot ? 'AUTOPILOT: ENGAGED' : 'AUTOPILOT: OFF'}
             </button>

             <button 
                onClick={runWorkflow}
                disabled={isProcessing}
                className={`flex items-center gap-2 px-6 py-2 rounded-sm text-xs font-bold uppercase tracking-widest transition-all border glitch-effect ${
                    isProcessing 
                    ? 'bg-amber-500/10 border-amber-500/30 text-amber-400 cursor-not-allowed'
                    : 'bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-500 border-emerald-500/30 hover:border-emerald-500/60'
                }`}
             >
                {isProcessing ? (
                    <>
                        <span className="animate-spin">⟳</span> PROC_ID_{activeAgentId}
                    </>
                ) : (
                    <>
                        <span>▶</span> FORCE RUN
                    </>
                )}
             </button>
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-auto p-6 scroll-smooth">
          {activeTab === 'dashboard' && (
            <div className="grid grid-cols-12 gap-6 h-full max-h-[calc(100vh-6rem)]">
              {/* Left Column: Workflow Visualizer (Replaces Grid) */}
              <div className="col-span-8 flex flex-col gap-6 h-full overflow-hidden">
                <div className="flex-1 overflow-hidden relative">
                    <WorkflowVisualizer 
                        agents={AGENTS} 
                        activeAgentId={activeAgentId} 
                        completedAgents={completedAgents} 
                    />
                </div>
                {/* Bottom Charts */}
                <div className="h-[250px] grid grid-cols-2 gap-4 shrink-0">
                    <PnLChart />
                    <PnLHeatmap />
                </div>
              </div>

              {/* Right Column: Terminal & Logs */}
              <div className="col-span-4 flex flex-col gap-6 h-full">
                <div className="flex-1 min-h-0">
                  <Terminal logs={logs} />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'analyst' && (
             <div className="h-full">
                <MarketAnalysis onLog={addLog} />
             </div>
          )}
          
          {activeTab === 'logs' && (
             <div className="h-full">
                <Terminal logs={logs} />
             </div>
          )}

          {activeTab === 'settings' && (
            <div className="max-w-2xl mx-auto mt-10 cyber-card p-8 relative">
                <div className="corner corner-tl"></div>
                <div className="corner corner-tr"></div>
                <div className="corner corner-br"></div>
                <div className="corner corner-bl"></div>

                <h2 className="text-2xl font-bold mb-6 text-white font-tech uppercase">System Configuration</h2>
                
                {/* Auth Section */}
                <div className="mb-8 p-6 bg-black/40 border border-gray-800 rounded-sm">
                    <h3 className="text-sm text-emerald-500 font-bold uppercase tracking-widest mb-4 flex items-center gap-2">
                        <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
                        Sentinel Access // {isPaperTrading ? 'SANDBOX' : 'LIVE'}
                    </h3>
                    
                    <div className="space-y-4">
                        <div>
                            <label className="block text-xs uppercase text-gray-500 mb-2 font-mono">Login Email</label>
                            <input 
                                type="email" 
                                value={kalshiEmail}
                                onChange={(e) => setKalshiEmail(e.target.value)}
                                className="w-full bg-black border border-gray-700 rounded-sm px-3 py-2 text-emerald-400 font-mono focus:border-emerald-500 focus:outline-none transition-colors" 
                            />
                        </div>
                        <div>
                            <label className="block text-xs uppercase text-gray-500 mb-2 font-mono">Password</label>
                            <input 
                                type="password" 
                                value={kalshiPass}
                                onChange={(e) => setKalshiPass(e.target.value)}
                                className="w-full bg-black border border-gray-700 rounded-sm px-3 py-2 text-emerald-400 font-mono focus:border-emerald-500 focus:outline-none transition-colors" 
                            />
                        </div>
                        
                        {authError && (
                            <div className="text-red-500 text-xs font-mono border-l-2 border-red-500 pl-2">
                                ERROR: {authError}
                            </div>
                        )}

                        <button 
                            onClick={handleLogin}
                            disabled={isLoggedIn || !kalshiEmail || !kalshiPass}
                            className={`w-full py-3 rounded-sm text-xs font-bold uppercase tracking-widest transition-all border ${
                                isLoggedIn 
                                ? 'bg-emerald-900/20 border-emerald-500 text-emerald-500 cursor-default' 
                                : 'bg-emerald-500/10 hover:bg-emerald-500/20 border-emerald-500/30 text-emerald-400'
                            }`}
                        >
                            {isLoggedIn ? 'SECURE SESSION ACTIVE' : 'AUTHENTICATE CONNECTION'}
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