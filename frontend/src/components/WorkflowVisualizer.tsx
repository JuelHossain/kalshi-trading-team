import React from 'react';
import { Agent } from '@shared/types';
import { WORKFLOW_STEPS, PHASES } from '@shared/constants';

interface WorkflowVisualizerProps {
    agents: Agent[];
    activeAgentId: number | null;
    completedAgents: number[];
    currentPhaseId?: number;
}

// 4 Mega-Agent Vertical Topology: SOUL → SENSES → BRAIN → HAND
const NODES = [
    { id: 1, x: 50, y: 12 },  // SOUL (Top)
    { id: 2, x: 50, y: 37 },  // SENSES
    { id: 3, x: 50, y: 62 },  // BRAIN
    { id: 4, x: 50, y: 87 },  // HAND (Bottom)
];

// Vertical Pipeline Connections
const CONNECTIONS = [
    { from: 1, to: 2 },  // SOUL → SENSES
    { from: 2, to: 3 },  // SENSES → BRAIN
    { from: 3, to: 4 },  // BRAIN → HAND
];

// Agent metadata for display
const AGENT_META: Record<number, { icon: string; color: string; glow: string }> = {
    1: { icon: '👁️', color: 'purple', glow: 'rgba(168, 85, 247, 0.5)' },
    2: { icon: '📡', color: 'blue', glow: 'rgba(59, 130, 246, 0.5)' },
    3: { icon: '🧠', color: 'pink', glow: 'rgba(236, 72, 153, 0.5)' },
    4: { icon: '✋', color: 'emerald', glow: 'rgba(16, 185, 129, 0.5)' },
};

