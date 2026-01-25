import React from 'react';
import { SimulationState } from '@shared/types';

interface SimulationResultsProps {
  simulation?: SimulationState;
}

const SimulationResults: React.FC<SimulationResultsProps> = ({ simulation }) => {
  if (!simulation) {
    return (
      <div className="bg-white/5 rounded-2xl p-5 border border-white/5 flex items-center justify-center opacity-40">
        <span className="text-[10px] font-mono tracking-widest uppercase">
          Awaiting Monte Carlo Data...
        </span>
      </div>
    );
  }

  return (
    <div className="bg-white/5 rounded-2xl p-5 border border-white/5 relative overflow-hidden group">
      <div className="flex justify-between items-center mb-4">
        <span className="text-[10px] text-blue-400/80 uppercase font-mono tracking-widest flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></span>
          Sim Scientist Results
        </span>
        {simulation.veto && (
          <span className="text-[9px] text-red-400 font-bold uppercase px-2 py-0.5 rounded-full bg-red-400/10 border border-red-400/20">
            VETO TRIGGERED
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-[8px] text-gray-500 uppercase tracking-widest mb-1">Win Rate</div>
          <div
            className={`text-2xl font-black font-tech ${simulation.winRate >= 58 ? 'text-emerald-400' : 'text-red-400'}`}
          >
            {((simulation.winRate ?? 0) * 1).toFixed(1)}%
          </div>
        </div>
        <div>
          <div className="text-[8px] text-gray-500 uppercase tracking-widest mb-1">EV Score</div>
          <div className="text-2xl font-black font-tech text-white">
            {(simulation.evScore ?? 0).toFixed(3)}
          </div>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-white/5 flex justify-between items-center">
        <span className="text-[8px] text-gray-600 font-mono uppercase">
          Iterations: {simulation.iterations}k
        </span>
        <span className="text-[8px] text-gray-600 font-mono uppercase">
          Variance: {simulation.variance}%
        </span>
      </div>
    </div>
  );
};

export default SimulationResults;
