import React from 'react';
import { Agent } from '../types';
import { WORKFLOW_STEPS } from '../constants';

interface WorkflowVisualizerProps {
  agents: Agent[];
  activeAgentId: number | null;
  completedAgents: number[];
}

// Fluid Topology - Coordinates in Percentages (0-100)
const NODES = [
  { id: 1, x: 10, y: 50 },  // Orchestrator (Center Left)
  { id: 2, x: 25, y: 20 },  // Scout (Top Left)
  { id: 3, x: 25, y: 80 },  // Interceptor (Bottom Left)
  { id: 4, x: 45, y: 35 },  // Analyst (Mid Top)
  { id: 5, x: 45, y: 65 },  // Sim Scientist (Mid Bot)
  { id: 6, x: 65, y: 20 },  // Auditor
  { id: 7, x: 65, y: 80 },  // Sniper
  { id: 8, x: 80, y: 50 },  // Executioner (Center Right)
  { id: 9, x: 92, y: 20 },  // Accountant
  { id: 10, x: 92, y: 80 }, // Historian
  { id: 11, x: 50, y: 95 }, // Mechanic (Bottom Center)
  { id: 12, x: 50, y: 5 },  // Visualist (Top Center)
  { id: 13, x: 50, y: 50 }, // The Fixer (Dead Center, usually hidden)
];

const CONNECTIONS = [
    { from: 1, to: 2 }, { from: 1, to: 3 },
    { from: 2, to: 4 }, { from: 3, to: 5 },
    { from: 4, to: 6 }, { from: 5, to: 6 }, // Converge on Auditor
    { from: 6, to: 7 }, // Auditor -> Sniper
    { from: 7, to: 8 }, // Sniper -> Executioner
    { from: 8, to: 9 }, { from: 8, to: 10 },
    { from: 1, to: 11 }, { from: 1, to: 12 },
    // Fixer connects to everything centrally
    { from: 13, to: 4 }, { from: 13, to: 5 }, { from: 13, to: 8 }
];

