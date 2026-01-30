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
import { useStore } from './store/useStore';
import { useAuth } from './hooks/useAuth';
import LogisticsCenter from './components/LogisticsCenter';
import SensesMetrics from './components/SensesMetrics';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { AgentWorkflowGraph, WorkflowControls, WorkflowTimeline } from './components/agent-workflow';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');

  const addLogToOrchestrator = (msg: string, _id: number, _level: string) => {
    // This will be handled by the backend broadcast,
    // but for local UI feedback before SSE is established:
    console.log(`[UI LOG] ${msg}`);
  };

  // New auth system - Demo/Production mode
  const {
    isAuthenticated: isLoggedIn,
    authMode,
    isAuthenticating,
    authError,
    login,
  } = useAuth();

  const orchestratorProps = useOrchestrator(isLoggedIn, authMode === 'demo');

  const [viewedAgentId, setViewedAgentId] = useState<number | null>(null);

  const handleSelectAgent = (id: number) => {
    setViewedAgentId(id);
  };

  // Demo animation handler - manually triggers workflow animations
  const handleDemoAnimation = () => {
    console.log('[App] Starting demo animation...');
    const store = useStore.getState();

    // Sequential animation through all 4 agents
    const agents = [1, 2, 3, 4]; // SOUL -> SENSES -> BRAIN -> HAND
    const delays = [0, 1000, 2000, 3000];

    agents.forEach((agentId, index) => {
      setTimeout(() => {
        console.log(`[App] Demo animation: Activating agent ${agentId}`);
        store.setActiveAgentId(agentId);
        store.setAgentState(agentId, {
          status: 'active',
          lastAction: `Demo action ${index + 1}`,
          lastUpdated: new Date().toISOString(),
        });

        // Add transition
        const transition = {
          id: `demo-trans-${Date.now()}-${agentId}`,
          fromAgent: agentId,
          toAgent: agentId < 4 ? agentId + 1 : 4,
          flowType: ['authorization', 'opportunity', 'decision', 'execution'][index] as any,
          timestamp: new Date().toISOString(),
          data: { message: `Demo transition ${index + 1}` },
          active: true,
        };
        store.addTransition(transition);

        // Reset to idle after animation
        setTimeout(() => {
          store.setAgentState(agentId, { status: 'idle' });
        }, 2000);
      }, delays[index]);
    });

    // Reset all after sequence completes
    setTimeout(() => {
      store.setActiveAgentId(null);
      console.log('[App] Demo animation complete');
    }, 5000);
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

  // Show login screen when not authenticated
  if (!isLoggedIn) {
    return (
      <Login
        onLogin={login}
        authError={authError}
        isAuthenticating={isAuthenticating}
      />
    );
  }

  return (
    <div className="flex bg-[#020202] text-gray-300 h-screen font-sans selection:bg-emerald-500/30 overflow-hidden scanlines">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 flex flex-col min-w-0 bg-grid-pattern overflow-hidden relative">
        {/* Header Info */}
        <Card className="h-16 border-b border-white/5 flex items-center justify-between px-8 glass-panel z-10 shadow-xl rounded-none">
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
            <div
              className={`flex items-center p-1 bg-black/40 rounded-full border border-white/5 ${orchestratorProps.killSwitchActive || !isLoggedIn ? 'opacity-50' : ''}`}
            >
              <button
                onClick={() =>
                  !orchestratorProps.killSwitchActive &&
                  isLoggedIn &&
                  orchestratorProps.setAutoPilot(!orchestratorProps.autoPilot)
                }
                disabled={orchestratorProps.killSwitchActive || !isLoggedIn}
                className={`px-4 py-1.5 rounded-full text-[10px] font-bold transition-all ${
                  orchestratorProps.autoPilot
                    ? 'bg-emerald-500 text-black shadow-lg shadow-emerald-500/20'
                    : 'text-gray-500 hover:text-gray-300'
                } ${orchestratorProps.killSwitchActive || !isLoggedIn ? 'cursor-not-allowed' : ''}`}
              >
                AUTOPILOT
              </button>
              <button
                onClick={() =>
                  !orchestratorProps.killSwitchActive &&
                  isLoggedIn &&
                  !orchestratorProps.autoPilot &&
                  orchestratorProps.setAutoPilot(true)
                }
                disabled={orchestratorProps.killSwitchActive || !isLoggedIn}
                className={`px-4 py-1.5 rounded-full text-[10px] font-bold transition-all ${
                  !orchestratorProps.autoPilot
                    ? 'bg-white/10 text-white'
                    : 'text-transparent w-0 p-0 overflow-hidden'
                } ${orchestratorProps.killSwitchActive || !isLoggedIn ? 'cursor-not-allowed' : ''}`}
              >
                MANUAL
              </button>
            </div>

            <div className="h-6 w-px bg-white/10"></div>

            <Button
              onClick={() =>
                orchestratorProps.isProcessing
                  ? orchestratorProps.handleCancelCycle()
                  : orchestratorProps.runOrchestrator()
              }
              disabled={orchestratorProps.killSwitchActive || !isLoggedIn}
              className={`!py-1.5 !px-5 !text-[10px] tracking-widest btn-primary ${
                orchestratorProps.killSwitchActive || !isLoggedIn
                  ? 'opacity-50 cursor-not-allowed'
                  : orchestratorProps.isProcessing
                    ? 'bg-orange-500/20 hover:bg-orange-500/30 text-orange-400 border-orange-500/30'
                    : 'hover:scale-105 active:scale-95'
              }`}
            >
              {!isLoggedIn
                ? '🔗 LINK OFFLINE'
                : orchestratorProps.killSwitchActive
                  ? '🔒 LOCKED'
                  : orchestratorProps.isProcessing
                    ? 'CANCEL CYCLE'
                    : 'INITIATE CYCLE'}
            </Button>
          </div>
        </Card>

        {/* Kill Switch Modal */}

        <div className="flex-1 overflow-y-auto no-scrollbar relative z-0 p-6 lg:p-10">
          <div className="max-w-[1600px] mx-auto h-full">
            {activeTab === 'dashboard' && (
              <div className="flex flex-col gap-6 h-full animate-scale-in">
                {/* Top: Compact Terminal */}
                <div className="h-[280px] shrink-0">
                  <Terminal
                    timelineEvents={orchestratorProps.timelineEvents}
                    activeAgentId={orchestratorProps.activeAgentId}
                  />
                </div>

                {/* Bottom: Visualizer & Charts */}
                <div className="flex-1 grid grid-cols-12 gap-6 min-h-0">
                  <div className="col-span-12 xl:col-span-8 flex flex-col gap-6">
                    <LogisticsCenter />

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 flex-1">
                      <Card className="glass-panel rounded-[2rem] p-8 h-full min-h-[300px] shadow-lg hover:border-white/10 transition-colors">
                        <PnLChart />
                      </Card>
                      <Card className="glass-panel rounded-[2rem] p-8 h-full min-h-[300px] shadow-lg hover:border-white/10 transition-colors">
                        <PnLHeatmap />
                      </Card>
                    </div>
                  </div>

                  {/* Right Side: Senses Metrics & Additional Widgets */}
                  <div className="col-span-12 xl:col-span-4 flex flex-col gap-6">
                    <SensesMetrics
                      logs={orchestratorProps.logs}
                      cycleCount={orchestratorProps.cycleCount}
                    />
                    <Card className="glass-panel rounded-[2rem] p-6 flex-1 flex items-center justify-center border border-white/5">
                      <div className="text-center">
                        <div className="text-4xl mb-3">📊</div>
                        <div className="text-[10px] text-gray-500 font-mono uppercase tracking-widest">
                          Metrics Panel
                        </div>
                        <div className="text-xs text-gray-600 mt-1">Coming Soon</div>
                      </div>
                    </Card>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'workflow' && (
              <div className="animate-scale-in h-full">
                <div className="grid grid-cols-12 gap-6 h-[calc(100vh-140px)]">
                  {/* Left: Workflow Visualization */}
                  <div className="col-span-12 xl:col-span-9 flex flex-col gap-4">
                    {/* Workflow Controls */}
                    <WorkflowControls
                      isProcessing={orchestratorProps.isProcessing}
                      autoPilot={orchestratorProps.autoPilot}
                      killSwitchActive={orchestratorProps.killSwitchActive}
                      isLoggedIn={isLoggedIn}
                      onInitiateCycle={orchestratorProps.runOrchestrator}
                      onCancelCycle={orchestratorProps.handleCancelCycle}
                      onToggleAutopilot={() => orchestratorProps.setAutoPilot(!orchestratorProps.autoPilot)}
                      onReset={() => {
                        // Clear transitions and reset view
                        useStore.getState().clearTransitions?.();
                      }}
                      onDemoAnimation={handleDemoAnimation}
                    />

                    {/* Main Workflow Graph */}
                    <Card className="glass-panel rounded-[2rem] p-6 shadow-2xl border border-white/10 overflow-hidden flex-1">
                      <div className="flex items-center justify-between mb-4">
                        <div>
                          <h2 className="text-2xl font-tech font-bold text-white uppercase tracking-wider">
                            Agent Workflow
                          </h2>
                          <p className="text-[10px] text-gray-500 font-mono mt-1">
                            Real-time visualization of the 4 Mega-Agent pipeline
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                          <span className="text-[10px] font-mono text-emerald-400 uppercase tracking-wider">
                            Live
                          </span>
                        </div>
                      </div>
                      <div className="h-[calc(100%-80px)]">
                        <AgentWorkflowGraph />
                      </div>
                    </Card>
                  </div>

                  {/* Right: Senses Metrics & Timeline Panel */}
                  <div className="col-span-12 xl:col-span-3 flex flex-col gap-4">
                    <SensesMetrics
                      logs={orchestratorProps.logs}
                      cycleCount={orchestratorProps.cycleCount}
                    />
                    <WorkflowTimeline
                      transitions={(orchestratorProps as any).activeTransitions || []}
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
                  isLoggedIn={isLoggedIn}
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

                  {/* Kill Switch Section */}
                  <div
                    className={`p-5 rounded-xl border ${orchestratorProps.killSwitchActive ? 'bg-red-900/20 border-red-500/40' : 'bg-white/5 border-white/10'}`}
                  >
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <div className="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2">
                          ⚠️ Emergency Kill Switch
                        </div>
                        <div className="text-[10px] text-gray-500 font-mono mt-1">
                          Immediately stops all engines and blocks all actions until manually
                          deactivated.
                        </div>
                      </div>
                      <div
                        className={`px-3 py-1 rounded-full text-[10px] font-bold flex items-center gap-1.5 ${
                          orchestratorProps.killSwitchActive
                            ? 'bg-red-500 text-white animate-pulse'
                            : 'bg-gray-700 text-gray-400'
                        }`}
                      >
                        <span
                          className={`w-2 h-2 rounded-full ${orchestratorProps.killSwitchActive ? 'bg-white' : 'bg-gray-500'}`}
                        ></span>
                        {orchestratorProps.killSwitchActive ? 'ACTIVE' : 'INACTIVE'}
                      </div>
                    </div>

                    <div className="flex gap-3">
                      {orchestratorProps.killSwitchActive ? (
                        <button
                          onClick={orchestratorProps.handleDeactivateKillSwitch}
                          className="flex-1 py-2.5 px-4 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 border border-emerald-500/30 rounded-lg text-[11px] font-bold uppercase tracking-wider transition-all"
                        >
                          🟢 Deactivate Kill Switch
                        </button>
                      ) : (
                        <button
                          onClick={() => {
                            if (
                              window.confirm(
                                '⚠️ ACTIVATE KILL SWITCH?\n\nThis will:\n• Stop all engines immediately\n• Cancel any running cycles\n• Block all manual and automated actions\n\nSystem will remain locked until you deactivate.'
                              )
                            ) {
                              orchestratorProps.handleActivateKillSwitch();
                            }
                          }}
                          className="flex-1 py-2.5 px-4 bg-red-900/30 hover:bg-red-600/40 text-red-400 border border-red-500/30 rounded-lg text-[11px] font-bold uppercase tracking-wider transition-all"
                        >
                          🔴 Activate Kill Switch
                        </button>
                      )}
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
