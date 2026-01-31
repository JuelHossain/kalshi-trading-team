import React, { useMemo, useState, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { Card } from '@/components/ui/card';
import { LogEntry, TimelineEvent, SimulationState, VaultState, ErrorEvent } from '@shared/types';

interface FlowMetrics {
  totalOpportunities: number;
  totalExecutions: number;
  activeCycle: number;
  processingRate: number;
}

// --- REUSE EVENT DISPLAY COMPONENTS FROM TERMINAL ---

const VaultCard: React.FC<{ data: VaultState }> = ({ data }) => (
  <div className="bg-emerald-900/10 border border-emerald-500/20 rounded-lg p-2 my-1 backdrop-blur-sm">
    <div className="flex justify-between items-center">
      <span className="text-[9px] text-emerald-400 uppercase tracking-widest font-mono">
        Vault Balance
      </span>
      <span className="text-sm font-bold font-tech text-white">
        ${((data.total ?? 0) / 100).toFixed(2)}
      </span>
    </div>
  </div>
);

const SimulationCard: React.FC<{ data: SimulationState }> = ({ data }) => (
  <div className="bg-blue-900/10 border border-blue-500/20 rounded-lg p-2 my-1 backdrop-blur-sm">
    <div className="flex items-center gap-2">
      <span className="text-[9px] text-blue-400 uppercase tracking-widest font-mono">
        {data.ticker}
      </span>
      <span
        className={`px-1.5 py-0.5 rounded text-[8px] font-bold uppercase ${
          data.veto ? 'bg-red-500/20 text-red-500' : 'bg-emerald-500/20 text-emerald-500'
        }`}
      >
        {data.veto ? 'VETO' : 'OK'}
      </span>
      <span className="text-[9px] text-gray-400 font-mono">
        EV: {(data.evScore ?? 0).toFixed(2)}
      </span>
    </div>
  </div>
);

const LogLine: React.FC<{ log: LogEntry }> = ({ log }) => {
  const getLevelStyles = (level: string) => {
    switch (level) {
      case 'ERROR':
        return 'border-red-500 bg-red-500/10 text-red-400';
      case 'WARN':
      case 'WARNING':
        return 'border-yellow-500 bg-yellow-500/10 text-yellow-400';
      case 'SUCCESS':
        return 'border-emerald-500 bg-emerald-500/10 text-emerald-400';
      case 'INFO':
        return 'border-blue-500 bg-blue-500/5 text-blue-300';
      default:
        return 'border-gray-500 bg-gray-500/5 text-gray-400';
    }
  };

  const levelStyles = getLevelStyles(log.level);

  return (
    <div
      className={`flex gap-2 py-1 px-2 rounded hover:bg-white/5 transition-colors font-mono text-[9px] border-l-2 ${levelStyles}`}
    >
      <span className="text-gray-600 w-10 shrink-0 opacity-50">
        {log.timestamp.split('T')[1]?.split('.')[0]}
      </span>
      <span className="break-words flex-1">
        {log.message.replace(/^Agent \d+: /, '')}
        {log.count > 1 && <span className="text-gray-500"> ({log.count}x)</span>}
      </span>
    </div>
  );
};

const ErrorCard: React.FC<{ error: ErrorEvent }> = ({ error }) => {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return 'border-red-500 bg-red-500/20';
      case 'HIGH':
        return 'border-orange-500 bg-orange-500/20';
      case 'MEDIUM':
        return 'border-yellow-500 bg-yellow-500/20';
      default:
        return 'border-blue-500 bg-blue-500/20';
    }
  };

  return (
    <div className={`${getSeverityColor(error.severity)} border rounded-lg p-2 my-1`}>
      <div className="flex items-center gap-2">
        <span className="text-red-400 text-[9px] font-mono">{error.code}</span>
        <span className="text-xs text-red-200 truncate">{error.message}</span>
      </div>
    </div>
  );
};

// --- NEURAL TRACE EVENTS COMPONENT ---

interface NeuralTraceEventsProps {
  events: TimelineEvent[];
}

