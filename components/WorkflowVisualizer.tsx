import React, { useEffect, useRef, useState } from 'react';
import { Agent } from '../types';
import { WORKFLOW_STEPS } from '../constants';

interface WorkflowVisualizerProps {
  agents: Agent[];
  activeAgentId: number | null;
  completedAgents: number[];
}

const WorkflowVisualizer: React.FC<WorkflowVisualizerProps> = ({ agents, activeAgentId, completedAgents }) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  
  // Logic to determine which agents to show
  // We want to show: All Completed + Current Active + Next 2 Pending
  const relevantAgents = agents.filter((agent) => {
    // Always show hidden agents if they are active or completed (like the debugger)
    if (agent.hidden && (agent.id === activeAgentId || completedAgents.includes(agent.id))) return true;
    if (agent.hidden) return false;

    const isCompleted = completedAgents.includes(agent.id);
    const isActive = activeAgentId === agent.id;
    
    // Find index of current active to determine "Next 2"
    const activeIndex = agents.findIndex(a => a.id === activeAgentId);
    const thisIndex = agents.findIndex(a => a.id === agent.id);
    
    // Show if completed, active, or within next 2 steps (and not hidden)
    if (isCompleted || isActive) return true;
    if (activeAgentId && thisIndex > activeIndex && thisIndex <= activeIndex + 2) return true;
    
    // Initial state: show first 3
    if (!activeAgentId && thisIndex < 3) return true;
    
    return false;
  });

  // Auto-scroll to keep active agent centered
  useEffect(() => {
    if (activeAgentId && scrollContainerRef.current) {
        const activeEl = document.getElementById(`node-${activeAgentId}`);
        if (activeEl) {
            activeEl.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
        }
    }
  }, [activeAgentId, relevantAgents.length]);

  return (
    <div className="h-full w-full relative overflow-hidden rounded-2xl glass-panel flex flex-col">
      {/* Background Ambience */}
      <div className="absolute inset-0 bg-gradient-to-r from-emerald-900/10 via-black to-purple-900/10 opacity-50"></div>
      
      {/* Header */}
      <div className="absolute top-4 left-6 z-20">
        <h2 className="text-white font-tech uppercase tracking-widest text-lg flex items-center gap-3">
            <span className="w-3 h-3 rounded-full bg-emerald-500 shadow-[0_0_15px_#10b981] animate-pulse"></span>
            Neural Stream
        </h2>
        <div className="text-[10px] text-gray-400 font-mono mt-1">Real-time Execution Pipeline</div>
      </div>

      {/* Horizontal Stream Container */}
      <div 
        ref={scrollContainerRef}
        className="flex-1 flex items-center overflow-x-auto no-scrollbar px-12 py-8 relative z-10 scroll-smooth"
      >
        {/* Connecting Line (SVG Layer) */}
        <div className="absolute top-1/2 left-0 w-full h-1 z-0 -translate-y-1/2 pointer-events-none">
            <svg className="w-full h-full overflow-visible">
                <defs>
                    <linearGradient id="streamGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="rgba(16, 185, 129, 0.1)" />
                        <stop offset="50%" stopColor="rgba(16, 185, 129, 0.5)" />
                        <stop offset="100%" stopColor="rgba(16, 185, 129, 0.1)" />
                    </linearGradient>
                </defs>
                {/* We draw a simple straight line since we are flex-aligned, but style it nicely */}
                <line x1="0" y1="0" x2="100%" y2="0" stroke="url(#streamGradient)" strokeWidth="2" />
            </svg>
        </div>

        {relevantAgents.map((agent, index) => {
          const isActive = activeAgentId === agent.id;
          const isCompleted = completedAgents.includes(agent.id);
          const isPending = !isActive && !isCompleted;
          
          return (
            <div 
                key={agent.id} 
                id={`node-${agent.id}`}
                className={`
                    relative shrink-0 transition-all duration-700 ease-out mx-4 group
                    ${isActive ? 'w-[320px] scale-100 z-20' : 'w-[200px] scale-95 opacity-60 hover:opacity-100 z-10'}
                `}
            >
                {/* Connecting Dot on Line */}
                <div className="absolute top-1/2 -left-6 w-3 h-3 rounded-full bg-gray-800 border border-gray-600 -translate-y-1/2 z-0">
                    {isCompleted && <div className="absolute inset-0 bg-emerald-500 rounded-full animate-ping opacity-20"></div>}
                </div>

                {/* The Card */}
                <div className={`
                    h-[220px] rounded-[32px] p-6 flex flex-col justify-between backdrop-blur-xl border transition-all duration-500
                    ${isActive 
                        ? 'bg-gradient-to-br from-gray-900 via-black to-emerald-900/30 border-emerald-500/50 organic-glow shadow-2xl' 
                        : isCompleted 
                            ? 'bg-gray-900/40 border-emerald-500/20' 
                            : 'bg-gray-900/20 border-white/5 grayscale'}
                `}>
                    
                    {/* Top Section */}
                    <div className="flex justify-between items-start">
                        <div className={`
                            w-12 h-12 rounded-2xl flex items-center justify-center text-lg font-bold font-mono transition-colors
                            ${isActive ? 'bg-emerald-500 text-black shadow-lg' : isCompleted ? 'bg-emerald-900/50 text-emerald-400' : 'bg-gray-800 text-gray-500'}
                        `}>
                            {agent.id}
                        </div>
                        
                        {isActive && (
                            <div className="flex items-center gap-2">
                                <span className="relative flex h-3 w-3">
                                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                  <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                                </span>
                                <span className="text-[10px] font-mono text-emerald-400 uppercase tracking-widest animate-pulse">Processing</span>
                            </div>
                        )}
                        {isCompleted && <span className="text-emerald-500 text-xl">✓</span>}
                    </div>

                    {/* Middle Section: Info */}
                    <div className="mt-4">
                        <h3 className={`font-tech text-xl uppercase tracking-wide mb-1 ${isActive ? 'text-white' : 'text-gray-400'}`}>
                            {agent.name}
                        </h3>
                        <p className="text-[10px] font-mono uppercase tracking-widest text-gray-500 mb-3 border-b border-gray-800 pb-2 inline-block">
                            {agent.role}
                        </p>
                        
                        {isActive ? (
                             <div className="h-16 relative overflow-hidden">
                                <p className="text-sm text-emerald-300 font-mono leading-relaxed typewriter">
                                    {'>'} {WORKFLOW_STEPS[agent.id] || "Initializing logic..."}
                                </p>
                             </div>
                        ) : (
                            <p className="text-xs text-gray-500 line-clamp-2 leading-relaxed">
                                {isCompleted ? "Task execution verified." : agent.description}
                            </p>
                        )}
                    </div>

                    {/* Bottom Section: Metrics (Only for active) */}
                    {isActive && (
                        <div className="mt-auto pt-4 border-t border-white/5 flex gap-4">
                            <div className="flex flex-col">
                                <span className="text-[9px] text-gray-500 uppercase">CPU</span>
                                <div className="w-16 h-1 bg-gray-800 rounded-full mt-1 overflow-hidden">
                                    <div className="h-full bg-emerald-500 w-2/3 animate-[slide_2s_ease-in-out_infinite]"></div>
                                </div>
                            </div>
                            <div className="flex flex-col">
                                <span className="text-[9px] text-gray-500 uppercase">NET</span>
                                <div className="w-16 h-1 bg-gray-800 rounded-full mt-1 overflow-hidden">
                                    <div className="h-full bg-blue-500 w-1/2 animate-[pulse_1s_infinite]"></div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Connection Curve to Next Node */}
                {index < relevantAgents.length - 1 && (
                     <div className="absolute top-1/2 -right-4 w-8 h-[2px] bg-gray-800 -translate-y-1/2 z-0 hidden md:block">
                         {isActive && <div className="h-full bg-emerald-500 w-full animate-flow origin-left"></div>}
                     </div>
                )}
            </div>
          );
        })}
        
        {/* End of Stream Placeholder */}
        <div className="w-24 shrink-0 h-[2px] bg-gradient-to-r from-gray-800 to-transparent"></div>
      </div>
    </div>
  );
};

export default WorkflowVisualizer;
