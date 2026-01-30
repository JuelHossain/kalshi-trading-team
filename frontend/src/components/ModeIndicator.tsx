import React from 'react';

interface ModeIndicatorProps {
  mode: 'demo' | 'production';
  isProduction: boolean;
}

/**
 * ModeIndicator displays the current authentication mode (demo or production)
 * with appropriate styling and animations.
 */
const ModeIndicator: React.FC<ModeIndicatorProps> = ({ mode, isProduction }) => {
  const isDemo = !isProduction && mode === 'demo';

  return (
    <div
      data-testid="mode-indicator"
      className={`
        inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider
        transition-all duration-300
        ${
          isDemo
            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
            : 'bg-red-500/10 text-red-400 border border-red-500/20 animate-pulse'
        }
      `}
    >
      <span
        data-testid="mode-dot"
        className={`
          w-2 h-2 rounded-full
          ${isDemo ? 'bg-emerald-400' : 'bg-red-400'}
        `}
      />
      <span data-testid="mode-label">{isDemo ? 'Demo Mode' : 'Production Mode'}</span>
      {isProduction && (
        <span data-testid="production-warning" className="text-red-300">
          (Live Trading)
        </span>
      )}
    </div>
  );
};

export default ModeIndicator;
