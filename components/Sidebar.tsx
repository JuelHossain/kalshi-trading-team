import React from 'react';
import VaultGauge from './VaultGauge';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab }) => {
  const menuItems = [
    { id: 'dashboard', label: 'Command Center', icon: '⚡' },
    { id: 'analyst', label: 'Agent 4: Analyst', icon: '🧠' },
    { id: 'logs', label: 'System Logs', icon: '📜' },
    { id: 'settings', label: 'Configuration', icon: '⚙️' },
  ];

  return (
    <div className="w-64 h-full shrink-0 p-4 bg-[#020202]">
      <div className="h-full cyber-card rounded-sm flex flex-col cyber-glow">
        {/* Holographic Corners */}
        <div className="corner corner-tl"></div>
        <div className="corner corner-tr"></div>
        <div className="corner corner-br"></div>
        <div className="corner corner-bl"></div>

        <div className="p-6 border-b border-gray-800/50 bg-black/40">
          <h1 className="font-black text-xl tracking-tighter text-white">
            KALSHI<span className="text-emerald-500">SENTIENT</span>
          </h1>
          <div className="text-[10px] text-gray-500 font-mono mt-1 flex justify-between">
            <span>ARCH: V1.2</span>
            <span className="animate-pulse text-emerald-900">●</span>
          </div>
        </div>
        
        <div className="flex-1 py-6 px-3 space-y-2">
          {menuItems.map(item => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-[2px] text-sm font-tech tracking-wide transition-all uppercase border-l-2 ${
                activeTab === item.id 
                  ? 'bg-emerald-900/20 text-emerald-400 border-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.1)]' 
                  : 'text-gray-500 hover:text-gray-300 hover:bg-white/5 border-transparent'
              }`}
            >
              <span className="opacity-70">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </div>

        <div className="p-4 border-t border-gray-800/50 bg-black/20">
          <VaultGauge />
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
