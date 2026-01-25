import React, { useEffect, useMemo, useState } from 'react';
import {
  LogEntry,
  TimelineEvent,
  SimulationState,
  VaultState,
} from '@shared/types';
import { PHASES, PHASE_ORDER, INTERVENTION_PHASE, PhaseConfig } from '@shared/constants';

interface TerminalProps {
  timelineEvents: TimelineEvent[];
  activeAgentId?: number | null;
}

const getPhaseConfig = (phaseId: number): PhaseConfig => {
  if (phaseId === 13) return INTERVENTION_PHASE;
  return PHASES[phaseId] || PHASES[0];
};

// --- DATA CARD COMPONENTS ---

const VaultCard: React.FC<{ data: VaultState }> = ({ data }) => (
  <div className="bg-emerald-900/10 border border-emerald-500/20 rounded-lg p-3 my-2 flex justify-between items-center backdrop-blur-sm animate-scale-in">
    <div className="flex flex-col">
      <span className="text-[9px] text-emerald-400 uppercase tracking-widest font-mono">
        Vault Balance
      </span>
      <span className="text-lg font-bold font-tech text-white">
        ${((data.total ?? 0) / 100).toFixed(2)}
      </span>
    </div>
    <div className="flex flex-col items-end">
      <span className="text-[9px] text-gray-400 uppercase tracking-widest font-mono">Profit</span>
      <span
        className={`text-sm font-bold font-mono ${data.currentProfit >= 0 ? 'text-emerald-400' : 'text-red-400'}`}
      >
        {(data.currentProfit ?? 0) >= 0 ? '+' : ''}${((data.currentProfit ?? 0) / 100).toFixed(2)}
      </span>
    </div>
  </div>
);

const SimulationCard: React.FC<{ data: SimulationState }> = ({ data }) => (
  <div className="bg-blue-900/10 border border-blue-500/20 rounded-lg p-3 my-2 backdrop-blur-sm animate-scale-in">
    <div className="flex justify-between items-center mb-2">
      <span className="text-[9px] text-blue-400 uppercase tracking-widest font-mono">
        Sim Results: {data.ticker}
      </span>
      <span
        className={`px-1.5 py-0.5 rounded text-[8px] font-bold uppercase ${data.veto ? 'bg-red-500/20 text-red-500' : 'bg-emerald-500/20 text-emerald-500'}`}
      >
        {data.veto ? 'VETOED' : 'APPROVED'}
      </span>
    </div>
    <div className="grid grid-cols-3 gap-2">
      <div className="bg-black/20 rounded p-1.5 text-center">
        <div className="text-[8px] text-gray-500 uppercase">Win Rate</div>
        <div className="text-sm font-bold text-white">
          {((data.winRate ?? 0) * 100).toFixed(1)}%
        </div>
      </div>
      <div className="bg-black/20 rounded p-1.5 text-center">
        <div className="text-[8px] text-gray-500 uppercase">EV Score</div>
        <div className="text-sm font-bold text-blue-300">{(data.evScore ?? 0).toFixed(2)}</div>
      </div>
      <div className="bg-black/20 rounded p-1.5 text-center">
        <div className="text-[8px] text-gray-500 uppercase">Variance</div>
        <div className="text-sm font-bold text-purple-300">{(data.variance ?? 0).toFixed(3)}</div>
      </div>
    </div>
  </div>
);

const LogLine: React.FC<{ log: LogEntry }> = ({ log }) => {
  // Terminal best practices: Color by log level
  const getLevelStyles = (level: string) => {
    switch (level) {
      case 'ERROR':
        return 'border-red-500 bg-red-500/10 text-red-400 font-semibold';
      case 'WARN':
      case 'WARNING':
        return 'border-yellow-500 bg-yellow-500/10 text-yellow-400';
      case 'INFO':
        return 'border-blue-500 bg-blue-500/5 text-blue-300';
      case 'DEBUG':
        return 'border-gray-500 bg-gray-500/5 text-gray-500';
      default:
        return 'border-transparent text-gray-400';
    }
  };

  const levelStyles = getLevelStyles(log.level);

  return (
    <div
      className={`flex gap-3 py-1 px-2 rounded hover:bg-white/5 transition-colors font-mono text-[10px] group border-l-2 ${levelStyles}`}
    >
      <span className="text-gray-600 w-12 shrink-0 opacity-50">
        {log.timestamp.split('T')[1]?.split('.')[0]}
      </span>
      <span className="break-words flex-1 group-hover:text-gray-200">
        {log.message.replace(/^Agent \d+: /, '')}
        {log.count > 1 && <span className="text-gray-500"> ({log.count}x)</span>}
      </span>
    </div>
  );
};

// --- ERROR & FIXER CARDS (Inline Agent 13) ---

