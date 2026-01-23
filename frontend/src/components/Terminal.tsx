import React, { useEffect, useMemo, useState, useRef } from 'react';
import { LogEntry } from '@shared/types';
import { PHASES, PHASE_ORDER, INTERVENTION_PHASE, PhaseConfig } from '@shared/constants';

interface TerminalProps {
    logs: LogEntry[];
    activeAgentId?: number | null;
}

const getPhaseConfig = (phaseId: number): PhaseConfig => {
    if (phaseId === 13) return INTERVENTION_PHASE;
    return PHASES[phaseId] || PHASES[0];
};

// --- SUB-COMPONENTS ---

const TypewriterLog: React.FC<{ message: string, className?: string }> = ({ message, className }) => {
    const [displayed, setDisplayed] = useState('');

    useEffect(() => {
        setDisplayed(message);
    }, [message]);

    return (
        <div className={`font-mono text-sm leading-relaxed break-words ${className}`}>
            {displayed}
            <span className="inline-block w-2 h-4 bg-emerald-500 ml-1 animate-pulse align-middle"></span>
        </div>
    );
};

const PhaseHero: React.FC<{
    currentPhaseId: number,
    latestLog?: LogEntry,
    isComplete: boolean
}> = ({ currentPhaseId, latestLog, isComplete }) => {
    const config = getPhaseConfig(currentPhaseId);

    return (
        <div className={`relative w-full p-6 mb-6 rounded-2xl overflow-hidden border border-white/10 transition-all duration-500 ${isComplete ? 'bg-emerald-900/10' : 'bg-black/40'}`}>
            {/* Background Glow */}
            <div className={`absolute top-0 right-0 w-64 h-64 blur-[100px] rounded-full opacity-20 pointer-events-none ${isComplete ? 'bg-emerald-500' : 'bg-blue-500'}`}></div>

            <div className="relative z-10 flex flex-col gap-4">
                {/* Header */}
                <div className="flex justify-between items-start">
                    <div className="flex items-center gap-4">
                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center border ${config.borderColor} ${config.bg} shadow-lg`}>
                            <span className={`text-xl ${config.color}`}>{config.icon}</span>
                        </div>
                        <div>
                            <div className="text-[10px] text-gray-500 uppercase tracking-[0.2em] font-mono mb-1">Current Protocol</div>
                            <div className={`text-2xl font-bold font-tech uppercase tracking-widest ${config.color}`}>
                                {config.title}
                            </div>
                            <div className="text-xs text-gray-400 font-mono uppercase tracking-wider opacity-70">
                                {config.subtitle}
                            </div>
                        </div>
                    </div>

                    {/* Status Badge */}
                    <div className={`px-3 py-1.5 rounded-lg border ${isComplete ? 'border-emerald-500/30 bg-emerald-500/10' : 'border-blue-500/30 bg-blue-500/10'}`}>
                        <span className={`text-[10px] font-bold font-mono uppercase animate-pulse ${isComplete ? 'text-emerald-400' : 'text-blue-400'}`}>
                            {isComplete ? 'PHASE COMPLETE' : 'PROCESSING...'}
                        </span>
                    </div>
                </div>

                {/* Console Output Area */}
                <div className="mt-4 p-4 rounded-xl bg-black/60 border border-white/5 min-h-[80px] relative font-mono text-xs">
                    <div className="absolute top-2 right-2 text-[8px] text-gray-600 uppercase">System Output</div>
                    {latestLog ? (
                        <TypewriterLog
                            message={latestLog.message.replace(/^Agent \d+: /, '')}
                            className={latestLog.level === 'ERROR' ? 'text-red-400' : 'text-emerald-100'}
                        />
                    ) : (
                        <span className="text-gray-600 italic">Waiting for signal...</span>
                    )}
                </div>
            </div>

            {/* Progress Line */}
            <div className="absolute bottom-0 left-0 h-1 bg-white/5 w-full">
                <div
                    className={`h-full transition-all duration-300 ${isComplete ? 'bg-emerald-500 w-full' : 'bg-blue-500 w-1/3 animate-pulse'}`}
                ></div>
            </div>
        </div>
    );
};

// --- SIMPLIFIED HISTORY ROW ---
const HistoryLog: React.FC<{ log: LogEntry }> = ({ log }) => {
    const isError = log.level === 'ERROR';
    return (
        <div className={`flex gap-3 py-1.5 px-2 rounded hover:bg-white/5 transition-colors font-mono text-[10px] group border-l-2 ${isError ? 'border-red-500 bg-red-500/5' : 'border-transparent'}`}>
            <span className="text-gray-600 w-14 shrink-0 opacity-50">{log.timestamp.split('T')[1]?.split('.')[0]}</span>
            <span className={`${isError ? 'text-red-400' : 'text-gray-400 group-hover:text-gray-200'}`}>
                {log.message}
            </span>
        </div>
    );
};

const CycleHistory: React.FC<{ cycleId: number, logs: LogEntry[] }> = ({ cycleId, logs }) => {
    const [isOpen, setIsOpen] = useState(false);
    const hasError = logs.some(l => l.level === 'ERROR');

    return (
        <div className="border border-white/5 rounded-xl bg-white/[0.02] overflow-hidden mb-2">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center justify-between p-3 hover:bg-white/5 transition-colors"
            >
                <div className="flex items-center gap-3">
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${hasError ? 'bg-red-500/20 text-red-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
                        CYCLE #{cycleId}
                    </span>
                    <span className="text-[10px] text-gray-500 font-mono">
                        {logs.length} events
                    </span>
                </div>
                <span className={`text-xs text-gray-600 transition-transform ${isOpen ? 'rotate-180' : ''}`}>▼</span>
            </button>

            {isOpen && (
                <div className="p-3 pt-0 border-t border-white/5 bg-black/20">
                    {logs.map(log => <HistoryLog key={log.id} log={log} />)}
                </div>
            )}
        </div>
    );
};


// --- MAIN TERMINAL ---

const Terminal: React.FC<TerminalProps> = ({ logs, activeAgentId }) => {
    const bottomRef = useRef<HTMLDivElement>(null);

    // Filter relevant logs for display
    const currentCycleId = logs.length > 0 ? logs[logs.length - 1].cycleId : 0;
    const currentLogs = logs.filter(l => l.cycleId === currentCycleId);

    // Find latest "Action"
    const latestLog = currentLogs[currentLogs.length - 1];

    // Determine active phase from latest log
    const currentPhaseId = latestLog?.phaseId || 0;

    // Detect cycle completion
    const isCycleComplete = latestLog?.message.includes('COMPLETE') || false;

    // Auto-scroll effect for the stream
    useEffect(() => {
        if (bottomRef.current) {
            bottomRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [logs.length]);

    // Group past cycles
    const pastCycles = useMemo(() => {
        const groups: Record<number, LogEntry[]> = {};
        logs.forEach(l => {
            if (l.cycleId !== currentCycleId) {
                if (!groups[l.cycleId]) groups[l.cycleId] = [];
                groups[l.cycleId].push(l);
            }
        });
        return Object.entries(groups).sort((a, b) => Number(b[0]) - Number(a[0]));
    }, [logs, currentCycleId]);

    return (
        <div className="h-full max-h-full flex flex-col relative glass-panel rounded-3xl overflow-hidden shadow-2xl border border-white/10">
            {/* Header */}
            <div className="shrink-0 h-12 border-b border-white/5 bg-black/40 backdrop-blur-md flex justify-between items-center px-6">
                <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_10px_#10b981]"></div>
                    <span className="text-[10px] font-mono font-bold text-gray-300 uppercase tracking-[0.2em] opacity-80">
                        NEURAL_UPLINK_V4.0 // LIVE
                    </span>
                </div>
                <div className="text-[10px] font-mono text-emerald-500/50">
                    FREQ: 4Hz [BUFFERED]
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 overflow-y-auto p-6 scroll-smooth">
                {/* 1. HERO: Active Process */}
                {logs.length > 0 && (
                    <PhaseHero
                        currentPhaseId={currentPhaseId}
                        latestLog={latestLog}
                        isComplete={isCycleComplete}
                    />
                )}

                {/* 2. LOG STREAM (Current Cycle) */}
                <div className="mb-8">
                    <div className="text-[10px] text-gray-500 font-mono uppercase tracking-widest mb-3 pl-1">Target Sequence Stream</div>
                    <div className="space-y-1 relative">
                        {/* Connecting Line */}
                        <div className="absolute left-[11px] top-0 bottom-0 w-[1px] bg-white/5"></div>

                        {currentLogs.slice(-8).map(log => ( // Show last 8 only to keep it clean, unless scrolled
                            <div key={log.id} className="relative pl-6 animate-slide-in-right">
                                <div className={`absolute left-2 top-2.5 w-1.5 h-1.5 rounded-full ${log.level === 'ERROR' ? 'bg-red-500' : 'bg-emerald-500/30'}`}></div>
                                <HistoryLog log={log} />
                            </div>
                        ))}
                        <div ref={bottomRef}></div>
                    </div>
                </div>

                {/* 3. ARCHIVE (Past Cycles) */}
                {pastCycles.length > 0 && (
                    <div className="border-t border-white/5 pt-6 mt-6">
                        <div className="text-[10px] text-gray-600 font-mono uppercase tracking-widest mb-4 text-center opacity-50">
                            Completed Sequences
                        </div>
                        {pastCycles.map(([id, cycleLogs]) => (
                            <CycleHistory key={id} cycleId={Number(id)} logs={cycleLogs} />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default Terminal;