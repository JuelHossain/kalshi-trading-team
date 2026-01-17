import React from 'react';

const VaultGauge: React.FC<{compact?: boolean}> = ({ compact = false }) => {
  const principal = 300;
  const currentProfit = 105;
  const lockThreshold = 50;
  const isLocked = currentProfit >= lockThreshold;
  const total = principal + currentProfit;

  if (compact) {
      return (
          <div className="w-full">
              <div className="flex justify-between items-center mb-1.5 px-1">
                  <span className="text-[8px] text-gray-500 uppercase tracking-widest font-mono">Vault</span>
                  <span className="text-[10px] font-bold text-white font-mono">${total.toFixed(0)}</span>
              </div>
              <div className="w-full h-1.5 bg-gray-800/50 rounded-full overflow-hidden flex">
                  <div className="h-full bg-gray-600/50" style={{ width: `${(principal/total)*100}%` }}></div>
                  <div className="h-full bg-emerald-500 shadow-[0_0_5px_rgba(16,185,129,0.5)]" style={{ width: `${(currentProfit/total)*100}%` }}></div>
              </div>
          </div>
      );
  }

  return (
    <div className="bg-white/5 rounded-2xl p-5 border border-white/5 relative overflow-hidden group">
        <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 blur-[50px] rounded-full pointer-events-none group-hover:bg-emerald-500/10 transition-colors"></div>
        
        <div className="flex justify-between items-center mb-4 relative z-10">
            <span className="text-[10px] text-emerald-500/80 uppercase font-mono tracking-widest flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></span>
                Recursive Vault
            </span>
            {isLocked && (
                <span className="text-[9px] text-amber-400 font-bold uppercase px-2 py-0.5 rounded-full bg-amber-400/10 border border-amber-400/20 shadow-[0_0_10px_rgba(251,191,36,0.2)]">
                    Locked
                </span>
            )}
        </div>
        
        <div className="flex items-baseline gap-2 mb-4 relative z-10">
            <span className="text-3xl font-black text-white tracking-tighter font-tech">${total.toFixed(2)}</span>
            <span className="text-xs text-emerald-400 font-mono">+{((currentProfit/principal)*100).toFixed(1)}%</span>
        </div>

        {/* Soft Gauge Bar */}
        <div className="w-full h-3 bg-black/40 rounded-full overflow-hidden flex relative shadow-inner">
            {/* Principal Bar */}
            <div 
                className="h-full bg-gray-700/50 relative backdrop-blur-sm" 
                style={{ width: `${(principal/total)*100}%` }}
            >
                {isLocked && (
                    <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/diagonal-stripes.png')] opacity-10"></div>
                )}
            </div>
            
            {/* Profit Bar */}
            <div 
                className="h-full bg-gradient-to-r from-emerald-600 to-emerald-400 relative shadow-[0_0_15px_rgba(16,185,129,0.4)]" 
                style={{ width: `${(currentProfit/total)*100}%` }}
            >
                <div className="absolute top-0 right-0 h-full w-1 bg-white/50 blur-[1px]"></div>
            </div>
        </div>
        
        <div className="flex justify-between mt-3 text-[9px] font-mono uppercase tracking-wide relative z-10 opacity-70">
            <div>
                Principal <span className="text-gray-300 ml-1">${principal}</span>
            </div>
            <div>
                House <span className="text-emerald-300 ml-1">${currentProfit}</span>
            </div>
        </div>
    </div>
  );
};

export default VaultGauge;