const ErrorCard: React.FC<{ error: any }> = ({ error }) => (
  <div className="bg-red-900/20 border border-red-500/40 rounded-xl p-4 my-3 backdrop-blur-sm animate-shake relative overflow-hidden">
    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-red-500 via-red-400 to-red-500 animate-pulse"></div>
    <div className="flex items-start gap-3">
      <div className="w-10 h-10 rounded-lg bg-red-500/20 border border-red-500/40 flex items-center justify-center shrink-0">
        <span className="text-xl">⚠️</span>
      </div>
      <div className="flex-1">
        <div className="text-[10px] text-red-400 uppercase tracking-widest font-mono mb-1">
          System Error Detected
        </div>
        <div className="text-sm text-red-200 font-mono break-words">{error.message || error}</div>
      </div>
    </div>
  </div>
);

const FixerCard: React.FC<{ data: any }> = ({ data }) => {
  const actionColors: Record<string, string> = {
    ANALYZING: 'text-yellow-400 border-yellow-500/30 bg-yellow-900/10',
    ATTEMPTING_FIX: 'text-orange-400 border-orange-500/30 bg-orange-900/10',
    FIXED: 'text-emerald-400 border-emerald-500/30 bg-emerald-900/10',
    FAILED: 'text-red-400 border-red-500/30 bg-red-900/10',
  };
  const colorClass = actionColors[data.action] || actionColors['ANALYZING'];

  return (
    <div className={`border rounded-xl p-4 my-3 backdrop-blur-sm animate-scale-in ${colorClass}`}>
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-lg bg-black/30 border border-current flex items-center justify-center shrink-0 animate-pulse">
          <span className="text-xl">🔧</span>
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] uppercase tracking-widest font-mono">
              Agent 13 :: Fixer
            </span>
            <span className="px-1.5 py-0.5 rounded text-[8px] font-bold uppercase bg-black/30">
              {data.action}
            </span>
          </div>
          <div className="text-sm font-mono break-words opacity-90">{data.details}</div>
          {data.action === 'FAILED' && !data.canRecover && (
            <div className="mt-2 text-[10px] text-red-300 border-t border-red-500/20 pt-2">
              ⚠️ Manual intervention required. System paused.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// --- ACCORDION ITEM ---

const PhaseAccordionItem: React.FC<{
  phaseId: number;
  events: TimelineEvent[];
  isActive: boolean;
  isPending: boolean;
  isComplete: boolean;
  onToggle: () => void;
  expanded: boolean;
}> = ({ phaseId, events, isActive, _isPending, isComplete, onToggle, expanded }) => {
  const config = getPhaseConfig(phaseId);

  // Status visual logic
  let borderColor = 'border-white/5';
  let bgClass = 'bg-white/[0.02]';

  if (isActive) {
    borderColor = 'border-blue-500/30';
    bgClass = 'bg-blue-900/5';
  } else if (isComplete) {
    borderColor = 'border-emerald-500/20';
    bgClass = 'bg-emerald-900/5';
  }

  return (
    <div
      className={`mb-2 rounded-xl border ${borderColor} ${bgClass} overflow-hidden transition-all duration-300`}
    >
      {/* Header */}
      <div
        onClick={onToggle}
        className="flex items-center justify-between p-3 cursor-pointer hover:bg-white/5"
      >
        <div className="flex items-center gap-3">
          <div
            className={`w-8 h-8 rounded-lg flex items-center justify-center border ${isActive ? config.borderColor : 'border-transparent'} bg-black/20`}
          >
            <span className={`text-sm ${isActive ? config.color : 'text-gray-600'}`}>
              {config.icon}
            </span>
          </div>
          <div>
            <div
              className={`text-[10px] font-bold font-tech uppercase tracking-wider ${isActive ? 'text-white' : 'text-gray-400'}`}
            >
              {config.title}
            </div>
            <div className="text-[8px] text-gray-600 uppercase font-mono">
              {events.length} Events
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Mini Status Indicator */}
          {isActive && <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>}
          {isComplete && <div className="text-emerald-500 text-xs">✓</div>}
          <div
            className={`text-xs text-gray-600 transition-transform duration-300 ${expanded ? 'rotate-180' : ''}`}
          >
            ▼
          </div>
        </div>
      </div>

      {/* Expanded Content (Timeline) */}
      {expanded && (
        <div className="border-t border-white/5 bg-black/20 p-3 animate-slide-down">
          {events.map((event) => {
            if (event.type === 'LOG')
              return <LogLine key={event.id} log={event.data as LogEntry} />;
            if (event.type === 'SIMULATION')
              return <SimulationCard key={event.id} data={event.data as SimulationState} />;
            if (event.type === 'VAULT')
              return <VaultCard key={event.id} data={event.data as VaultState} />;
            if (event.type === 'ERROR') return <ErrorCard key={event.id} error={event.data} />;
            if (event.type === 'FIXER') return <FixerCard key={event.id} data={event.data} />;
            return null;
          })}
          {isActive && (
            <div className="pl-14 pt-2 pb-1">
              <span className="inline-block w-1.5 h-3 bg-blue-500/50 animate-pulse"></span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// --- MAIN TERMINAL ---

const Terminal: React.FC<TerminalProps> = ({ timelineEvents }) => {
  // Group events by Cycle -> Phase
  // Only show the LATEST cycle
  const latestCycleId =
    timelineEvents.length > 0 ? timelineEvents[timelineEvents.length - 1].cycleId : 0;

  // Filter events for this cycle
  const cycleEvents = timelineEvents.filter((e) => e.cycleId === latestCycleId);

  // Determine current active phase
  const lastEvent = cycleEvents[cycleEvents.length - 1];
  const currentPhaseId = lastEvent?.phaseId || 0;

  // Compress consecutive identical logs
  const compressLogs = (events: TimelineEvent[]) => {
    const compressed = [];
    let lastLog = null;
    for (const event of events) {
      if (event.type === 'LOG') {
        const log = event.data as LogEntry;
        if (lastLog && lastLog.message === log.message && lastLog.level === log.level) {
          lastLog.count = (lastLog.count || 1) + 1;
          lastLog.timestamp = log.timestamp;
        } else {
          if (lastLog) compressed.push(lastLog.event);
          lastLog = {
            message: log.message,
            level: log.level,
            timestamp: log.timestamp,
            count: 1,
            event,
          };
        }
      } else {
        if (lastLog) {
          compressed.push(lastLog.event);
          lastLog = null;
        }
        compressed.push(event);
      }
    }
    if (lastLog) compressed.push(lastLog.event);
    return compressed;
  };

  // Group into phases
  const eventsByPhase = useMemo(() => {
    const groups: Record<number, TimelineEvent[]> = {};
    PHASE_ORDER.forEach((id) => (groups[id] = []));

    cycleEvents.forEach((e) => {
      if (!groups[e.phaseId]) groups[e.phaseId] = [];
      groups[e.phaseId].push(e);
    });

    // Compress logs in each phase
    for (const phaseId in groups) {
      groups[phaseId] = compressLogs(groups[phaseId]);
    }

    return groups;
  }, [cycleEvents]);

  // Auto-expand logic: By default, expand the ACTIVE phase
  const [expandedPhases, setExpandedPhases] = useState<Record<number, boolean>>({});

  // Effect to auto-expand new phases as we enter them
  useEffect(() => {
    setExpandedPhases((prev) => ({
      ...prev,
      [currentPhaseId]: true,
    }));
  }, [currentPhaseId]);

  const togglePhase = (id: number) => {
    setExpandedPhases((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="h-full max-h-full flex flex-col relative glass-panel rounded-3xl overflow-hidden shadow-2xl border border-white/10">
      {/* Header */}
      <div className="shrink-0 h-14 border-b border-white/5 bg-black/40 backdrop-blur-md flex justify-between items-center px-6">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_10px_#10b981]"></div>
          <div>
            <div className="text-[10px] font-mono font-bold text-gray-300 uppercase tracking-[0.2em] opacity-80">
              NEURAL_TRACE_V5 // CYCLE {latestCycleId}
            </div>
            <div className="text-[8px] text-gray-500 font-mono uppercase tracking-wider">
              Real-time Event Stream
            </div>
          </div>
        </div>
      </div>

      {/* Accordion List */}
      <div className="flex-1 overflow-y-auto p-4 scroll-smooth no-scrollbar">
        {PHASE_ORDER.map((phaseId) => {
          const isActive = phaseId === currentPhaseId;
          // Phase is complete if we are past it in the sequence OR if cycle is done
          const isComplete =
            phaseId < currentPhaseId ||
            cycleEvents.some(
              (e) => e.data?.message?.includes('CYCLE') && e.data?.message?.includes('COMPLETE')
            );

          return (
            <PhaseAccordionItem
              key={phaseId}
              phaseId={phaseId}
              events={eventsByPhase[phaseId] || []}
              isActive={isActive}
              isPending={!isActive && !isComplete}
              isComplete={isComplete}
              expanded={!!expandedPhases[phaseId]}
              onToggle={() => togglePhase(phaseId)}
            />
          );
        })}

        {cycleEvents.length === 0 && (
          <div className="text-center mt-20 text-gray-600 font-mono text-xs animate-pulse">
            Waiting for Cycle Initiation...
          </div>
        )}
      </div>
    </div>
  );
};

export default Terminal;
