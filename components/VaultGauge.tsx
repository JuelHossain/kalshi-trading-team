import React from 'react';

const VaultGauge: React.FC = () => {
  const principal = 300;
  const currentProfit = 105;
  const lockThreshold = 50;
  const isLocked = currentProfit >= lockThreshold;
  
  const total = principal + currentProfit;

  return (
    <div className="bg-black/40 rounded-[2px] p-4 border border-gray-800 relative group overflow-hidden">
        {/* Subtle screw heads in corners */}
        <div className="absolute top-1 left-1 w-1 h-1 bg-gray-700 rounded-full"></div>
        <div className="absolute top-1 right-1 w-1 h-1 bg-gray-700 rounded-full"></div>
        <div className="absolute bottom-1 left-1 w-1 h-1 bg-gray-700 rounded-full"></div>
        <div className="absolute bottom-1 right-1 w-1 h-1 bg-gray-700 rounded-full"></div>

        <div className="flex justify-between items-center mb-2">
            <span className="text-[10px] text-gray-500 uppercase font-mono tracking-widest">Recursive Vault</span>
            {isLocked && (
                <span className="flex items-center gap-1 text-[9px] text-amber-400 font-bold uppercase border border-amber-400/30 px-1.5 py-0.5 rounded-sm bg-amber-400/10 animate-pulse">
                    Locked
                </span>
            )}
        </div>
        
        <div className="flex justify-between items-end mb-2">
            <span className="text-2xl font-black text-white tracking-tighter font-tech">${total.toFixed(2)}</span>
            <span className="text-xs text-emerald-500 font-mono mb-1">+{((currentProfit/principal)*100).toFixed(1)}%</span>
        </div>

        {/* Gauge Bar */}
        <div className="w-full h-2 bg-gray-800 rounded-sm overflow-hidden flex relative box-shadow-inner">
            {/* Principal Bar */}
            <div 
                className="h-full bg-gray-600 relative group transition-all duration-1000" 
                style={{ width: `${(principal/total)*100}%` }}
            >
                {isLocked && (
                    <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/diagonal-stripes.png')] opacity-30"></div>
                )}
            </div>
            
            {/* Profit Bar */}
            <div 
                className="h-full bg-emerald-500 relative transition-all duration-1000" 
                style={{ width: `${(currentProfit/total)*100}%` }}
            >
                <div className="absolute top-0 right-0 bottom-0 w-[2px] bg-white/80 shadow-[0_0_10px_white]"></div>
            </div>
        </div>
        
        <div className="flex justify-between mt-2 text-[9px] font-mono uppercase tracking-wide">
            <div className="text-gray-600">
                Principal: <span className={isLocked ? "text-amber-500" : "text-gray-400"}>${principal}</span>
            </div>
            <div className="text-gray-600">
                House: <span className="text-emerald-400">${currentProfit}</span>
            </div>
        </div>
    </div>
  );
};

export default VaultGauge;