const WorkflowVisualizer: React.FC<WorkflowVisualizerProps & { onAgentClick?: (id: number) => void }> = ({
    agents,
    activeAgentId,
    completedAgents,
    currentPhaseId = 0,
    onAgentClick
}) => {
    const [hoveredAgentId, setHoveredAgentId] = React.useState<number | null>(null);

    return (
        <div className="h-full w-full relative overflow-hidden rounded-3xl glass-panel bg-black/80 shadow-2xl flex items-center justify-center p-8 border border-white/5">

            {/* Deep Space Background */}
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-gray-900/40 via-black to-black pointer-events-none"></div>

            {/* Pipeline SVG */}
            <svg className="absolute inset-0 w-full h-full z-0 pointer-events-none overflow-visible">
                <defs>
                    <filter id="glow-line">
                        <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                        <feMerge>
                            <feMergeNode in="coloredBlur" />
                            <feMergeNode in="SourceGraphic" />
                        </feMerge>
                    </filter>
                    <linearGradient id="pipeline-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" stopColor="#a855f7" />
                        <stop offset="33%" stopColor="#3b82f6" />
                        <stop offset="66%" stopColor="#ec4899" />
                        <stop offset="100%" stopColor="#10b981" />
                    </linearGradient>
                </defs>

                {CONNECTIONS.map((conn, i) => {
                    const start = NODES.find(n => n.id === conn.from) || { x: 50, y: 0 };
                    const end = NODES.find(n => n.id === conn.to) || { x: 50, y: 100 };

                    const isPathActive = (completedAgents.includes(conn.from) || activeAgentId === conn.from) &&
                        (completedAgents.includes(conn.to) || activeAgentId === conn.to);

                    return (
                        <g key={`link-${i}`}>
                            {/* Background Line */}
                            <line
                                x1={`${start.x}%`} y1={`${start.y}%`}
                                x2={`${end.x}%`} y2={`${end.y}%`}
                                stroke="#222"
                                strokeWidth="2"
                            />
                            {/* Active Pulse Line */}
                            <line
                                x1={`${start.x}%`} y1={`${start.y}%`}
                                x2={`${end.x}%`} y2={`${end.y}%`}
                                stroke={isPathActive ? "url(#pipeline-gradient)" : "transparent"}
                                strokeWidth="4"
                                filter="url(#glow-line)"
                                strokeDasharray="10"
                                className={isPathActive ? "animate-flow opacity-80" : "opacity-0"}
                            />
                        </g>
                    );
                })}
            </svg>

            {/* 4 Mega-Agent Nodes */}
            <div className="relative w-full h-full z-10">
                {agents.map((agent) => {
                    const pos = NODES.find(p => p.id === agent.id);
                    if (!pos) return null;

                    const isActive = activeAgentId === agent.id;
                    const isCompleted = completedAgents.includes(agent.id);
                    const isHovered = hoveredAgentId === agent.id;
                    const meta = AGENT_META[agent.id] || { icon: '⚡', color: 'gray', glow: 'rgba(100,100,100,0.5)' };

                    return (
                        <div
                            key={agent.id}
                            className="absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer group"
                            style={{
                                left: `${pos.x}%`,
                                top: `${pos.y}%`,
                            }}
                            onMouseEnter={() => setHoveredAgentId(agent.id)}
                            onMouseLeave={() => setHoveredAgentId(null)}
                            onClick={() => onAgentClick && onAgentClick(agent.id)}
                        >
                            {/* Node Container */}
                            <div className={`
                                relative flex flex-col items-center transition-all duration-500
                                ${isActive ? 'scale-125' : isHovered ? 'scale-110' : 'scale-100'}
                            `}>
                                {/* Orbiting Ring (Active) */}
                                {isActive && (
                                    <svg className="absolute w-24 h-24 -inset-4 rotate-[-90deg]">
                                        <circle
                                            cx="50%" cy="50%" r="40"
                                            fill="none"
                                            stroke={meta.glow}
                                            strokeWidth="2"
                                            strokeLinecap="round"
                                            className="animate-dash"
                                            strokeDasharray="250"
                                            strokeDashoffset="250"
                                        />
                                    </svg>
                                )}

                                {/* Core Icon */}
                                <div
                                    className={`
                                        w-16 h-16 rounded-2xl flex items-center justify-center text-3xl
                                        transition-all duration-500 backdrop-blur-sm
                                        ${isActive
                                            ? 'bg-white/10 border-2 border-white/50'
                                            : isCompleted
                                                ? 'bg-emerald-500/20 border border-emerald-500/50'
                                                : 'bg-white/5 border border-white/10'}
                                    `}
                                    style={{
                                        boxShadow: isActive ? `0 0 40px ${meta.glow}` : 'none'
                                    }}
                                >
                                    {meta.icon}
                                    {isActive && (
                                        <div className="absolute inset-0 bg-white/10 rounded-2xl animate-ping opacity-30"></div>
                                    )}
                                </div>

                                {/* Agent Name */}
                                <div className={`
                                    mt-3 text-center transition-all duration-300
                                    ${isActive ? 'opacity-100' : 'opacity-60 group-hover:opacity-100'}
                                `}>
                                    <div className={`
                                        text-xs font-bold font-tech uppercase tracking-widest
                                        ${isActive ? 'text-white' : 'text-gray-400'}
                                    `}>
                                        {agent.name}
                                    </div>
                                    <div className="text-[9px] text-gray-600 font-mono">
                                        {agent.role.split(' ')[0]}
                                    </div>
                                </div>

                                {/* Status Badge */}
                                {isCompleted && !isActive && (
                                    <div className="absolute -top-1 -right-1 w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center text-[10px] text-black font-bold">
                                        ✓
                                    </div>
                                )}
                            </div>

                            {/* Expanded Info Panel */}
                            {isHovered && !isActive && (
                                <div className="absolute left-full ml-4 top-1/2 -translate-y-1/2 z-20 w-48 animate-fade-in">
                                    <div className="bg-black/90 border border-white/10 rounded-xl p-3 backdrop-blur-xl shadow-2xl">
                                        <div className="text-xs font-bold text-white mb-1">{agent.name}</div>
                                        <div className="text-[10px] text-gray-400">{agent.description}</div>
                                        <div className="mt-2 pt-2 border-t border-white/10 text-[9px] text-gray-500 font-mono">
                                            {agent.model}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Background Noise */}
            <div className="absolute inset-0 pointer-events-none opacity-[0.02] bg-[url('https://grainy-gradients.vercel.app/noise.svg')]"></div>
        </div>
    );
};

export default WorkflowVisualizer;
