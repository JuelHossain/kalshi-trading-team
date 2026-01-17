import React from 'react';
import { AGENTS } from '../constants';

const AboutPage: React.FC = () => {
  return (
    <div className="h-full overflow-y-auto no-scrollbar glass-panel rounded-3xl p-8 border border-white/5 organic-glow relative animate-[fadeIn_0.5s_ease-out]">
        {/* Background Ambient Effects */}
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-emerald-900/10 blur-[120px] rounded-full pointer-events-none"></div>
        <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-blue-900/10 blur-[100px] rounded-full pointer-events-none"></div>

        {/* Header Section */}
        <div className="max-w-4xl mx-auto mb-16 text-center relative z-10 pt-4">
            <div className="inline-flex items-center justify-center p-3 mb-6 rounded-2xl bg-white/5 border border-white/5 shadow-[0_0_20px_rgba(16,185,129,0.1)] backdrop-blur-md">
                <span className="text-3xl">🧬</span>
            </div>
            <h1 className="text-5xl font-black font-tech text-white uppercase tracking-wider mb-6 drop-shadow-2xl">
                System <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-blue-500">Architecture</span>
            </h1>
            <p className="text-gray-400 font-mono text-sm leading-relaxed max-w-3xl mx-auto tracking-wide">
                <span className="text-emerald-400 font-bold">Kalshi Sentient Alpha</span> is a fully autonomous, high-frequency decentralized trading system powered by a recursive neural topology of <span className="text-white">{AGENTS.length} specialized AI agents</span>. It operates on a continuous 24/7 loop, identifying asymmetric risk/reward opportunities in prediction markets through a rigorous process of discovery, debate, simulation, and execution.
            </p>
        </div>

        {/* The Core Doctrine / Workflow */}
        <div className="max-w-6xl mx-auto mb-20 relative z-10">
             <div className="flex items-center gap-4 mb-6">
                 <div className="h-[1px] flex-1 bg-gradient-to-r from-transparent to-white/20"></div>
                 <h2 className="text-sm font-bold font-mono text-gray-500 uppercase tracking-[0.3em]">Operational Doctrine</h2>
                 <div className="h-[1px] flex-1 bg-gradient-to-l from-transparent to-white/20"></div>
             </div>

             <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="bg-black/40 p-6 rounded-2xl border border-white/5 hover:border-emerald-500/30 transition-all group">
                    <div className="text-emerald-500 text-2xl mb-4 group-hover:scale-110 transition-transform duration-300">📡</div>
                    <h3 className="text-white font-tech text-lg mb-2 uppercase tracking-wide">1. Discovery</h3>
                    <p className="text-gray-500 text-[10px] font-mono leading-5">
                        Broad-spectrum scanning using Groq (Llama 3 70B) ingests thousands of active markets. Filters apply strictly for liquidity ({'>'}$2k vol) and volatility events.
                    </p>
                </div>
                <div className="bg-black/40 p-6 rounded-2xl border border-white/5 hover:border-purple-500/30 transition-all group">
                    <div className="text-purple-500 text-2xl mb-4 group-hover:scale-110 transition-transform duration-300">🧠</div>
                    <h3 className="text-white font-tech text-lg mb-2 uppercase tracking-wide">2. Cognition</h3>
                    <p className="text-gray-500 text-[10px] font-mono leading-5">
                        Markets undergo "Committee Debate". Gemini 1.5 Pro simulates Optimist vs Pessimist viewpoints while Agent 5 runs 10k Monte Carlo simulations for EV.
                    </p>
                </div>
                <div className="bg-black/40 p-6 rounded-2xl border border-white/5 hover:border-red-500/30 transition-all group">
                    <div className="text-red-500 text-2xl mb-4 group-hover:scale-110 transition-transform duration-300">🛡️</div>
                    <h3 className="text-white font-tech text-lg mb-2 uppercase tracking-wide">3. Validation</h3>
                    <p className="text-gray-500 text-[10px] font-mono leading-5">
                        The Auditor (Agent 6) checks for "Whale Traps" and irregular volume. The Scraper (Agent 3) cross-references Vegas odds for arbitrage deltas.
                    </p>
                </div>
                <div className="bg-black/40 p-6 rounded-2xl border border-white/5 hover:border-blue-500/30 transition-all group">
                    <div className="text-blue-500 text-2xl mb-4 group-hover:scale-110 transition-transform duration-300">⚡</div>
                    <h3 className="text-white font-tech text-lg mb-2 uppercase tracking-wide">4. Execution</h3>
                    <p className="text-gray-500 text-[10px] font-mono leading-5">
                        Precision entry via Limit Orders based on Kelly Criterion sizing. The Accountant tracks spend while The Historian archives data for RAG training.
                    </p>
                </div>
             </div>
        </div>

        {/* Detailed Agent Roster */}
        <div className="max-w-7xl mx-auto relative z-10">
            <h2 className="text-2xl font-bold font-tech text-white uppercase tracking-widest mb-10 pl-4 border-l-4 border-emerald-500">
                Active Agent Roster
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {AGENTS.map(agent => (
                    <div key={agent.id} className="group relative bg-black/40 border border-white/5 rounded-xl p-5 hover:border-emerald-500/40 hover:bg-white/[0.02] transition-all duration-300 flex flex-col h-full">
                        {/* Hover Gradient */}
                        <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/0 blur-[60px] rounded-full group-hover:bg-emerald-500/10 transition-colors duration-500"></div>
                        
                        <div className="flex justify-between items-start mb-4 relative z-10">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center font-mono text-emerald-500 font-bold border border-white/10 text-lg shadow-inner">
                                    {agent.id}
                                </div>
                                <div>
                                    <h4 className="text-white font-tech uppercase tracking-wider text-base font-bold group-hover:text-emerald-400 transition-colors">{agent.name}</h4>
                                    <span className="text-[9px] text-gray-400 font-mono uppercase tracking-[0.2em] block mt-0.5">
                                        {agent.role}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <div className="space-y-4 flex-1">
                            {/* Primary Description */}
                            <div>
                                <p className="text-gray-300 text-[11px] font-mono leading-relaxed border-l border-white/10 pl-3 italic opacity-80">
                                    "{agent.description}"
                                </p>
                            </div>
                            
                            {/* Model Info */}
                            <div className="flex items-center gap-2 bg-black/20 p-2 rounded border border-white/5">
                                <span className="text-[10px] text-gray-600 uppercase font-bold">Model Core:</span>
                                <span className="text-[10px] text-emerald-500/80 font-mono">{agent.model}</span>
                            </div>

                            {/* Detailed Task List */}
                            <div className="bg-black/60 rounded-lg p-3 border border-white/5 flex-1">
                                <span className="text-[9px] text-gray-500 uppercase font-bold tracking-widest block mb-2 border-b border-white/5 pb-1">Protocols</span>
                                <ul className="text-[10px] text-gray-400 font-mono space-y-1.5">
                                    {getDetailedTasks(agent.role).map((task, i) => (
                                        <li key={i} className="flex gap-2 items-start">
                                            <span className="text-emerald-500/50 mt-0.5">›</span>
                                            <span className="leading-tight">{task}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
        
        {/* Footer */}
        <div className="max-w-2xl mx-auto mt-24 text-center border-t border-white/5 pt-10 pb-16 opacity-50 hover:opacity-100 transition-opacity">
            <div className="w-8 h-8 mx-auto mb-4 grayscale opacity-50">
                <span className="text-2xl">🦅</span>
            </div>
            <p className="font-tech uppercase text-[10px] tracking-[0.4em] text-gray-400">
                Sentinel Alpha Directive v2.1.0
            </p>
            <p className="font-mono text-[9px] text-gray-600 mt-2">
                "The market transfers wealth from the impatient to the patient."
            </p>
        </div>
    </div>
  );
};

// Helper to generate detailed task lists based on Agent Role
const getDetailedTasks = (role: string): string[] => {
    switch(role) {
        case 'Orchestrator': 
            return ['Initialize Cycle & Reset Global State', 'Monitor Global Profit Targets vs Principal', 'Manage Recursive Vault Locking Mechanism'];
        case 'Harvester': 
            return ['Scan Kalshi WebSocket Feed (WSS)', 'Filter Markets for Volume > $2000', 'Parse Event Contracts for High Volatility'];
        case 'Scraper': 
            return ['Fetch Odds from Pinnacle/Bovada/Polymarket', 'Calculate Implied Probability Delta', 'Flag Arbitrage Opportunities (>5% Spread)'];
        case 'Gemini Brain': 
            return ['Synthesize Real-Time News Context', 'Generate Optimist/Pessimist Arguments', 'Assign Weighted Confidence Score (0-100)'];
        case 'Simulator': 
            return ['Run 10,000 Monte Carlo Iterations', 'Calculate Kelly Criterion Edge', 'Stress Test Volatility Scenarios'];
        case 'Pessimist': 
            return ['Analyze Order Book Depth for "Spoofing"', 'Detect Whale Manipulation/Traps', 'Veto Low-Confidence Signals (<60%)'];
        case 'Order Book': 
            return ['Identify Support/Resistance Walls', 'Analyze Bid-Ask Spread Velocity', 'Optimize Entry Price Execution'];
        case 'Assassin': 
            return ['Execute Limit/Market Orders via API', 'Manage Fill Rate & Slippage Tolerance', 'Report Execution Status to Ledger'];
        case 'Sentinel': 
            return ['Track API Token Usage & Cost', 'Audit Daily Budget Caps (<$1.00/day)', 'Calculate ROI per Token Spent'];
        case 'Memory': 
            return ['Archive Trade Logs to Supabase DB', 'Update RAG Knowledge Base Vectors', 'Generate Post-Mortem Failure Analysis'];
        case 'Healer': 
            return ['Monitor System Heartbeat & Latency', 'Rotate API Keys on Rate Limit Errors', 'Auto-Restart Stalled Agents'];
        case 'UI Engineer': 
            return ['Render Real-Time Neural Topology', 'Visualize PnL Velocity & Heatmaps', 'Stream Terminal Logs via WebSocket'];
        case 'Debugger': 
            return ['Catch Runtime Exceptions (Try/Catch)', 'Analyze Stack Traces via Gemini Flash', 'Deploy Hotfix Patches Live'];
        default: 
            return ['Process Data Stream', 'Await Central Command Directive'];
    }
}

export default AboutPage;