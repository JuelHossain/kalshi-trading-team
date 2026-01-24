import React, { useState } from 'react';
import Sidebar from './components/Sidebar';

import Terminal from './components/Terminal';
import AgentsPage from './components/AgentsPage';
import MarketAnalysis from './components/MarketAnalysis';
import AboutPage from './components/AboutPage';
import PnLChart from './components/PnLChart';
import PnLHeatmap from './components/PnLHeatmap';
import Login from './components/Login';
import { useOrchestrator } from './hooks/useOrchestrator';
import { useAuth } from './hooks/useAuth';
import SimulationResults from './components/SimulationResults';
import VaultGauge from './components/VaultGauge';
import LogisticsCenter from './components/LogisticsCenter';

interface QueueItem {
  id: string;
  data: unknown;
}

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isPaperTrading, setIsPaperTrading] = useState(true);

  // Queue states for Logistics Center
  const [opportunityQueue] = useState<QueueItem[]>([]);
  const [executionQueue] = useState<QueueItem[]>([]);
  const [scoutStatus] = useState('active');
  const [brainStatus] = useState('idle');
  const [sniperStatus] = useState('ready');

  const addLogToOrchestrator = (msg: string, _id: number, _level: string) => {
    // This will be handled by the backend broadcast,
    // but for local UI feedback before SSE is established:
    console.log(`[UI LOG] ${msg}`);
  };

  const {
    apiKeyId,
    setApiKeyId,
    apiSecret,
    setApiSecret,
    isLoggedIn,
    isAuthenticating,
    authError,
    handleLogin,
  } = useAuth(addLogToOrchestrator, isPaperTrading);

  const orchestratorProps = useOrchestrator(isLoggedIn, isPaperTrading);

  const [viewedAgentId, setViewedAgentId] = useState<number | null>(null);

  const handleSelectAgent = (id: number) => {
    setViewedAgentId(id);
  };

  // Header Status Logic
  const getStatusColor = () => {
    if (isAuthenticating) return 'bg-blue-500 shadow-[0_0_10px_#3b82f6]';
    if (!isLoggedIn) return 'bg-red-500 shadow-[0_0_10px_#ef4444]';
    if (orchestratorProps.isProcessing) return 'bg-emerald-500 shadow-[0_0_10px_#10b981]';
    return 'bg-orange-500 shadow-[0_0_10px_#f97316]';
  };

  const getStatusText = () => {
    if (isAuthenticating) return 'Neural Link Establishing...';
    if (!isLoggedIn) return 'Neural Link Offline';
    if (orchestratorProps.isProcessing) return 'Neural Link Active';
    return 'Neural Link Standby';
  };

  if (!isLoggedIn && !isPaperTrading) {
    return (
      <Login
        apiKeyId={apiKeyId}
        setApiKeyId={setApiKeyId}
        apiSecret={apiSecret}
        setApiSecret={setApiSecret}
        isPaperTrading={isPaperTrading}
        setIsPaperTrading={setIsPaperTrading}
        handleLogin={handleLogin}
        authError={authError}
      />
    );
  }

  return (
    <div className="flex bg-[#020202] text-gray-300 h-screen font-sans selection:bg-emerald-500/30 overflow-hidden scanlines">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 flex flex-col min-w-0 bg-grid-pattern overflow-hidden relative">
        {/* Header Info */}
        <div className="h-16 border-b border-white/5 flex items-center justify-between px-8 glass-panel z-10 shadow-xl">
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className={`w-3 h-3 rounded-full ${getStatusColor()}`}></div>
                {(orchestratorProps.isProcessing || isAuthenticating) && (
                  <div
                    className={`absolute inset-0 ${isAuthenticating ? 'bg-blue-500' : 'bg-emerald-500'} rounded-full animate-ping opacity-50`}
                  ></div>
                )}
              </div>
              <span className="text-[10px] font-mono font-bold uppercase tracking-[0.2em] text-emerald-500/80">
                {getStatusText()}
              </span>
            </div>

            <div className="h-6 w-px bg-white/10 hidden md:block"></div>

            <div className="hidden md:flex items-center gap-6">
              <div className="flex flex-col">
                <span className="text-[8px] font-mono text-gray-600 uppercase tracking-widest">
                  Operational Bankroll
                </span>
                <span className="text-sm font-mono font-bold text-white tracking-tighter">
                  ${(orchestratorProps.currentBalance ?? 0).toFixed(2)}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-[8px] font-mono text-gray-600 uppercase tracking-widest">
                  Active Cycle
                </span>
                <span className="text-sm font-mono font-bold text-emerald-400 tracking-tighter">
                  #{orchestratorProps.cycleCount}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center p-1 bg-black/40 rounded-full border border-white/5">
              <button
                onClick={() => orchestratorProps.setAutoPilot(!orchestratorProps.autoPilot)}
                className={`px-4 py-1.5 rounded-full text-[10px] font-bold transition-all ${orchestratorProps.autoPilot
                  ? 'bg-emerald-500 text-black shadow-lg shadow-emerald-500/20'
                  : 'text-gray-500 hover:text-gray-300'
                  }`}
              >
                AUTOPILOT
              </button>
              <button
                onClick={() => !orchestratorProps.autoPilot && orchestratorProps.setAutoPilot(true)}
                className={`px-4 py-1.5 rounded-full text-[10px] font-bold transition-all ${!orchestratorProps.autoPilot
                  ? 'bg-white/10 text-white'
                  : 'text-transparent w-0 p-0 overflow-hidden'
                  }`}
              >
                MANUAL
              </button>
            </div>

            <div className="h-6 w-px bg-white/10"></div>

            <button
              onClick={() =>
                orchestratorProps.isProcessing
                  ? orchestratorProps.handleKillSwitch()
                  : orchestratorProps.runOrchestrator()
              }
              className={`btn-primary !py-1.5 !px-5 !text-[10px] tracking-widest ${orchestratorProps.isProcessing ? 'bg-red-500/20 hover:bg-red-500/30 text-red-500 border-red-500/30' : 'hover:scale-105 active:scale-95'}`}
            >
              {orchestratorProps.isProcessing ? 'CANCEL CYCLE' : 'INITIATE CYCLE'}
            </button>
          </div>
        </div>

        {/* Kill Switch Modal */}

        <div className="flex-1 overflow-y-auto no-scrollbar relative z-0 p-6 lg:p-10">
          <div className="max-w-[1600px] mx-auto h-full">
            {activeTab === 'dashboard' && (
              <div className="grid grid-cols-12 gap-10 h-full animate-scale-in">
                {/* Left Content: Visualizer & Charts */}
                <div className="col-span-12 xl:col-span-8 flex flex-col gap-10">
                  <LogisticsCenter
                    opportunityQueue={opportunityQueue}
                    executionQueue={executionQueue}
                    scoutStatus={scoutStatus}
                    brainStatus={brainStatus}
                    sniperStatus={sniperStatus}
                  />

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
                    <VaultGauge vault={orchestratorProps.vault} />
                    <SimulationResults simulation={orchestratorProps.simulation} />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
                    <div className="glass-panel rounded-[2rem] p-8 h-[420px] shadow-lg hover:border-white/10 transition-colors">
                      <PnLChart />
                    </div>
                    <div className="glass-panel rounded-[2rem] p-8 h-[420px] shadow-lg hover:border-white/10 transition-colors">
                      <PnLHeatmap />
                    </div>
                  </div>
                </div>

                {/* Right Content: Terminal */}
                <div className="col-span-12 xl:col-span-4 flex flex-col min-h-[600px]">
                  <div className="h-full">
                    <Terminal
                      timelineEvents={orchestratorProps.timelineEvents}
                      activeAgentId={orchestratorProps.activeAgentId}
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'agents' && (
              <div className="animate-scale-in">
                <AgentsPage
                  onTestAgent={orchestratorProps.handleAgentTest}
                  onSelectAgent={handleSelectAgent}
                  activeAgentId={orchestratorProps.activeAgentId}
                  viewedAgentId={viewedAgentId}
                />
              </div>
            )}

            {activeTab === 'analysis' && (
              <div className="animate-scale-in">
                <MarketAnalysis market={orchestratorProps.targetMarket} />
              </div>
            )}

            {activeTab === 'logs' && (
              <div className="animate-scale-in h-full">
                <Terminal
                  timelineEvents={orchestratorProps.timelineEvents}
                  activeAgentId={orchestratorProps.activeAgentId}
                />
              </div>
            )}

            {activeTab === 'settings' && (
              <div className="animate-scale-in glass-panel p-10 rounded-[2rem]">
                <h2 className="text-2xl font-tech font-bold text-emerald-500 mb-6 tracking-widest uppercase">
                  System Configuration
                </h2>
                <div className="space-y-6 max-w-2xl">
                  <div className="flex justify-between items-center p-4 bg-white/5 rounded-xl border border-white/10">
                    <div>
                      <div className="text-sm font-bold text-white uppercase tracking-widest">
                        Environment
                      </div>
                      <div className="text-[10px] text-gray-500 font-mono">
                        Current operational environment
                      </div>
                    </div>
                    <div className="px-3 py-1 bg-emerald-500/20 text-emerald-400 rounded-full text-[10px] font-bold border border-emerald-500/30">
                      DEMO SANDBOX
                    </div>
                  </div>
                  <div className="flex justify-between items-center p-4 bg-white/5 rounded-xl border border-white/10">
                    <div>
                      <div className="text-sm font-bold text-white uppercase tracking-widest">
                        Safety Sentinel
                      </div>
                      <div className="text-[10px] text-gray-500 font-mono">
                        Agent 14 Principal Protection
                      </div>
                    </div>
                    <div className="px-3 py-1 bg-emerald-500 text-black rounded-full text-[10px] font-bold">
                      ACTIVE
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'about' && (
              <div className="animate-scale-in">
                <AboutPage />
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default App;
