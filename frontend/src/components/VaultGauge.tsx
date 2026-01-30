import React from 'react';
import { motion } from 'framer-motion';

interface VaultState {
  total?: number;
  locked?: boolean;
}

interface VaultGaugeProps {
  vault?: VaultState;
  compact?: boolean;
}

const VaultGauge: React.FC<VaultGaugeProps> = ({ vault, compact = false }) => {
  const total = vault?.total ?? 0;
  const isLocked = vault?.locked ?? false;

  if (compact) {
    return (
      <div className="flex items-center gap-2 text-[10px] font-mono text-gray-400">
        <motion.div
          className={`w-2 h-2 rounded-full ${isLocked ? 'bg-red-500' : 'bg-emerald-500'}`}
          animate={isLocked ? {} : { scale: [1, 1.2, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
        <span>${total.toFixed(2)}</span>
      </div>
    );
  }

  return (
    <div className="bg-white/5 rounded-xl p-4 border border-white/10">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">Vault</span>
        <motion.div
          className={`w-2 h-2 rounded-full ${isLocked ? 'bg-red-500' : 'bg-emerald-500'}`}
          animate={isLocked ? {} : { scale: [1, 1.2, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
      </div>
      <div className="text-lg font-mono font-bold text-white">
        ${total.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
      </div>
      <div className="text-[9px] text-gray-500 mt-1">{isLocked ? 'Locked' : 'Active'}</div>
    </div>
  );
};

export default VaultGauge;
