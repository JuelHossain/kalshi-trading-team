import React, { useEffect, useMemo, useState } from 'react';
import { LogEntry } from '@shared/types';
import { PHASES, PHASE_ORDER, INTERVENTION_PHASE, PhaseConfig } from '@shared/constants';

interface TerminalProps {
    logs: LogEntry[];
}

const getPhaseConfig = (phaseId: number): PhaseConfig => {
    if (phaseId === 13) return INTERVENTION_PHASE;
    return PHASES[phaseId] || PHASES[0];
};

const PhaseBlock: React.FC<{
    phaseId: number;
    logs: LogEntry[];
    isLast: boolean;
    isActiveCycle: boolean;
}> = ({ phaseId, logs, isLast, isActiveCycle }) => {
    const config = getPhaseConfig(phaseId);

    // Determine status based on logs
    const hasError = logs.some(l => l.level === 'ERROR');
    const isWorking = isActiveCycle && isLast && !hasError;

    return (
        <div className="relative pl-6 pb-6 last:pb-0">
            {/* Timeline Line */}
            {!isLast && (
                <div className="absolute left-[11px] top-6 bottom-0 w-[2px] bg-white/5"></div>
            )}

            {/* Node Icon */}
            <div className={`absolute left-0 top-0 w-6 h-6 rounded-full border ${config.borderColor} ${config.bg} flex items-center justify-center z-10 shadow-[0_0_10px_rgba(0,0,0,0.5)]`}>
                <span className={`text-[10px] ${config.color} ${isWorking ? 'animate-pulse' : ''}`}>{config.icon}</span>
            </div>

            {/* Content Card */}
            <div className={`ml-4 rounded-xl border ${config.borderColor} ${config.bg} overflow-hidden backdrop-blur-sm transition-all duration-300`}>
                <div className="px-3 py-2 border-b border-white/5 flex justify-between items-center bg-black/20">
                    <div>
                        <span className={`text-[10px] font-bold font-tech tracking-widest uppercase ${config.color}`}>
                            {config.title}
                        </span>
                        <span className="text-[9px] text-gray-500 font-mono ml-2 uppercase tracking-wide">
                            {config.subtitle}
                        </span>
                    </div>
                    {isWorking && (
                        <div className="flex gap-1">
                            <span className="w-1 h-1 bg-white rounded-full animate-bounce"></span>
                            <span className="w-1 h-1 bg-white rounded-full animate-bounce [animation-delay:0.1s]"></span>
                            <span className="w-1 h-1 bg-white rounded-full animate-bounce [animation-delay:0.2s]"></span>
                        </div>
                    )}
                </div>

                <div className="p-2 space-y-1.5">
                    {logs.map(log => (
                        <div key={log.id} className="flex gap-2 text-[10px] font-mono group">
                            <span className="text-gray-600 shrink-0 opacity-50 select-none w-12 text-right">
                                {log.timestamp.split('.')[0]}
                            </span>
                            <div className="break-words leading-relaxed text-gray-300 group-hover:text-white transition-colors">
                                {hasError && log.level === 'ERROR' ? (
                                    <span className="text-red-500 font-bold mr-1">FAIL »</span>
                                ) : (
                                    <span className={`mr-1 opacity-50 ${config.color}`}>›</span>
                                )}
                                {log.message.replace(/^Agent \d+: /, '')}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

const CycleProgressIndicator: React.FC<{
    completedPhases: Set<number>;
    currentPhase: number;
    hasError: boolean;
    isComplete: boolean;
}> = ({ completedPhases, currentPhase, hasError, isComplete }) => {
    const progress = (completedPhases.size / PHASE_ORDER.length) * 100;

    return (
        <div className="mb-4 p-3 rounded-xl bg-black/40 border border-white/5">
            {/* Progress Bar */}
            <div className="mb-3">
                <div className="flex justify-between items-center mb-1.5">
                    <span className="text-[9px] font-mono text-gray-500 uppercase tracking-wider">Cycle Progress</span>
                    <span className="text-[9px] font-mono text-emerald-400 font-bold">{Math.round(progress)}%</span>
                </div>
                <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                    <div
                        className={`h-full transition-all duration-500 ${hasError ? 'bg-red-500' : isComplete ? 'bg-emerald-500' : 'bg-blue-500'
                            }`}
                        style={{ width: `${progress}%` }}
                    ></div>
                </div>
            </div>

            {/* Phase Checklist */}
            <div className="grid grid-cols-2 gap-2">
                {PHASE_ORDER.map(phaseId => {
                    const config = PHASES[phaseId];
                    const isCompleted = completedPhases.has(phaseId);
                    const isCurrent = currentPhase === phaseId;
                    const isPending = !isCompleted && !isCurrent;

                    let statusIcon = '○';
                    let statusColor = 'text-gray-600';

                    if (isCompleted) {
                        statusIcon = '✓';
                        statusColor = 'text-emerald-500';
                    } else if (isCurrent) {
                        statusIcon = '⏳';
                        statusColor = 'text-blue-400 animate-pulse';
                    } else if (hasError && isCurrent) {
                        statusIcon = '✗';
                        statusColor = 'text-red-500';
                    }

                    return (
                        <div
                            key={phaseId}
                            className={`flex items-center gap-2 px-2 py-1 rounded-lg ${isCurrent ? 'bg-white/5 border border-white/10' : ''
                                }`}
                        >
                            <span className={`text-[10px] ${statusColor}`}>{statusIcon}</span>
                            <span className={`text-[9px] font-mono ${isCompleted ? 'text-gray-400' : isCurrent ? 'text-white' : 'text-gray-600'
                                }`}>
                                {config.subtitle}
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

const CycleGroup: React.FC<{
    cycleId: number;
    logs: LogEntry[];
    isExpanded: boolean;
    toggle: () => void;
    isLatest: boolean;
}> = ({ cycleId, logs, isExpanded, toggle, isLatest }) => {

    const hasError = logs.some(l => l.level === 'ERROR');
    const isComplete = logs.some(l => l.message.includes('CYCLE') && l.message.includes('COMPLETE'));

    const targetLog = logs.find(l => l.message.includes('TARGET LOCK') || l.message.includes('Target:'));
    const targetName = targetLog
        ? targetLog.message.split(':').pop()?.replace('(', '').replace(')', '').trim()
        : logs.find(l => l.message.includes('Scanning')) ? 'SCANNING...' : 'SYSTEM IDLE';

    const statusColor = isLatest && !isComplete && !hasError ? 'text-blue-400'
        : hasError ? 'text-red-400'
            : isComplete ? 'text-emerald-400'
                : 'text-gray-400';

    const borderColor = isLatest && !isComplete && !hasError ? 'border-blue-500/30'
        : hasError ? 'border-red-500/30'
            : isComplete ? 'border-emerald-500/30'
                : 'border-white/5';

    // Group logs by Phase
    const phaseGroups = useMemo(() => {
        const groups: { phaseId: number, logs: LogEntry[] }[] = [];
        let currentPhaseId = -1;

        logs.forEach(log => {
            const pId = log.phaseId;
            if (pId !== currentPhaseId) {
                groups.push({ phaseId: pId, logs: [log] });
                currentPhaseId = pId;
            } else {
                groups[groups.length - 1].logs.push(log);
            }
        });
        return groups;
    }, [logs]);

    // Calculate completed phases and current phase
    const completedPhases = useMemo(() => {
        const phases = new Set<number>();
        let maxPhase = 0;

        logs.forEach(log => {
            if (log.phaseId > maxPhase) maxPhase = log.phaseId;
        });

        // Mark all phases before the current one as complete
        PHASE_ORDER.forEach(phaseId => {
            if (phaseId < maxPhase) {
                phases.add(phaseId);
            }
        });

        // If cycle is complete, mark all phases as complete
        if (isComplete) {
            PHASE_ORDER.forEach(phaseId => phases.add(phaseId));
        }

        return phases;
    }, [logs, isComplete]);

    const currentPhase = useMemo(() => {
        let maxPhase = 0;
        logs.forEach(log => {
            if (log.phaseId > maxPhase) maxPhase = log.phaseId;
        });
        return maxPhase;
    }, [logs]);

    return (
        <div className={`mb-4 rounded-2xl border ${borderColor} overflow-hidden transition-all duration-300 ${isExpanded ? 'bg-black/40 shadow-xl' : 'bg-white/[0.02]'}`}>
            {/* Cycle Header */}
            <div
                onClick={toggle}
                className={`flex items-center justify-between p-4 cursor-pointer hover:bg-white/5 transition-colors`}
            >
                <div className="flex items-center gap-4">
                    <div className={`flex flex-col items-center justify-center w-10 h-10 rounded-xl border ${borderColor} bg-black/40 shadow-inner`}>
                        <span className="text-[8px] uppercase text-gray-500 font-mono leading-none mb-0.5">CYC</span>
                        <span className={`text-sm font-bold font-mono ${statusColor}`}>{cycleId === 0 ? 'SYS' : cycleId}</span>
                    </div>

                    <div className="flex flex-col">
                        <span className="text-[9px] text-gray-500 font-mono uppercase tracking-widest mb-0.5">
                            {logs[0]?.timestamp.split('.')[0] || '--:--:--'}
                        </span>
                        <span className={`text-sm font-bold truncate ${statusColor} font-tech tracking-wider uppercase`}>
                            {targetName}
                        </span>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    {isLatest && !isComplete && !hasError && (
                        <div className="px-2 py-0.5 bg-blue-500/10 border border-blue-500/20 rounded text-[9px] text-blue-400 font-mono animate-pulse">
                            RUNNING
                        </div>
                    )}
                    {isComplete && (
                        <div className="px-2 py-0.5 bg-emerald-500/10 border border-emerald-500/20 rounded text-[9px] text-emerald-400 font-mono">
                            COMPLETE
                        </div>
                    )}
                    <div className={`text-xs text-gray-500 transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}>
                        ▼
                    </div>
                </div>
            </div>

            {/* Expanded Phase View */}
            {isExpanded && (
                <div className="p-4 pt-2 border-t border-white/5 animate-[fadeIn_0.3s_ease-out]">
                    {/* Cycle Progress Indicator */}
                    <CycleProgressIndicator
                        completedPhases={completedPhases}
                        currentPhase={currentPhase}
                        hasError={hasError}
                        isComplete={isComplete}
                    />

                    {/* Phase Timeline */}
                    <div className="relative">
                        {phaseGroups.map((group, idx) => (
                            <PhaseBlock
                                key={idx}
                                phaseId={group.phaseId}
                                logs={group.logs}
                                isLast={idx === phaseGroups.length - 1}
                                isActiveCycle={isLatest && !isComplete && !hasError}
                            />
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

const Terminal: React.FC<TerminalProps> = ({ logs }) => {
    const [expandedCycles, setExpandedCycles] = useState<Record<number, boolean>>({});

    const groupedLogs = useMemo(() => {
        const groups: Record<number, LogEntry[]> = {};
        logs.forEach(log => {
            const cid = log.cycleId ?? 0;
            if (!groups[cid]) groups[cid] = [];
            groups[cid].push(log);
        });

        return Object.keys(groups)
            .map(Number)
            .sort((a, b) => b - a)
            .map(cid => ({
                id: cid,
                logs: groups[cid]
            }));
    }, [logs]);

    const newestCycleId = groupedLogs.length > 0 ? groupedLogs[0].id : null;

    useEffect(() => {
        if (newestCycleId !== null) {
            setExpandedCycles({ [newestCycleId]: true });
        }
    }, [newestCycleId]);

    const toggleCycle = (id: number) => {
        setExpandedCycles(prev => ({
            ...prev,
            [id]: !prev[id]
        }));
    };

    return (
        <div className="h-full max-h-full relative glass-panel rounded-3xl overflow-hidden flex flex-col border border-white/5 shadow-2xl">
            <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/5 blur-[80px] rounded-full pointer-events-none"></div>

            <div className="flex justify-between items-center px-5 py-4 border-b border-white/5 bg-black/20 backdrop-blur-xl shrink-0 z-10">
                <div className="flex items-center gap-3">
                    <div className="flex gap-1.5">
                        <div className="w-2.5 h-2.5 rounded-full bg-red-500/20 border border-red-500/50"></div>
                        <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/20 border border-yellow-500/50"></div>
                        <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/20 border border-emerald-500/50"></div>
                    </div>
                    <h3 className="text-gray-400 font-mono text-xs uppercase tracking-widest ml-2">
                        Neural_Trace_v3.0 [CYCLE-BASED]
                    </h3>
                </div>
                <div className="px-2 py-1 rounded-full bg-emerald-900/20 border border-emerald-500/20">
                    <span className="text-[10px] text-emerald-400 font-mono flex items-center gap-2">
                        <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></span>
                        LIVE STREAM
                    </span>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto min-h-0 p-4 scroll-smooth no-scrollbar relative z-0">
                <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.03),rgba(0,255,0,0.01),rgba(0,0,255,0.03))] bg-[size:100%_3px,3px_100%] opacity-20"></div>

                {logs.length === 0 && (
                    <div className="text-gray-600 italic opacity-50 text-center mt-20 font-mono text-xs">
                        Initializing Neural Link...
                    </div>
                )}

                <div className="relative z-10 pb-4">
                    {groupedLogs.map((group, index) => (
                        <CycleGroup
                            key={group.id}
                            cycleId={group.id}
                            logs={group.logs}
                            isExpanded={!!expandedCycles[group.id]}
                            toggle={() => toggleCycle(group.id)}
                            isLatest={index === 0}
                        />
                    ))}
                </div>
            </div>
        </div>
    );
};

export default Terminal;