const NeuralTraceEvents: React.FC<NeuralTraceEventsProps> = ({ events }) => {
  if (events.length === 0) {
    return (
      <div className="text-[9px] text-gray-600 font-mono italic py-2 text-center">
        No events yet
      </div>
    );
  }

  return (
    <div className="space-y-1 max-h-48 overflow-y-auto no-scrollbar">
      {events.map((event) => {
        if (event.type === 'LOG') return <LogLine key={event.id} log={event.data as LogEntry} />;
        if (event.type === 'SIMULATION')
          return <SimulationCard key={event.id} data={event.data as SimulationState} />;
        if (event.type === 'VAULT')
          return <VaultCard key={event.id} data={event.data as VaultState} />;
        if (event.type === 'ERROR')
          return <ErrorCard key={event.id} error={event.data as ErrorEvent} />;
        if (event.type === 'FIXER') {
          return (
            <div
              key={event.id}
              className="text-[9px] text-yellow-400 font-mono py-1 px-2 bg-yellow-900/10 rounded"
            >
              🔧 {(event.data as any).action}
            </div>
          );
        }
        return null;
      })}
    </div>
  );
};

// --- AGENT PIPELINE CARD WITH NEURAL TRACE ---

interface AgentPipelineCardProps {
  id: number;
  name: string;
  title: string;
  icon: string;
  color: string;
  phase: number;
  state?: { status: string; lastAction: string; lastUpdated: string };
  isActive: boolean;
  isNext: boolean;
  events: TimelineEvent[];
  isExpanded: boolean;
  onToggle: () => void;
}

