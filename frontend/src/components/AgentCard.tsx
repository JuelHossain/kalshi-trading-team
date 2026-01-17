import React from 'react';
import { Agent, AgentStatus } from '@shared/types';

interface AgentCardProps {
  agent: Agent;
  isActive?: boolean;
}

const AgentCard: React.FC<AgentCardProps> = ({ agent, isActive }) => {
  const getStatusStyles = (status: AgentStatus) => {
    // Base style with active override
    if (isActive) {
      return 'bg-emerald-900/30 border-emerald-500 text-emerald-400 shadow-[0_0_20px_rgba(16,185,129,0.4)] scale-[1.03] z-10 ring-1 ring-emerald-400/50';
    }

    switch (status) {
      case AgentStatus.WORKING:
        return 'bg-emerald-500/5 border-emerald-500/30 text-emerald-400 hover:border-emerald-500/60 shadow-[0_0_10px_rgba(16,185,129,0.1)]';
      case AgentStatus.WARNING:
        return 'bg-amber-500/5 border-amber-500/30 text-amber-400 hover:border-amber-500/60 shadow-[0_0_10px_rgba(245,158,11,0.1)]';
      case AgentStatus.CRITICAL:
        return 'bg-red-500/5 border-red-500/30 text-red-400 hover:border-red-500/60 shadow-[0_0_10px_rgba(239,68,68,0.1)] animate-[pulse_2s_cubic-bezier(0.4,0,0.6,1)_infinite]';
      case AgentStatus.SUCCESS:
        return 'bg-blue-500/5 border-blue-500/30 text-blue-400 hover:border-blue-500/60 shadow-[0_0_10px_rgba(59,130,246,0.1)]';
      default:
        return 'bg-gray-800/40 border-gray-700 text-gray-500 hover:border-gray-600';
    }
  };

  const getStatusDot = (status: AgentStatus) => {
    if (isActive) return 'animate-[ping_1s_cubic-bezier(0,0,0.2,1)_infinite] bg-emerald-400';

    switch (status) {
      case AgentStatus.WORKING: return 'animate-pulse bg-emerald-500';
      case AgentStatus.WARNING: return 'animate-[bounce_1s_infinite] bg-amber-500'; // Slow bounce/blink
      case AgentStatus.CRITICAL: return 'animate-[ping_0.5s_cubic-bezier(0,0,0.2,1)_infinite] bg-red-500'; // Rapid ping
      case AgentStatus.SUCCESS: return 'bg-blue-500 shadow-[0_0_5px_#3b82f6]'; // Steady glow
      default: return 'bg-gray-600';
    }
  };

  return (
    <div className={`relative p-4 rounded-sm border backdrop-blur-sm transition-all duration-300 group ${getStatusStyles(agent.status)}`}>
      {/* Active scanning line effect for active card */}
      {isActive && (
        <div className="absolute inset-0 overflow-hidden rounded-sm pointer-events-none">
          <div className="absolute top-0 left-0 w-full h-[2px] bg-emerald-400/50 shadow-[0_0_10px_#34d399] animate-[scan_2s_linear_infinite]"></div>
        </div>
      )}

      {/* Status Corner Indicator */}
      {isActive && (
        <div className="absolute -top-[1px] -right-[1px] flex h-3 w-3">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
        </div>
      )}

      <div className="flex justify-between items-start mb-2 relative z-10">
        <h4 className="font-bold text-sm flex items-center gap-2 font-tech uppercase tracking-wider">
          {isActive && <span className="text-emerald-400 text-xs animate-pulse">▶</span>}
          {agent.name}
        </h4>
        <div className={`w-2 h-2 rounded-full ${getStatusDot(agent.status)} shadow-[0_0_8px_currentColor]`} />
      </div>

      <div className="text-xs font-mono text-gray-400 mb-2 min-h-[1.5em] opacity-80">{agent.role}</div>
      <div className="text-xs text-gray-300 mb-3 line-clamp-2 min-h-[3em] leading-relaxed">{agent.description}</div>

      <div className="border-t border-white/5 pt-2 mt-2">
        <div className="flex justify-between items-center text-[9px] font-mono uppercase tracking-wide opacity-60">
          <span>Model</span>
          <span>{agent.model}</span>
        </div>
        <div className="mt-1.5 text-[10px] truncate font-mono flex items-center gap-2">
          <span className="text-gray-600">{'>'}</span>
          <span className={isActive ? "text-emerald-400 font-bold animate-pulse" : "text-gray-400"}>
            {isActive ? 'EXECUTING DIRECTIVE...' : agent.lastAction}
          </span>
        </div>
      </div>

      {/* Hover glow effect for non-active cards */}
      {!isActive && (
        <div className="absolute inset-0 bg-white/0 group-hover:bg-white/[0.02] transition-colors duration-300 pointer-events-none rounded-sm"></div>
      )}
    </div>
  );
};

export default AgentCard;
