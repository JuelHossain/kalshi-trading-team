import React from 'react';
import { motion } from 'framer-motion';

interface SimulationState {
  confidence?: number;
  variance?: number;
  veto?: boolean;
}

interface SimulationResultsProps {
  simulation?: SimulationState;
}

const SimulationResults: React.FC<SimulationResultsProps> = ({ simulation }) => {
  const confidence = simulation?.confidence ?? 0;
  const variance = simulation?.variance ?? 0;
  const veto = simulation?.veto ?? false;

  return (
    <div className="bg-white/5 rounded-xl p-4 border border-white/10 h-full">
      <div className="flex items-center justify-between mb-4">
        <span className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">
          Simulation
        </span>
        {veto ? (
          <span className="px-2 py-0.5 bg-red-500/20 text-red-400 rounded text-[9px] font-bold uppercase">
            VETO
          </span>
        ) : (
          <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 rounded text-[9px] font-bold uppercase">
            PASS
          </span>
        )}
      </div>

      <div className="space-y-4">
        {/* Confidence Bar */}
        <div>
          <div className="flex justify-between text-[10px] text-gray-400 mb-1">
            <span>Confidence</span>
            <span>{(confidence * 100).toFixed(1)}%</span>
          </div>
          <div className="h-2 bg-white/10 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-purple-500 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${confidence * 100}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
        </div>

        {/* Variance Bar */}
        <div>
          <div className="flex justify-between text-[10px] text-gray-400 mb-1">
            <span>Variance</span>
            <span>{(variance * 100).toFixed(1)}%</span>
          </div>
          <div className="h-2 bg-white/10 rounded-full overflow-hidden">
            <motion.div
              className={`h-full rounded-full ${variance > 0.25 ? 'bg-red-500' : 'bg-cyan-500'}`}
              initial={{ width: 0 }}
              animate={{ width: `${variance * 100}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
        </div>

        {veto && (
          <motion.div
            className="p-2 bg-red-500/10 border border-red-500/20 rounded text-[9px] text-red-400"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            Heuristic veto triggered: Variance &gt; 0.25
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default SimulationResults;
