import React, { useState } from 'react';
import { Agent, AgentStatus } from '@shared/types';
import { AGENTS } from '@shared/constants';

interface AgentsPageProps {
    onTestAgent: (id: number) => void;
    onSelectAgent: (id: number) => void;
    activeAgentId: number | null;
    viewedAgentId: number | null;
}

const AgentsPage: React.FC<AgentsPageProps> = ({ onTestAgent, onSelectAgent, activeAgentId, viewedAgentId }) => {
    const [filter, setFilter] = useState<'ALL' | 'WORKING' | 'IDLE'>('ALL');

    const filteredAgents = AGENTS.filter(a => {
        if (a.hidden) return false; // Hide The Fixer unless error
        if (filter === 'ALL') return true;
        if (filter === 'WORKING') return a.status === AgentStatus.WORKING;
        return a.status !== AgentStatus.WORKING;
    });

    return (
        <div className="h-full flex flex-col gap-6 overflow-hidden">

            {/* Header / Filter */}
            <div className="flex items-center justify-between shrink-0 glass-panel p-4 rounded-2xl organic-glow">
                <h2 className="text-xl font-bold font-tech uppercase tracking-widest text-emerald-400 flex items-center gap-3">
                    <span className="text-2xl">🕵️‍♂️</span> Squad Roster
                </h2>

                <div className="flex bg-black/40 rounded-xl p-1 border border-white/5">
                    {['ALL', 'WORKING', 'IDLE'].map((f) => (
                        <button
                            key={f}
                            onClick={() => setFilter(f as any)}
                            className={`px-4 py-1.5 rounded-lg text-[10px] font-mono uppercase tracking-wider transition-all
                        ${filter === f
                                    ? 'bg-emerald-500 text-black font-bold shadow-[0_0_10px_rgba(16,185,129,0.4)]'
                                    : 'text-gray-500 hover:text-gray-300'}
                    `}
                        >
                            {f}
                        </button>
                    ))}
                </div>
            </div>

            {/* Grid */}
            <div className="flex-1 overflow-y-auto pr-2 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pb-20">
                {filteredAgents.map(agent => (
                    <div
                        key={agent.id}
                        onClick={() => onSelectAgent(agent.id)}
                        className={`
                    relative group p-5 rounded-2xl border transition-all duration-300 cursor-pointer overflow-hidden
                    ${viewedAgentId === agent.id
                                ? 'bg-emerald-900/20 border-emerald-500 shadow-[0_0_30px_rgba(16,185,129,0.2)] ring-1 ring-emerald-400'
                                : 'bg-black/40 border-white/5 hover:border-emerald-500/30 hover:bg-white/5'}
                `}
                    >
                        {/* Active Indicator Line */}
                        <div className={`absolute left-0 top-0 bottom-0 w-1 transition-colors duration-300 ${activeAgentId === agent.id ? 'bg-emerald-500 animate-pulse' : 'bg-transparent group-hover:bg-emerald-500/30'}`}></div>

                        <div className="flex justify-between items-start mb-4">
                            <div className="flex items-center gap-3">
                                <div className={`
                            w-10 h-10 rounded-xl flex items-center justify-center text-lg shadow-lg border border-white/5
                            ${viewedAgentId === agent.id ? 'bg-emerald-500 text-black' : 'bg-white/5 text-gray-400'}
                        `}>
                                    {/* Simple Icon Mapping or Generic */}
                                    <span className="font-bold font-mono">{agent.id}</span>
                                </div>
                                <div>
                                    <h3 className={`font-bold uppercase tracking-wider text-sm ${viewedAgentId === agent.id ? 'text-white' : 'text-gray-300'}`}>
                                        {agent.name}
                                    </h3>
                                    <span className="text-[10px] font-mono text-emerald-500/60 uppercase tracking-widest">{agent.role}</span>
                                </div>
                            </div>

                            {/* Status Badge */}
                            <div className={`
                        px-2 py-0.5 rounded-md text-[9px] font-mono uppercase border
                        ${activeAgentId === agent.id
                                    ? 'bg-emerald-500 text-black border-emerald-400 animate-pulse'
                                    : 'bg-gray-800 text-gray-500 border-gray-700'}
                    `}>
                                {activeAgentId === agent.id ? 'RUNNING' : agent.status}
                            </div>
                        </div>

                        <p className="text-xs text-gray-500 leading-relaxed mb-4 h-10 line-clamp-2">
                            {agent.description}
                        </p>

                        {/* Tech Specs */}
                        <div className="grid grid-cols-2 gap-2 text-[10px] font-mono bg-black/30 rounded-lg p-2 border border-white/5 mb-4">
                            <div className="text-gray-500">Model:</div>
                            <div className="text-right text-emerald-400">{agent.model}</div>
                            <div className="text-gray-500">Last Act:</div>
                            <div className="text-right text-gray-300 truncate">{agent.lastAction}</div>
                        </div>

                        {/* Action Button */}
                        <button
                            onClick={(e) => {
                                e.stopPropagation(); // Prevent card select when clicking button
                                onTestAgent(agent.id);
                                onSelectAgent(agent.id); // Also select it
                            }}
                            className={`
                        w-full py-2 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all
                        ${activeAgentId === agent.id
                                    ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30 cursor-wait'
                                    : 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 hover:bg-emerald-500 hover:text-black hover:shadow-[0_0_15px_rgba(16,185,129,0.4)]'}
                    `}
                        >
                            {activeAgentId === agent.id ? 'DIAGNOSING...' : 'RUN SELF-TEST'}
                        </button>

                    </div>
                ))}
            </div>
        </div>
    );
};

export default AgentsPage;
