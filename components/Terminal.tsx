import React, { useEffect, useMemo, useState } from 'react';
import { LogEntry } from '../types';

interface TerminalProps {
  logs: LogEntry[];
}

const CycleGroup: React.FC<{ 
    cycleId: number; 
    logs: LogEntry[]; 
    isExpanded: boolean; 
    toggle: () => void;
    isLatest: boolean;
}> = ({ cycleId, logs, isExpanded, toggle, isLatest }) => {
    
    // Auto-derive status and title from logs
    const hasError = logs.some(l => l.level === 'ERROR');
    const isSuccess = logs.some(l => l.message.includes('ORDER FILLED') || l.message.includes('Cycle Finished'));
    
    // Try to find a meaningful target name
    const targetLog = logs.find(l => l.message.includes('TARGET LOCK') || l.message.includes('Target:'));
    const targetName = targetLog 
        ? targetLog.message.split(':').pop()?.replace('(', '').replace(')', '').trim() 
        : logs.find(l => l.message.includes('Scanning')) ? 'Scanning Market...' : 'System Idle';

    // Status Color Logic
    const statusColor = isLatest && !isSuccess && !hasError ? 'text-blue-400' 
        : hasError ? 'text-red-400' 
        : isSuccess ? 'text-emerald-400' 
        : 'text-gray-400';
    
    const borderColor = isLatest && !isSuccess && !hasError ? 'border-blue-500/50' 
        : hasError ? 'border-red-500/50' 
        : isSuccess ? 'border-emerald-500/50' 
        : 'border-white/10';

    const bgGradient = isLatest ? 'bg-gradient-to-r from-blue-900/20 to-transparent' 
        : hasError ? 'bg-red-900/10'
        : isSuccess ? 'bg-emerald-900/10'
        : 'bg-white/5';

    return (
        <div className={`mb-3 rounded-xl border ${borderColor} overflow-hidden transition-all duration-300 ${isExpanded ? 'shadow-lg bg-white/5' : ''}`}>
            {/* Header / Summary */}
            <div 
                onClick={toggle}
                className={`flex items-center justify-between p-3 cursor-pointer ${bgGradient} hover:bg-white/10 transition-colors`}
            >
                <div className="flex items-center gap-3 overflow-hidden">
                    <div className={`flex flex-col items-center justify-center w-8 h-8 rounded-lg border ${borderColor} bg-black/40`}>
                        <span className="text-[8px] uppercase text-gray-500 font-mono leading-none">CYC</span>
                        <span className={`text-xs font-bold font-mono ${statusColor}`}>{cycleId === 0 ? 'SYS' : cycleId}</span>
                    </div>
                    
                    <div className="flex flex-col overflow-hidden">
                        <span className="text-[10px] text-gray-500 font-mono uppercase tracking-wider flex items-center gap-2">
                             {logs[0]?.timestamp.split('.')[0] || '--:--:--'} 
                             {isLatest && !isSuccess && !hasError && <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></span>}
                        </span>
                        <span className={`text-xs font-bold truncate ${statusColor} font-tech tracking-wide uppercase`}>
                            {targetName}
                        </span>
                    </div>
                </div>

                <div className={`text-[10px] font-mono transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''} text-gray-500`}>
                    ▼
                </div>
            </div>

            {/* Expanded Content */}
            {isExpanded && (
                <div className="bg-black/40 border-t border-white/5 p-3 space-y-1.5 font-mono text-[10px] animate-[slideDown_0.2s_ease-out]">
                     {logs.map(log => (
                        <div key={log.id} className="flex gap-2 group/line">
                            <span className="text-gray-600 shrink-0 opacity-50 select-none group-hover/line:opacity-100 transition-opacity">
                                {log.timestamp.split('.')[0]}
                            </span>
                            <div className="break-words leading-relaxed text-gray-400 group-hover/line:text-gray-200">
                                <span className={`mr-2 font-bold ${
                                    log.level === 'INFO' ? 'text-blue-500/50' :
                                    log.level === 'SUCCESS' ? 'text-emerald-500/80' :
                                    log.level === 'WARN' ? 'text-amber-500/80' : 'text-red-500/80'
                                }`}>
                                    {log.level === 'INFO' ? '›' : log.level === 'WARN' ? '⚠' : log.level === 'ERROR' ? '✖' : '✓'}
                                </span>
                                {log.message}
                            </div>
                        </div>
                     ))}
                     {isLatest && (
                         <div className="h-4 flex items-center justify-center gap-1 opacity-30 mt-2">
                             <span className="w-1 h-1 bg-gray-500 rounded-full animate-bounce"></span>
                             <span className="w-1 h-1 bg-gray-500 rounded-full animate-bounce [animation-delay:0.1s]"></span>
                             <span className="w-1 h-1 bg-gray-500 rounded-full animate-bounce [animation-delay:0.2s]"></span>
                         </div>
                     )}
                </div>
            )}
        </div>
    );
}

const Terminal: React.FC<TerminalProps> = ({ logs }) => {
  const [expandedCycles, setExpandedCycles] = useState<Record<number, boolean>>({});

  // Group logs by cycleId
  const groupedLogs = useMemo(() => {
    const groups: Record<number, LogEntry[]> = {};
    logs.forEach(log => {
        const cid = log.cycleId ?? 0;
        if (!groups[cid]) groups[cid] = [];
        groups[cid].push(log);
    });
    
    // Newest First
    return Object.keys(groups)
        .map(Number)
        .sort((a, b) => b - a)
        .map(cid => ({
            id: cid,
            logs: groups[cid]
        }));
  }, [logs]);

  // Strict Auto-Collapse: Only the single newest cycle is open.
  // Dependencies: Trigger whenever the newest cycle ID changes.
  const newestCycleId = groupedLogs.length > 0 ? groupedLogs[0].id : null;
  
  useEffect(() => {
      if (newestCycleId !== null) {
          // Reset explicitly ensures older ones collapse
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
        {/* Ambient Glow */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/5 blur-[80px] rounded-full pointer-events-none"></div>

        {/* Header */}
        <div className="flex justify-between items-center px-5 py-4 border-b border-white/5 bg-black/20 backdrop-blur-xl shrink-0 z-10">
            <div className="flex items-center gap-3">
                <div className="flex gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-red-500/20 border border-red-500/50"></div>
                    <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/20 border border-yellow-500/50"></div>
                    <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/20 border border-emerald-500/50"></div>
                </div>
                <h3 className="text-gray-400 font-mono text-xs uppercase tracking-widest ml-2">
                    Neural_Trace_v2.1
                </h3>
            </div>
            <div className="px-2 py-1 rounded-full bg-emerald-900/20 border border-emerald-500/20">
                <span className="text-[10px] text-emerald-400 font-mono flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></span>
                    HISTORY: DESC
                </span>
            </div>
        </div>

        {/* Log Stream Container */}
        <div className="flex-1 overflow-y-auto min-h-0 p-4 scroll-smooth no-scrollbar relative z-0">
            {/* Background Texture */}
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