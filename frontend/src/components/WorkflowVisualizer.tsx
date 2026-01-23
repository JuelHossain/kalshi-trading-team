import React from 'react';
import { Agent } from '@shared/types';
import { WORKFLOW_STEPS } from '@shared/constants';

interface WorkflowVisualizerProps {
    agents: Agent[];
    activeAgentId: number | null;
    completedAgents: number[];
    agentData?: Record<number, any>;
}

// Funnel Topology: Wide Left -> Narrow Center -> Execution Right
const NODES = [
    { id: 1, x: 10, y: 50 },  // Orchestrator (Far Left Start)
    { id: 11, x: 10, y: 85 }, // Mechanic (Below Start)

    // Phase 2: Wide Net (Scout & Interceptor)
    { id: 2, x: 25, y: 25 },  // Scout (Top Left)
    { id: 3, x: 25, y: 75 },  // Interceptor (Bottom Left)

    // Phase 3: The Filter (Analyst) - Central Hub
    { id: 4, x: 45, y: 50 },  // Analyst (Center)
    { id: 5, x: 45, y: 20 },  // Sim Scientist (Satellite Top - Standby)
    { id: 6, x: 45, y: 80 },  // Auditor (Satellite Bottom - Standby)

    // Phase 4: Sequential Execution Loop
    { id: 8, x: 70, y: 50 },  // Executioner (Center Right Hub)
    { id: 9, x: 70, y: 20 },  // Accountant (Risk Check - Top)
    { id: 7, x: 70, y: 80 },  // Sniper (Order Book - Bottom)

    // End State
    { id: 10, x: 90, y: 50 }, // Historian (Far Right End)

    { id: 12, x: 50, y: 5 },  // Visualist (Header)
    { id: 13, x: 50, y: 50 }, // Fixer (Hidden Layer)
];

// Connections reflecting the "Funnel" Logic
const CONNECTIONS = [
    // Phase 1 -> 2
    { from: 1, to: 11 }, // Init Check
    { from: 1, to: 2 },  // Start Scout
    { from: 1, to: 3 },  // Start Interceptor

    // Phase 2 -> 3 (Convergence)
    { from: 2, to: 4 },  // Scout data to Analyst
    { from: 3, to: 4 },  // Odds data to Analyst

    // Optional Standby Paths (Visual completeness)
    { from: 4, to: 5 }, { from: 5, to: 4 },
    { from: 4, to: 6 }, { from: 6, to: 4 },

    // Phase 3 -> 4 (Handoff to Execution)
    { from: 4, to: 8 },

    // Phase 4: The Loop (Star Topology around Executioner)
    { from: 8, to: 9 }, { from: 9, to: 8 }, // Balance Check
    { from: 8, to: 7 }, { from: 7, to: 8 }, // Depth Check
    { from: 8, to: 10 }, // Log Result

    // Error Handling
    { from: 13, to: 4 }, { from: 13, to: 8 }, { from: 13, to: 1 }
];

