import React from 'react';
import VaultGauge from './VaultGauge';

interface SidebarProps {
    activeTab: string;
    setActiveTab: (tab: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab }) => {
    const menuItems = [
        { id: 'dashboard', label: 'Command', icon: '⚡' },
        { id: 'agents', label: 'Agents', icon: '🕵️‍♂️' },
        { id: 'analyst', label: 'Analyst', icon: '🧠' },
        { id: 'logs', label: 'Trace', icon: '📜' },
        { id: 'about', label: 'Mission', icon: 'ℹ️' },
        { id: 'settings', label: 'Config', icon: '⚙️' },
    ];

    return (
        // Outer container keeps the 'flow' space of 16px (w-16) constant so dashboard doesn't jump
        <div className="relative w-16 h-full z-50">
            {/* Inner container expands absolutely over the dashboard */}
            <div className="absolute top-0 left-0 h-full w-16 hover:w-64 transition-all duration-500 ease-[cubic-bezier(0.23,1,0.32,1)] group">
                <div className="h-full glass-panel rounded-l-none rounded-r-3xl flex flex-col py-8 organic-glow relative overflow-hidden bg-black/90 backdrop-blur-xl border-l-0 border-white/10 shadow-2xl">

                    {/* Animated Background Mesh */}
                    <div className="absolute inset-0 opacity-20 pointer-events-none bg-[radial-gradient(circle_at_50%_50%,rgba(16,185,129,0.1),transparent_70%)] group-hover:opacity-40 transition-opacity duration-500"></div>

                    {/* Logo/Brand Icon */}
                    <div className="mb-10 px-3 relative flex items-center gap-4 overflow-hidden whitespace-nowrap">
                        <div className="w-10 h-10 shrink-0 rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-700 flex items-center justify-center shadow-[0_0_20px_rgba(16,185,129,0.4)] z-10">
                            <span className="text-black font-black font-tech text-xl">K</span>
                        </div>
                        <div className="opacity-0 group-hover:opacity-100 transition-all duration-500 transform translate-x-[-20px] group-hover:translate-x-0">
                            <h1 className="font-tech text-xl text-white font-bold tracking-widest uppercase">Kalshi<span className="text-emerald-500">Alpha</span></h1>
                            <div className="text-[9px] text-gray-400 font-mono tracking-[0.2em]">SENTIENT V2</div>
                        </div>
                        <div className="absolute bottom-1 left-7 w-2 h-2 bg-emerald-400 rounded-full animate-ping z-20 pointer-events-none"></div>
                    </div>

                    {/* Menu Items */}
                    <div className="flex-1 flex flex-col gap-2 w-full px-2">
                        {menuItems.map(item => (
                            <button
                                key={item.id}
                                onClick={() => setActiveTab(item.id)}
                                className={`
                    relative flex items-center h-12 rounded-xl transition-all duration-300 overflow-hidden group/btn
                    ${activeTab === item.id
                                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.1)]'
                                        : 'text-gray-500 hover:bg-white/5 hover:text-gray-200 border border-transparent'}
                `}
                            >
                                <div className="w-12 h-12 flex items-center justify-center shrink-0 text-lg relative z-10">
                                    {item.icon}
                                </div>

                                <span className={`
                    absolute left-14 whitespace-nowrap text-sm font-mono tracking-widest uppercase opacity-0 group-hover:opacity-100 transition-all duration-500 transform translate-x-4 group-hover:translate-x-0
                    ${activeTab === item.id ? 'font-bold' : ''}
                `}>
                                    {item.label}
                                </span>

                                {activeTab === item.id && (
                                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-emerald-500 rounded-r-full shadow-[0_0_10px_#34d399]"></div>
                                )}
                            </button>
                        ))}
                    </div>

                    {/* Vault Gauge Compact - Auto Expands */}
                    <div className="mt-auto px-2 w-full overflow-hidden">
                        <div className="opacity-0 group-hover:opacity-100 transition-all duration-700 delay-100">
                            <VaultGauge compact={false} />
                        </div>
                        <div className="absolute bottom-8 left-0 w-16 flex justify-center group-hover:opacity-0 transition-opacity duration-300 pointer-events-none">
                            <span className="text-2xl animate-pulse">🔒</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Sidebar;