const WorkflowVisualizer: React.FC<WorkflowVisualizerProps> = ({ agents, activeAgentId, completedAgents }) => {

  return (
    <div className="h-full w-full relative overflow-hidden rounded-3xl glass-panel bg-black/80 shadow-2xl flex items-center justify-center p-8 border border-white/5">
      
      {/* 1. Deep Space Background */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-gray-900/40 via-black to-black pointer-events-none"></div>
      
      {/* 2. Fluid SVG Connections (Bezier Curves) */}
      <svg className="absolute inset-0 w-full h-full z-0 pointer-events-none overflow-visible">
        <defs>
            <filter id="glow-line">
                <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
                <feMerge>
                    <feMergeNode in="coloredBlur"/>
                    <feMergeNode in="SourceGraphic"/>
                </feMerge>
            </filter>
        </defs>
        {CONNECTIONS.map((conn, i) => {
            const start = NODES.find(n => n.id === conn.from) || {x:0,y:0};
            const end = NODES.find(n => n.id === conn.to) || {x:0,y:0};
            
            // Check if this path is "Active" (Both nodes are involved in the current/past flow)
            const isPathActive = (completedAgents.includes(conn.from) || activeAgentId === conn.from) && 
                                 (completedAgents.includes(conn.to) || activeAgentId === conn.to);

            // Bezier Control Point (Simple curve effect)
            const cpX = (start.x + end.x) / 2;
            const cpY = (start.y + end.y) / 2 + (i % 2 === 0 ? 10 : -10); // Alternating curve direction

            return (
                <g key={`link-${i}`}>
                    {/* Background Trace */}
                    <path 
                        d={`M ${start.x}% ${start.y}% Q ${cpX}% ${cpY}% ${end.x}% ${end.y}%`}
                        stroke="#222" 
                        strokeWidth="1" 
                        fill="none"
                    />
                    {/* Active Impulse */}
                    <path 
                        d={`M ${start.x}% ${start.y}% Q ${cpX}% ${cpY}% ${end.x}% ${end.y}%`}
                        stroke={isPathActive ? "#10b981" : "transparent"} 
                        strokeWidth="2"
                        fill="none"
                        filter="url(#glow-line)"
                        strokeDasharray="10"
                        className={isPathActive ? "animate-flow opacity-60" : "opacity-0"}
                    />
                </g>
            );
        })}
      </svg>

      {/* 3. Floating Nodes (Star Points) */}
      <div className="relative w-full h-full z-10">
        {agents.map((agent) => {
            const pos = NODES.find(p => p.id === agent.id) || { x: 50, y: 50 };
            const isActive = activeAgentId === agent.id;
            const isCompleted = completedAgents.includes(agent.id);
            const isError = agent.id === 13;
            
            // Hide the fixer unless active or error
            if (agent.id === 13 && !isActive) return null;

            return (
                <div 
                    key={agent.id}
                    className="absolute transform -translate-x-1/2 -translate-y-1/2"
                    style={{ 
                        left: `${pos.x}%`, 
                        top: `${pos.y}%`,
                        // Slight float animation for organic feel
                        animation: `float ${5 + (agent.id % 3)}s ease-in-out infinite ${agent.id * 0.2}s` 
                    }}
                >
                    {/* --- THE STAR NODE --- */}
                    <div className="relative w-16 h-16 flex items-center justify-center">
                        
                        {/* 1. Orbiting Circle (Running around the star) - Active Only */}
                        {isActive && (
                            <svg className="absolute inset-0 w-full h-full rotate-[-90deg]">
                                <circle 
                                    cx="50%" cy="50%" r="28" 
                                    fill="none" 
                                    stroke={isError ? '#ef4444' : '#10b981'}
                                    strokeWidth="1.5"
                                    strokeLinecap="round"
                                    // Custom keyframe in index.html for "running" effect
                                    className="animate-dash" 
                                    strokeDasharray="175" // Circumference ~ 2*PI*28
                                    strokeDashoffset="175"
                                />
                                {/* Inner faint ring for structure */}
                                <circle cx="50%" cy="50%" r="28" stroke="rgba(255,255,255,0.1)" strokeWidth="1" fill="none" />
                            </svg>
                        )}

                        {/* 2. The Star Core */}
                        <div className={`
                            relative rounded-full transition-all duration-700 z-10 flex items-center justify-center
                            ${isActive 
                                ? 'w-3 h-3 bg-white shadow-[0_0_25px_rgba(255,255,255,1)] scale-125' 
                                : isCompleted 
                                    ? 'w-2.5 h-2.5 bg-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.8)]' 
                                    : 'w-1.5 h-1.5 bg-gray-600 opacity-60'}
                        `}>
                             {/* Flare active effect */}
                             {isActive && (
                                <div className="absolute inset-0 bg-white rounded-full animate-ping opacity-50"></div>
                             )}
                        </div>
                        
                        {/* 3. Ambient Glow Field (Active) */}
                        {isActive && (
                            <div className={`absolute inset-0 ${isError ? 'bg-red-500/20' : 'bg-emerald-500/20'} blur-xl rounded-full animate-pulse pointer-events-none`}></div>
                        )}
                    </div>

                    {/* Node Label (Below) */}
                    {!isActive && (
                        <div className={`
                            absolute top-14 left-1/2 -translate-x-1/2 whitespace-nowrap
                            text-[8px] font-mono uppercase tracking-widest transition-all duration-500
                            ${isCompleted ? 'text-emerald-500/60 translate-y-0' : 'text-gray-700 translate-y-1 opacity-50'}
                        `}>
                            {agent.name.split(' ').pop()}
                        </div>
                    )}

                    {/* --- SUMMARY POPUP (Smooth Animation) --- */}
                    {/* Shows "Summary" while running, then implies moving to next via completion state */}
                    {isActive && (
                        <div className={`
                            absolute top-1/2 pointer-events-none origin-center
                            ${pos.x > 60 ? 'right-full mr-8' : 'left-full ml-8'} 
                            -translate-y-1/2 w-[280px] z-50
                            animate-scale-in
                        `}>
                            <div className={`
                                glass-panel bg-black/95 p-5 rounded-2xl relative shadow-2xl backdrop-blur-2xl
                                ${isError ? 'border-red-500/50 shadow-[0_0_30px_rgba(239,68,68,0.2)]' : 'border-emerald-500/50 shadow-[0_0_30px_rgba(16,185,129,0.2)]'}
                            `}>
                                 {/* Connector Line to Star */}
                                 <div className={`
                                    absolute top-1/2 w-8 h-[1px]
                                    ${pos.x > 60 ? '-right-8 bg-gradient-to-l' : '-left-8 bg-gradient-to-r'}
                                    from-emerald-500/50 to-transparent
                                 `}></div>

                                 <div className="flex justify-between items-center mb-3">
                                    <h4 className={`font-tech text-sm uppercase tracking-wider font-bold ${isError ? 'text-red-400' : 'text-emerald-400'}`}>
                                        {agent.name}
                                    </h4>
                                    <div className="flex items-center gap-2">
                                        <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse"></span>
                                        <span className="text-[9px] font-mono text-gray-400 uppercase">Processing</span>
                                    </div>
                                 </div>
                                 
                                 <div className="text-[10px] text-gray-500 font-mono mb-3 flex items-center gap-2 bg-white/5 p-1.5 rounded-lg border border-white/5">
                                    <span className="text-emerald-500/50">CPU:</span>
                                    <span>{agent.model}</span>
                                 </div>
                                 
                                 <div className="bg-black/50 rounded-xl p-3 border border-white/10 relative overflow-hidden">
                                     <div className="absolute top-0 left-0 w-1 h-full bg-emerald-500/50"></div>
                                     <div className="flex gap-2">
                                         <span className={`text-[10px] mt-[2px] ${isError ? 'text-red-500' : 'text-emerald-500'}`}>►</span>
                                         <p className="text-[11px] text-gray-200 font-mono leading-relaxed">
                                             {WORKFLOW_STEPS[agent.id]}
                                         </p>
                                     </div>
                                 </div>
                                 
                                 {/* Decorative footer line */}
                                 <div className="mt-2 flex justify-end">
                                     <div className="w-12 h-[2px] bg-emerald-500/30 rounded-full animate-pulse"></div>
                                 </div>
                            </div>
                        </div>
                    )}
                </div>
            );
        })}
      </div>
    </div>
  );
};

export default WorkflowVisualizer;