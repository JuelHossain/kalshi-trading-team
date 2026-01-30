import React, { memo, useMemo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { motion } from 'framer-motion';

interface SynapseNodeData {
  name: string;
  status: 'idle' | 'active' | 'processing';
  color: string;
  queueMetrics: {
    opportunities: number;
    executions: number;
    totalProcessed: number;
  };
  lastAction: string;
}

const SynapseNode = memo(({ data, selected }: NodeProps<SynapseNodeData>) => {
  const { name, status, color, queueMetrics, lastAction } = data;

  const isActive = status === 'active' || status === 'processing';
  const totalQueued = queueMetrics.opportunities + queueMetrics.executions;

  // Pulse animation for active state
  const pulseVariants = {
    idle: {
      scale: 1,
      opacity: 0.3,
      transition: { duration: 0.5 },
    },
    active: {
      scale: [1, 1.2, 1],
      opacity: [0.5, 0.8, 0.5],
      transition: {
        duration: 1.5,
        repeat: Infinity,
        ease: 'easeInOut',
      },
    },
  };

  // Rotating ring animation
  const ringVariants = {
    animate: {
      rotate: 360,
      transition: {
        duration: 8,
        repeat: Infinity,
        ease: 'linear',
      },
    },
  };

  // Counter animation
  const counterVariants = {
    initial: { scale: 0.8, opacity: 0 },
    animate: { scale: 1, opacity: 1 },
    transition: { type: 'spring', stiffness: 500, damping: 30 },
  };

  return (
    <div className="relative">
      {/* Outer Glow Effect */}
      <motion.div
        className="absolute inset-0 rounded-full pointer-events-none"
        style={{
          background: `radial-gradient(circle, ${color}30 0%, transparent 70%)`,
          transform: 'scale(1.5)',
        }}
        variants={pulseVariants}
        animate={isActive ? 'active' : 'idle'}
      />

      {/* Rotating Data Rings */}
      {isActive && (
        <>
          <motion.div
            className="absolute inset-0 rounded-full border-2 border-dashed pointer-events-none"
            style={{
              borderColor: `${color}40`,
              transform: 'scale(1.3)',
            }}
            variants={ringVariants}
            animate="animate"
          />
          <motion.div
            className="absolute inset-0 rounded-full border border-dotted pointer-events-none"
            style={{
              borderColor: `${color}30`,
              transform: 'scale(1.6)',
            }}
            variants={ringVariants}
            animate="animate"
            transition={{ duration: 12, repeat: Infinity, ease: 'linear', direction: 'reverse' }}
          />
        </>
      )}

      {/* Main Synapse Container */}
      <motion.div
        className="relative p-5 rounded-full border-2 bg-black/95 backdrop-blur-md min-w-[180px] min-h-[180px] flex flex-col items-center justify-center cursor-pointer"
        style={{
          borderColor: color,
          boxShadow: isActive ? `0 0 40px ${color}50, inset 0 0 20px ${color}20` : 'none',
        }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        {/* Central Database Icon */}
        <motion.div
          className="text-4xl mb-2"
          style={{ color }}
          animate={
            isActive
              ? {
                  scale: [1, 1.1, 1],
                  transition: { duration: 2, repeat: Infinity },
                }
              : {}
          }
        >
          🗄️
        </motion.div>

        {/* Synapse Label */}
        <h3 className="font-tech font-bold text-white uppercase tracking-wider text-sm mb-1">
          {name}
        </h3>
        <p className="text-[9px] text-gray-400 uppercase tracking-wide mb-3">SQLite Persistence</p>

        {/* Status Indicator */}
        <motion.div
          className="px-3 py-1 rounded-full text-[9px] font-bold uppercase tracking-wider mb-3"
          style={{
            backgroundColor: `${color}20`,
            color: color,
            border: `1px solid ${color}40`,
          }}
        >
          {status}
        </motion.div>

        {/* Queue Metrics Grid */}
        <div className="grid grid-cols-2 gap-2 w-full px-2">
          {/* Opportunities Queue */}
          <motion.div
            className="bg-white/5 rounded-lg p-2 text-center"
            variants={counterVariants}
            key={queueMetrics.opportunities}
          >
            <div className="text-[8px] text-gray-500 uppercase tracking-wide mb-1">Opp Queue</div>
            <motion.div
              className="text-lg font-mono font-bold"
              style={{ color: '#06b6d4' }}
              initial={{ scale: 0.5 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 500, damping: 30 }}
            >
              {queueMetrics.opportunities}
            </motion.div>
          </motion.div>

          {/* Executions Queue */}
          <motion.div
            className="bg-white/5 rounded-lg p-2 text-center"
            variants={counterVariants}
            key={queueMetrics.executions}
          >
            <div className="text-[8px] text-gray-500 uppercase tracking-wide mb-1">Exec Queue</div>
            <motion.div
              className="text-lg font-mono font-bold"
              style={{ color: '#10b981' }}
              initial={{ scale: 0.5 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 500, damping: 30 }}
            >
              {queueMetrics.executions}
            </motion.div>
          </motion.div>
        </div>

        {/* Total Processed */}
        <div className="mt-2 text-center">
          <span className="text-[8px] text-gray-500 uppercase tracking-wide">
            Total Processed:{' '}
          </span>
          <motion.span
            className="text-[10px] font-mono font-bold text-white"
            key={queueMetrics.totalProcessed}
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {queueMetrics.totalProcessed.toLocaleString()}
          </motion.span>
        </div>

        {/* Activity Indicator */}
        {isActive && (
          <motion.div
            className="absolute inset-0 rounded-full pointer-events-none"
            style={{
              background: `conic-gradient(from 0deg, transparent, ${color}20, transparent)`,
            }}
            animate={{ rotate: 360 }}
            transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
          />
        )}

        {/* Selected State */}
        {selected && (
          <motion.div
            className="absolute inset-0 rounded-full pointer-events-none border-2 border-white"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          />
        )}
      </motion.div>

      {/* Connection Handles - Positioned around the circle for hub-spoke layout */}
      <Handle
        type="target"
        position={Position.Top}
        id="soul-in"
        style={{
          background: '#f59e0b',
          width: 10,
          height: 10,
          border: '2px solid #f59e0b',
        }}
      />
      <Handle
        type="source"
        position={Position.Top}
        id="soul-out"
        style={{
          background: '#f59e0b',
          width: 10,
          height: 10,
          border: '2px solid #f59e0b',
        }}
      />

      <Handle
        type="target"
        position={Position.Left}
        id="senses-in"
        style={{
          background: '#06b6d4',
          width: 10,
          height: 10,
          border: '2px solid #06b6d4',
        }}
      />
      <Handle
        type="source"
        position={Position.Left}
        id="senses-out"
        style={{
          background: '#06b6d4',
          width: 10,
          height: 10,
          border: '2px solid #06b6d4',
        }}
      />

      <Handle
        type="target"
        position={Position.Right}
        id="brain-in"
        style={{
          background: '#a855f7',
          width: 10,
          height: 10,
          border: '2px solid #a855f7',
        }}
      />
      <Handle
        type="source"
        position={Position.Right}
        id="brain-out"
        style={{
          background: '#a855f7',
          width: 10,
          height: 10,
          border: '2px solid #a855f7',
        }}
      />

      <Handle
        type="target"
        position={Position.Bottom}
        id="hand-in"
        style={{
          background: '#10b981',
          width: 10,
          height: 10,
          border: '2px solid #10b981',
        }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="hand-out"
        style={{
          background: '#10b981',
          width: 10,
          height: 10,
          border: '2px solid #10b981',
        }}
      />
    </div>
  );
});

SynapseNode.displayName = 'SynapseNode';

export default SynapseNode;