const AgentPipelineCard: React.FC<AgentPipelineCardProps> = ({
  name,
  title,
  icon,
  color,
  phase,
  state,
  isActive,
  isNext,
  events,
  isExpanded,
  onToggle,
}) => {
  const getColorClasses = (color: string, active: boolean) => {
    const colors = {
      emerald: {
        bg: active ? 'bg-emerald-500/20' : 'bg-emerald-500/5',
        border: active ? 'border-emerald-500/50' : 'border-emerald-500/20',
        text: active ? 'text-emerald-300' : 'text-emerald-400',
        glow: active ? 'shadow-emerald-500/30' : '',
      },
      blue: {
        bg: active ? 'bg-blue-500/20' : 'bg-blue-500/5',
        border: active ? 'border-blue-500/50' : 'border-blue-500/20',
        text: active ? 'text-blue-300' : 'text-blue-400',
        glow: active ? 'shadow-blue-500/30' : '',
      },
      purple: {
        bg: active ? 'bg-purple-500/20' : 'bg-purple-500/5',
        border: active ? 'border-purple-500/50' : 'border-purple-500/20',
        text: active ? 'text-purple-300' : 'text-purple-400',
        glow: active ? 'shadow-purple-500/30' : '',
      },
      orange: {
        bg: active ? 'bg-orange-500/20' : 'bg-orange-500/5',
        border: active ? 'border-orange-500/50' : 'border-orange-500/20',
        text: active ? 'text-orange-300' : 'text-orange-400',
        glow: active ? 'shadow-orange-500/30' : '',
      },
    };
    return colors[color as keyof typeof colors] || colors.emerald;
  };

  const classes = getColorClasses(color, isActive);

  return (
    <div
      className={`relative rounded-xl border transition-all duration-300 overflow-hidden ${classes.bg} ${classes.border} ${isActive ? classes.glow + ' shadow-lg' : ''}`}
    >
      {isNext && (
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent animate-shimmer pointer-events-none" />
      )}

      {/* Clickable Header */}
      <div onClick={onToggle} className="p-3 cursor-pointer hover:bg-white/5 transition-colors">
        <div className="flex items-center gap-3">
          {/* Icon */}
          <div
            className={`w-8 h-8 rounded-lg ${classes.bg} border ${classes.border} flex items-center justify-center text-sm shrink-0 ${isActive ? 'animate-pulse' : ''}`}
          >
            {icon}
          </div>

          {/* Agent Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className={`text-xs font-bold ${classes.text}`}>{name}</span>
              <span className="text-[9px] text-gray-500">P{phase}</span>
              {/* Event Count Badge */}
              {events.length > 0 && (
                <span
                  className={`px-1.5 py-0.5 rounded text-[8px] font-bold ${isActive ? 'bg-white/10' : 'bg-white/5'} text-gray-400`}
                >
                  {events.length}
                </span>
              )}
            </div>
            <div className="text-[10px] text-gray-400 font-mono truncate">
              {state?.lastAction || title}
            </div>
          </div>

          {/* Status Indicator */}
          <div className="flex items-center gap-2 shrink-0">
            {isActive ? (
              <div className="flex items-center gap-1">
                <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-ping" />
                <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
              </div>
            ) : (
              <div className="w-1.5 h-1.5 bg-gray-600 rounded-full" />
            )}
            {/* Expand/Collapse Icon */}
            <div
              className={`text-gray-500 transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}
            >
              ▼
            </div>
          </div>
        </div>
      </div>

      {/* Expandable Neural Trace Events */}
      <div
        className={`overflow-hidden transition-all duration-300 ${isExpanded ? 'max-h-64 opacity-100' : 'max-h-0 opacity-0'}`}
      >
        <div className="border-t border-white/5 bg-black/20 p-2">
          <div className="text-[8px] text-gray-500 uppercase tracking-wider font-mono mb-2">
            Neural Trace
          </div>
          <NeuralTraceEvents events={events} />
        </div>
      </div>
    </div>
  );
};

// --- MAIN LOGISTICS CENTER ---

const LogisticsCenter: React.FC = () => {
  const timelineEvents = useStore((state) => state.timelineEvents);
  const agentStates = useStore((state) => state.agentStates);
  const cycleCount = useStore((state) => state.cycleCount);
  const isProcessing = useStore((state) => state.isProcessing);
  const activeTransitions = useStore((state) => state.activeTransitions);

  // Real-time Synapse queue data
  const [queueData, setQueueData] = useState<{
    opportunities: { size: number; items: any[] };
    executions: { size: number; items: any[] };
    flowControl: { execution_queue_at_limit: boolean; limit: number };
  } | null>(null);

  // Track expanded agents
  const [expandedAgents, setExpandedAgents] = useState<Record<number, boolean>>({});
  const [activeAgentId, setActiveAgentId] = useState<number | null>(null);

  // Fetch Synapse queue data every 2 seconds
  useEffect(() => {
    const fetchQueueData = async () => {
      try {
        const res = await fetch('/api/synapse/queues');
        if (res.ok) {
          const data = await res.json();
          setQueueData(data);
        }
      } catch (e) {
        console.error('Failed to fetch queue data:', e);
      }
    };

    fetchQueueData();
    const interval = setInterval(fetchQueueData, 2000);
    return () => clearInterval(interval);
  }, []);

  // Auto-expand active agent
  useEffect(() => {
    const newActiveAgent = Object.entries(agentStates).find(
      ([, state]) => state?.status === 'active'
    )?.[0];
    const agentId = newActiveAgent ? parseInt(newActiveAgent) : null;

    if (agentId && agentId !== activeAgentId) {
      setActiveAgentId(agentId);
      setExpandedAgents((_prev) => ({
        // Collapse others, expand active
        1: agentId === 1,
        2: agentId === 2,
        3: agentId === 3,
        4: agentId === 4,
      }));
    }
  }, [agentStates, activeAgentId]);

  // Calculate flow metrics - Use real queue data from Synapse API
  const flowMetrics = useMemo<FlowMetrics>(() => {
    const recentEvents = timelineEvents.filter((e) => e.cycleId === cycleCount).length;
    const processingRate = cycleCount > 0 ? Math.round(recentEvents / 5) : 0;

    return {
      totalOpportunities: queueData?.opportunities?.size || 0,
      totalExecutions: queueData?.executions?.size || 0,
      activeCycle: cycleCount,
      processingRate,
    };
  }, [queueData, cycleCount, timelineEvents]);

  // Agent definitions
  const agents = useMemo(() => {
    return [
      {
        id: 1,
        name: 'SOUL',
        title: 'Authorization',
        icon: '👁️',
        color: 'emerald',
        state: agentStates[1],
        phase: 1,
      },
      {
        id: 2,
        name: 'SENSES',
        title: 'Surveillance',
        icon: '🔭',
        color: 'blue',
        state: agentStates[2],
        phase: 2,
      },
      {
        id: 3,
        name: 'BRAIN',
        title: 'Intelligence',
        icon: '🧠',
        color: 'purple',
        state: agentStates[3],
        phase: 3,
      },
      {
        id: 4,
        name: 'HAND',
        title: 'Execution',
        icon: '🤚',
        color: 'orange',
        state: agentStates[4],
        phase: 4,
      },
    ];
  }, [agentStates]);

  // Get latest cycle events for each phase
  const latestCycleId =
    timelineEvents.length > 0 ? timelineEvents[timelineEvents.length - 1].cycleId : 0;

  const eventsByPhase = useMemo(() => {
    const cycleEvents = timelineEvents.filter((e) => e.cycleId === latestCycleId);
    const groups: Record<number, TimelineEvent[]> = {};

    agents.forEach((agent) => {
      groups[agent.phase] = cycleEvents.filter((e) => e.phaseId === agent.phase);
    });

    return groups;
  }, [timelineEvents, latestCycleId, agents]);

  // Recent opportunities - Use real Synapse queue data
  const recentOpportunities = useMemo(() => {
    if (!queueData?.opportunities?.items) return [];

    return queueData.opportunities.items.map((item: any) => ({
      id: item.id,
      ticker: item.ticker,
      title: item.title,
      subtitle: item.subtitle,
      yes_price: item.yes_price,
      no_price: item.no_price,
      volume: item.volume,
      expiration: item.expiration,
      timestamp: item.timestamp,
    }));
  }, [queueData]);

  const recentExecutions = useMemo(() => {
    if (!queueData?.executions?.items) return [];

    return queueData.executions.items.map((item: any) => ({
      id: item.id,
      ticker: item.ticker,
      title: item.title,
      action: item.action,
      side: item.side,
      confidence: item.confidence,
      suggested_count: item.suggested_count,
      reasoning: item.reasoning,
      timestamp: item.timestamp,
    }));
  }, [queueData]);

  const toggleAgent = (id: number) => {
    setExpandedAgents((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <Card className="glass-panel rounded-4xl p-6 shadow-xl border border-white/10 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="relative">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-blue-500/30 flex items-center justify-center">
              <span className="text-lg">🚛</span>
            </div>
            {isProcessing && (
              <div className="absolute -inset-1 bg-blue-500/20 rounded-xl animate-pulse" />
            )}
          </div>
          <div>
            <h3 className="text-lg font-tech font-bold text-white uppercase tracking-wider">
              Logistics Center
            </h3>
            <p className="text-[10px] text-gray-500 font-mono">Neural Trace + Agent Pipeline</p>
          </div>
        </div>

        {/* Flow Metrics */}
        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 bg-white/5 rounded-lg border border-white/10">
            <div className="text-[9px] text-gray-500 uppercase tracking-wider font-mono">Cycle</div>
            <div className="text-sm font-bold text-white">#{flowMetrics.activeCycle}</div>
          </div>
          <div className="px-3 py-1.5 bg-white/5 rounded-lg border border-white/10">
            <div className="text-[9px] text-gray-500 uppercase tracking-wider font-mono">
              Pending
            </div>
            <div className="text-sm font-bold text-blue-400">{recentOpportunities.length}</div>
          </div>
          {queueData?.flowControl?.execution_queue_at_limit && (
            <div className="px-3 py-1.5 bg-red-500/20 rounded-lg border border-red-500/50 animate-pulse">
              <div className="text-[9px] text-red-400 uppercase tracking-wider font-mono">
                Flow Control
              </div>
              <div className="text-sm font-bold text-red-300">PAUSED</div>
            </div>
          )}
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-12 gap-4">
        {/* Agent Pipeline with Neural Trace (Left) */}
        <div className="col-span-12 lg:col-span-5 space-y-2">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider font-mono mb-3 flex items-center gap-2">
            <span>Agent Pipeline</span>
            <span className="text-gray-600">•</span>
            <span className="text-gray-600">Click to expand Neural Trace</span>
          </div>

          {agents.map((agent, idx) => {
            const isActive = agent.state?.status === 'active';
            const isNext = activeTransitions.some((t) => t.toAgent === agent.id && t.active);
            const events = eventsByPhase[agent.phase] || [];

            return (
              <div key={agent.id} className="relative">
                <AgentPipelineCard
                  {...agent}
                  isActive={isActive}
                  isNext={isNext}
                  events={events}
                  isExpanded={!!expandedAgents[agent.id]}
                  onToggle={() => toggleAgent(agent.id)}
                />

                {/* Flow Line */}
                {idx < agents.length - 1 && (
                  <div className="absolute left-1/2 -bottom-2 transform -translate-x-1/2 z-10">
                    <div
                      className={`w-0.5 h-2 ${isNext || isActive ? 'bg-gradient-to-b from-blue-400 to-purple-400' : 'bg-gray-700'}`}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Flow Visualization (Center) */}
        <div className="col-span-12 lg:col-span-4 flex flex-col gap-4">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider font-mono">
            Queue Status
          </div>

          {/* Opportunities In */}
          <div className="flex-1 bg-gradient-to-br from-green-500/5 to-transparent rounded-xl p-4 border border-green-500/20">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-green-400">↓</span>
                <span className="text-xs font-bold text-green-400">Opportunities In</span>
              </div>
              <div className="px-2 py-0.5 bg-green-500/20 rounded text-[10px] font-bold text-green-300 border border-green-500/30">
                {flowMetrics.totalOpportunities}
              </div>
            </div>

            <div className="space-y-1.5 max-h-32 overflow-y-auto no-scrollbar">
              {recentOpportunities.length === 0 ? (
                <div className="text-[10px] text-gray-600 font-mono py-2 text-center">
                  Awaiting market data...
                </div>
              ) : (
                recentOpportunities.map((opp) => (
                  <div
                    key={opp.id}
                    className="p-2 bg-white/5 rounded-lg border border-white/5 hover:bg-white/10 transition-colors"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <div className="w-1 h-1 bg-green-400 rounded-full shrink-0" />
                      <span className="text-[10px] text-green-300 font-mono font-bold">
                        {opp.ticker}
                      </span>
                    </div>
                    <div className="text-[9px] text-gray-400 line-clamp-2 mb-1.5">{opp.title}</div>
                    <div className="flex items-center gap-3 text-[9px] font-mono">
                      <div className="flex items-center gap-1">
                        <span className="text-green-400">YES</span>
                        <span className="text-gray-300">{opp.yes_price}¢</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <span className="text-red-400">NO</span>
                        <span className="text-gray-300">{opp.no_price}¢</span>
                      </div>
                      <div className="text-gray-500">Vol: {opp.volume.toLocaleString()}</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Executions Out */}
          <div
            className={`flex-1 rounded-xl p-4 border transition-all ${
              queueData?.flowControl?.execution_queue_at_limit
                ? 'bg-gradient-to-br from-red-500/10 to-transparent border-red-500/30'
                : 'bg-gradient-to-br from-orange-500/5 to-transparent border-orange-500/20'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span
                  className={
                    queueData?.flowControl?.execution_queue_at_limit
                      ? 'text-red-400'
                      : 'text-orange-400'
                  }
                >
                  ↑
                </span>
                <span
                  className={`text-xs font-bold ${
                    queueData?.flowControl?.execution_queue_at_limit
                      ? 'text-red-400'
                      : 'text-orange-400'
                  }`}
                >
                  Executions Out
                </span>
              </div>
              <div
                className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                  queueData?.flowControl?.execution_queue_at_limit
                    ? 'bg-red-500/30 text-red-300 border-red-500/50'
                    : 'bg-orange-500/20 text-orange-300 border-orange-500/30'
                }`}
              >
                {flowMetrics.totalExecutions}/10
              </div>
            </div>

            <div className="space-y-1.5 max-h-32 overflow-y-auto no-scrollbar">
              {recentExecutions.length === 0 ? (
                <div className="text-[10px] text-gray-600 font-mono py-2 text-center">
                  No trades yet...
                </div>
              ) : (
                recentExecutions.map((exec) => (
                  <div
                    key={exec.id}
                    className="p-2 bg-white/5 rounded-lg border border-white/5 hover:bg-white/10 transition-colors"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <div className="w-1 h-1 bg-orange-400 rounded-full shrink-0" />
                      <span className="text-[10px] text-orange-300 font-mono font-bold">
                        {exec.ticker}
                      </span>
                      <span
                        className={`px-1.5 py-0.5 rounded text-[8px] font-bold ${
                          exec.side === 'YES'
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-red-500/20 text-red-400'
                        }`}
                      >
                        {exec.side}
                      </span>
                    </div>
                    <div className="text-[9px] text-gray-400 line-clamp-2 mb-1.5">{exec.title}</div>
                    <div className="flex items-center gap-3 text-[9px] font-mono">
                      <div className="flex items-center gap-1">
                        <span className="text-blue-400">{Math.round(exec.confidence * 100)}%</span>
                        <span className="text-gray-500">conf</span>
                      </div>
                      <div className="text-gray-500">Qty: {exec.suggested_count}</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Synapse Stats (Right) */}
        <div className="col-span-12 lg:col-span-3 flex flex-col gap-3">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider font-mono">
            System Stats
          </div>

          <div className="bg-white/5 rounded-xl p-4 border border-white/10 flex-1">
            <div className="space-y-4">
              {/* Cycle Count */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] text-gray-400 font-mono">Total Cycles</span>
                  <span className="text-xs font-bold text-blue-400">#{cycleCount}</span>
                </div>
                <div className="text-[8px] text-gray-600">Trading cycles completed</div>
              </div>

              {/* Total Trades */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] text-gray-400 font-mono">Total Trades</span>
                  <span className="text-xs font-bold text-orange-400">
                    {flowMetrics.totalExecutions}
                  </span>
                </div>
                <div className="text-[8px] text-gray-600">Executed trades</div>
              </div>

              {/* Success Rate */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] text-gray-400 font-mono">Conversion Rate</span>
                  <span className="text-xs font-bold text-emerald-400">
                    {flowMetrics.totalOpportunities > 0
                      ? Math.round(
                          (flowMetrics.totalExecutions / flowMetrics.totalOpportunities) * 100
                        )
                      : 0}
                    %
                  </span>
                </div>
                <div className="text-[8px] text-gray-600">Executions / Opportunities</div>
                <div className="h-1.5 bg-white/10 rounded-full overflow-hidden mt-1">
                  <div
                    className="h-full bg-gradient-to-r from-emerald-500 to-green-400 rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.min(
                        flowMetrics.totalOpportunities > 0
                          ? (flowMetrics.totalExecutions / flowMetrics.totalOpportunities) * 100
                          : 0,
                        100
                      )}%`,
                    }}
                  />
                </div>
              </div>

              {/* Active Agents */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] text-gray-400 font-mono">Active Agents</span>
                  <span className="text-xs font-bold text-purple-400">
                    {agents.filter((a) => a.state?.status === 'active').length}/4
                  </span>
                </div>
                <div className="text-[8px] text-gray-600">Currently processing</div>
              </div>
            </div>

            {/* Current Phase Indicator */}
            <div className="mt-4 pt-4 border-t border-white/10">
              <div className="text-[10px] text-gray-400 font-mono mb-2">Current Phase</div>
              <div className="space-y-1.5">
                {agents.map((agent) => {
                  const isActive = agent.state?.status === 'active';
                  return (
                    <div
                      key={agent.id}
                      className={`flex items-center gap-2 p-2 rounded-lg border transition-all ${
                        isActive ? 'bg-white/10 border-white/20' : 'bg-white/5 border-white/5'
                      }`}
                    >
                      <div
                        className={`w-1.5 h-1.5 rounded-full ${
                          isActive ? 'bg-emerald-400 animate-pulse' : 'bg-gray-600'
                        }`}
                      />
                      <span
                        className={`text-[10px] font-mono ${isActive ? 'text-white' : 'text-gray-600'}`}
                      >
                        {isActive ? `→ ${agent.name}` : agent.name}
                      </span>
                    </div>
                  );
                })}
              </div>
              {isProcessing && (
                <div className="mt-3 text-[9px] text-emerald-400 font-mono flex items-center gap-1.5">
                  <div className="w-1 h-1 bg-emerald-400 rounded-full animate-pulse" />
                  Cycle in progress...
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
};

export default LogisticsCenter;
