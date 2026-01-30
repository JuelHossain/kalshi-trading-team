import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { DataFlowTransition } from '@/store/slices/agentSlice';
import { ArrowRight, Activity } from 'lucide-react';

interface WorkflowTimelineProps {
  transitions: DataFlowTransition[];
  className?: string;
}

const agentColors: Record<number, string> = {
  1: '#f59e0b', // SOUL - Amber
  2: '#06b6d4', // SENSES - Cyan
  3: '#a855f7', // BRAIN - Purple
  4: '#10b981', // HAND - Emerald
};

const agentNames: Record<number, string> = {
  1: 'SOUL',
  2: 'SENSES',
  3: 'BRAIN',
  4: 'HAND',
};

const flowTypeLabels: Record<string, { label: string; color: string }> = {
  authorization: { label: 'AUTH', color: '#f59e0b' },
  opportunity: { label: 'OPPORTUNITY', color: '#06b6d4' },
  decision: { label: 'DECISION', color: '#a855f7' },
  execution: { label: 'EXECUTION', color: '#10b981' },
};

const WorkflowTimeline: React.FC<WorkflowTimelineProps> = ({ transitions, className }) => {
  // Get last 10 transitions
  const recentTransitions = transitions.slice(-10).reverse();

  return (
    <motion.div
      className={`bg-black/80 backdrop-blur-md border border-white/10 rounded-xl p-4 ${className || ''}`}
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.3 }}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-[10px] font-tech font-bold text-gray-400 uppercase tracking-wider">
          Transition Timeline
        </h3>
        <div className="flex items-center gap-2">
          <Activity className="w-3 h-3 text-gray-500" />
          <span className="text-[9px] font-mono text-gray-500">{transitions.length} total</span>
        </div>
      </div>

      <div className="space-y-2 max-h-[300px] overflow-y-auto scrollbar-thin">
        <AnimatePresence mode="popLayout">
          {recentTransitions.length === 0 ? (
            <motion.div
              className="text-center py-8 text-gray-600"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <div className="text-[10px] font-mono uppercase tracking-wider">
                No transitions yet
              </div>
              <div className="text-[9px] mt-1">Initiate a cycle to see agent workflow</div>
            </motion.div>
          ) : (
            recentTransitions.map((transition, index) => {
              const fromColor = agentColors[transition.fromAgent] || '#666';
              const toColor = agentColors[transition.toAgent] || '#666';
              const flowType = flowTypeLabels[transition.flowType] || {
                label: 'DATA',
                color: '#666',
              };
              const isActive = transition.active;

              return (
                <motion.div
                  key={transition.id}
                  layout
                  initial={{ opacity: 0, x: -20, scale: 0.9 }}
                  animate={{ opacity: 1, x: 0, scale: 1 }}
                  exit={{ opacity: 0, x: 20, scale: 0.9 }}
                  transition={{ delay: index * 0.05 }}
                  className={`relative flex items-center gap-3 p-2.5 rounded-lg border transition-all ${
                    isActive
                      ? 'bg-white/5 border-white/20'
                      : 'bg-transparent border-white/5 hover:border-white/10'
                  }`}
                >
                  {/* Active indicator */}
                  {isActive && (
                    <motion.div
                      className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-8 rounded-full"
                      style={{ backgroundColor: flowType.color }}
                      layoutId="activeIndicator"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                    />
                  )}

                  {/* From Agent */}
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: fromColor }} />
                    <span
                      className="text-[10px] font-bold uppercase tracking-wider"
                      style={{ color: fromColor }}
                    >
                      {agentNames[transition.fromAgent]}
                    </span>
                  </div>

                  {/* Arrow */}
                  <div className="flex items-center">
                    <ArrowRight
                      className="w-3 h-3 text-gray-600"
                      style={{ color: isActive ? flowType.color : undefined }}
                    />
                  </div>

                  {/* To Agent */}
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: toColor }} />
                    <span
                      className="text-[10px] font-bold uppercase tracking-wider"
                      style={{ color: toColor }}
                    >
                      {agentNames[transition.toAgent]}
                    </span>
                  </div>

                  {/* Flow Type Badge */}
                  <div className="ml-auto">
                    <span
                      className="px-2 py-0.5 rounded text-[8px] font-bold uppercase tracking-wider border"
                      style={{
                        backgroundColor: `${flowType.color}15`,
                        color: flowType.color,
                        borderColor: `${flowType.color}30`,
                      }}
                    >
                      {flowType.label}
                    </span>
                  </div>

                  {/* Timestamp */}
                  <div className="text-[8px] font-mono text-gray-600">
                    {new Date(transition.timestamp).toLocaleTimeString('en-US', {
                      hour12: false,
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                    })}
                  </div>
                </motion.div>
              );
            })
          )}
        </AnimatePresence>
      </div>

      {/* Legend */}
      <div className="mt-4 pt-4 border-t border-white/5">
        <div className="flex flex-wrap gap-2">
          {Object.entries(flowTypeLabels).map(([type, { label, color }]) => (
            <div key={type} className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />
              <span className="text-[8px] text-gray-500 uppercase tracking-wider">{label}</span>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
};

export default WorkflowTimeline;