const WorkflowVisualizer: React.FC<WorkflowVisualizerProps & { onAgentClick?: (id: number) => void }> = ({ agents, activeAgentId, completedAgents, agentData = {}, onAgentClick }) => {
    const [hoveredAgentId, setHoveredAgentId] = React.useState<number | null>(null);

    return (
        <div className="h-full w-full relative overflow-hidden rounded-3xl glass-panel bg-black/80 shadow-2xl flex items-center justify-center p-8 border border-white/5">

            {/* 1. Deep Space Background */}
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-gray-900/40 via-black to-black pointer-events-none"></div>

            {/* 2. Fluid SVG Connections (Bezier Curves) */}
            <svg className="absolute inset-0 w-full h-full z-0 pointer-events-none overflow-visible">
                <defs>
                    <filter id="glow-line">
                        <feGaussianBlur stdDeviation="2" result="coloredBlur" />
                        <feMerge>
                            <feMergeNode in="coloredBlur" />
                            <feMergeNode in="SourceGraphic" />
                        </feMerge>
                    </filter>
                </defs>
                {CONNECTIONS.map((conn, i) => {
                    const start = NODES.find(n => n.id === conn.from) || { x: 0, y: 0 };
                    const end = NODES.find(n => n.id === conn.to) || { x: 0, y: 0 };

                    // Check if this path is "Active" (Both nodes are involved in the current/past flow)
                    const isPathActive = (completedAgents.includes(conn.from) || activeAgentId === conn.from) &&
                        (completedAgents.includes(conn.to) || activeAgentId === conn.to);

                    // Bezier Control Point (Simple curve effect)
                    const cpX = (start.x + end.x) / 2;
                    const cpY = (start.y + end.y) / 2 + (i % 2 === 0 ? 15 : -15); // Alternating curve direction

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
                    const isHovered = hoveredAgentId === agent.id;
                    const isError = agent.id === 13;
                    const data = agentData[agent.id];

                    // Hide the fixer unless active or error OR explicitly hovered (to test it)
                    if (agent.id === 13 && !isActive && !isHovered) return null;

                    return (
                        <div
                            key={agent.id}
                            className="absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer group"
                            style={{
                                left: `${pos.x}%`,
                                top: `${pos.y}%`,
                                // Slight float animation for organic feel
                                animation: `float ${5 + (agent.id % 3)}s ease-in-out infinite ${agent.id * 0.2}s`
                            }}
                            onMouseEnter={() => setHoveredAgentId(agent.id)}
                            onMouseLeave={() => setHoveredAgentId(null)}
                            onClick={() => onAgentClick && onAgentClick(agent.id)}
                        >
                            {/* --- THE STAR NODE --- */}
                            <div className="relative w-16 h-16 flex items-center justify-center transition-transform duration-300 group-hover:scale-110">

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
                                        : isHovered
                                            ? 'w-3 h-3 bg-emerald-400 shadow-[0_0_20px_rgba(52,211,153,0.6)] scale-110'
                                            : isCompleted
                                                ? 'w-2.5 h-2.5 bg-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.8)]'
                                                : 'w-1.5 h-1.5 bg-gray-600 opacity-60'}
                        `}>
                                    {/* Flare active effect */}
                                    {isActive && (
                                        <div className="absolute inset-0 bg-white rounded-full animate-ping opacity-50"></div>
                                    )}
                                </div>

                                {/* 3. Ambient Glow Field (Active or Hovered) */}
                                {(isActive || isHovered) && (
                                    <div className={`absolute inset-0 ${isError ? 'bg-red-500/20' : 'bg-emerald-500/20'} blur-xl rounded-full animate-pulse pointer-events-none`}></div>
                                )}
                            </div>

                            {/* Node Label (Below) */}
                            {!isActive && !isHovered && (
                                <div className={`
                            absolute top-14 left-1/2 -translate-x-1/2 whitespace-nowrap
                            text-[8px] font-mono uppercase tracking-widest transition-all duration-500
                            ${isCompleted ? 'text-emerald-500/60 translate-y-0' : 'text-gray-700 translate-y-1 opacity-50'}
                        `}>
                                    {agent.name.split(' ').pop()}
                                </div>
                            )}

                            {/* --- SUMMARY POPUP (Smooth Animation) --- */}
                            {/* Check for Hover OR Active (ONLY for ERROR/FIXER) for the expanded view */}
                            {(isHovered || (isActive && isError)) && (
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
                                                <span className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-white animate-pulse' : 'bg-gray-500'}`}></span>
                                                <span className="text-[9px] font-mono text-gray-400 uppercase">
                                                    {isActive ? 'Processing' : (isHovered ? 'Click to Test' : agent.status)}
                                                </span>
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
                                                <div className="text-[11px] text-gray-200 font-mono leading-relaxed w-full">
                                                    {/* DATA DISPLAY LOGIC */}
                                                    {data ? (
                                                        <div className="space-y-1">
                                                            {agent.id === 4 && (
                                                                <>
                                                                    <div className="flex justify-between"><span className="text-gray-500">Verdict:</span> <span className="text-white font-bold">{data.judgeVerdict}</span></div>
                                                                    <div className="flex justify-between"><span className="text-gray-500">Confidence:</span> <span className="text-emerald-400">{data.confidenceScore}%</span></div>
                                                                </>
                                                            )}
                                                            {agent.id === 7 && (
                                                                <>
                                                                    <div className="flex justify-between"><span className="text-gray-500">Snipe:</span> <span className="text-white font-bold">{data.snipe_price}c</span></div>
                                                                    <div className="flex justify-between"><span className="text-gray-500">Spread:</span> <span className="text-emerald-400">{data.spread}c</span></div>
                                                                    <div className="flex justify-between"><span className="text-gray-500">Liquid:</span> <span className={data.is_liquid ? "text-emerald-400" : "text-red-400"}>{data.is_liquid ? "YES" : "NO"}</span></div>
                                                                </>
                                                            )}
                                                            {agent.id === 5 && (
                                                                <>
                                                                    <div className="flex justify-between"><span className="text-gray-500">EV Score:</span> <span className="text-white font-bold">{data.evScore?.toFixed(2)}</span></div>
                                                                    <div className="flex justify-between"><span className="text-gray-500">Win Rate:</span> <span className="text-emerald-400">{(data.winRate * 100)?.toFixed(1)}%</span></div>
                                                                </>
                                                            )}
                                                            {![4, 5, 7].includes(agent.id) && (
                                                                <p className="text-[10px] text-gray-400 wrap-text">{JSON.stringify(data).substring(0, 50)}...</p>
                                                            )}
                                                        </div>
                                                    ) : (
                                                        <p>{isActive ? WORKFLOW_STEPS[agent.id] : agent.description}</p>
                                                    )}
                                                </div>
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