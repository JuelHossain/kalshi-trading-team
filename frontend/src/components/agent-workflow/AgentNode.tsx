import React, { memo, useMemo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { motion } from 'framer-motion';
import { AgentState } from '@/store/slices/agentSlice';

interface AgentNodeData extends AgentState {}

const AgentNode = memo(({ data, selected }: NodeProps<AgentNodeData>) => {
  const { agentId, name, role, status, color, metrics, lastAction } = data;

  // Determine animation variants based on status
  const isActive = status === 'active' || status === 'processing';
  const isError = status === 'error';
  const isVeto = status === 'veto';

  // Get agent icon
  const getAgentIcon = (name: string): string => {
    switch (name) {
      case 'SOUL':
        return '👁️';
      case 'SENSES':
        return '📡';
      case 'BRAIN':
        return '🧠';
      case 'HAND':
        return '✋';
      default:
        return '⚡';
    }
  };

  // Status-specific glow colors
  const glowColor = useMemo(() => {
    if (isError) return '#ef4444';
    if (isVeto) return '#f59e0b';
    return color;
  }, [isError, isVeto, color]);

  // Animation variants for different states
  const containerVariants = {
    idle: {
      scale: 1,
      boxShadow: '0 0 0px rgba(0,0,0,0)',
      transition: { duration: 0.3 },
    },
    active: {
      scale: [1, 1.02, 1],
      boxShadow: `0 0 30px ${glowColor}40, 0 0 60px ${glowColor}20`,
      transition: {
        duration: 2,
        repeat: Infinity,
        ease: 'easeInOut',
      },
    },
    error: {
      scale: [1, 1.05, 1],
      boxShadow: '0 0 30px rgba(239,68,68,0.6), 0 0 60px rgba(239,68,68,0.3)',
      transition: {
        duration: 0.5,
        repeat: Infinity,
        ease: 'easeInOut',
      },
    },
    veto: {
      scale: [1, 1.03, 1],
      boxShadow: '0 0 30px rgba(245,158,11,0.6), 0 0 60px rgba(245,158,11,0.3)',
      transition: {
        duration: 1,
        repeat: Infinity,
        ease: 'easeInOut',
      },
    },
  };

  // Pulse ring animation
  const pulseRingVariants = {
    idle: {
      scale: 1,
      opacity: 0,
      transition: { duration: 0 },
    },
    active: {
      scale: [1, 1.5, 2],
      opacity: [0.6, 0.3, 0],
      transition: {
        duration: 2,
        repeat: Infinity,
        ease: 'easeOut',
      },
    },
    error: {
      scale: [1, 1.3, 1.6],
      opacity: [0.8, 0.4, 0],
      transition: {
        duration: 0.8,
        repeat: Infinity,
        ease: 'easeOut',
      },
    },
    veto: {
      scale: [1, 1.4, 1.8],
      opacity: [0.7, 0.35, 0],
      transition: {
        duration: 1.2,
        repeat: Infinity,
        ease: 'easeOut',
      },
    },
  };

  // Icon shake animation for error/veto
  const iconVariants = {
    idle: { rotate: 0 },
    active: {
      rotate: [0, -5, 5, -5, 5, 0],
      transition: { duration: 0.5, repeat: Infinity, repeatDelay: 2 },
    },
    error: {
      rotate: [0, -10, 10, -10, 10, 0],
      x: [0, -2, 2, -2, 2, 0],
      transition: { duration: 0.4, repeat: Infinity },
    },
    veto: {
      rotate: [0, -8, 8, -8, 8, 0],
      transition: { duration: 0.6, repeat: Infinity },
    },
  };

  // Metrics fade-in animation
  const metricsVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        staggerChildren: 0.05,
        delayChildren: 0.1,
      },
    },
  };

  const metricItemVariants = {
    hidden: { opacity: 0, x: -10 },
    visible: { opacity: 1, x: 0 },
  };

  return (
    <div className="relative">
      {/* Outer Pulse Rings */}
      {isActive && (
        <>
          <motion.div
            className="absolute inset-0 rounded-2xl pointer-events-none"
            style={{ backgroundColor: glowColor }}
            variants={pulseRingVariants}
            initial="active"
            animate="active"
          />
          <motion.div
            className="absolute inset-0 rounded-2xl pointer-events-none"
            style={{ backgroundColor: glowColor }}
            variants={pulseRingVariants}
            initial="active"
            animate="active"
            transition={{ delay: 0.5 }}
          />
        </>
      )}

      {/* Main Card Container */}
      <motion.div
        className={`relative p-4 rounded-xl border-2 bg-black/90 backdrop-blur-md min-w-[220px] cursor-pointer`}
        style={{
          borderColor: isError ? '#ef4444' : isVeto ? '#f59e0b' : color,
        }}
        variants={containerVariants}
        initial="idle"
        animate={status}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        {/* Animated Status Indicator */}
        <div className="absolute -top-3 -right-3">
          <div className="relative">
            <div
              className={`w-6 h-6 rounded-full ${isActive ? 'animate-pulse' : ''} transition-all duration-300`}
              style={{ backgroundColor: glowColor }}
            />
            {isActive && (
              <>
                <motion.div
                  className="absolute inset-0 rounded-full"
                  style={{ backgroundColor: glowColor }}
                  animate={{
                    scale: [1, 1.8, 1],
                    opacity: [0.8, 0, 0.8],
                  }}
                  transition={{
                    duration: 1.5,
                    repeat: Infinity,
                    ease: 'easeOut',
                  }}
                />
                <motion.div
                  className="absolute inset-0 rounded-full"
                  style={{ backgroundColor: glowColor }}
                  animate={{
                    scale: [1, 2.2, 1],
                    opacity: [0.6, 0, 0.6],
                  }}
                  transition={{
                    duration: 1.5,
                    repeat: Infinity,
                    ease: 'easeOut',
                    delay: 0.5,
                  }}
                />
              </>
            )}
          </div>
        </div>

        {/* Agent Header */}
        <div className="flex items-center gap-3 mb-3">
          <motion.div
            className="text-3xl"
            style={{ color }}
            variants={iconVariants}
            animate={status}
          >
            {getAgentIcon(name)}
          </motion.div>
          <div>
            <motion.h3
              className="font-tech font-bold text-white uppercase tracking-wider text-sm"
              animate={{ color: isActive ? color : '#ffffff' }}
              transition={{ duration: 0.3 }}
            >
              {name}
            </motion.h3>
            <p className="text-[9px] text-gray-400 uppercase tracking-wide">{role}</p>
          </div>
        </div>

        {/* Animated Status Badge */}
        <motion.div
          className={`mb-3 px-2 py-1 rounded text-[9px] font-bold uppercase tracking-wider text-center`}
          style={{
            backgroundColor: isActive ? `${color}20` : 'rgba(255,255,255,0.05)',
            color: glowColor,
            border: `1px solid ${glowColor}40`,
          }}
          animate={
            isError
              ? {
                  borderColor: ['#ef444440', '#ef4444', '#ef444440'],
                  transition: { duration: 0.5, repeat: Infinity },
                }
              : {}
          }
        >
          {status}
        </motion.div>

        {/* Metrics with Staggered Animation */}
        <motion.div
          className="space-y-1.5 mb-3"
          variants={metricsVariants}
          initial="hidden"
          animate="visible"
        >
          {Object.entries(metrics).map(([key, value]) => (
            <motion.div
              key={key}
              className="flex justify-between items-center text-[10px]"
              variants={metricItemVariants}
            >
              <span className="text-gray-500 uppercase tracking-wide">{key}</span>
              <motion.span
                className="font-mono font-bold"
                style={{ color }}
                key={`${key}-val-${value}`}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.3 }}
              >
                {value}
              </motion.span>
            </motion.div>
          ))}
        </motion.div>

        {/* Last Action with Typewriter Effect */}
        {lastAction && (
          <motion.div
            className="pt-2 border-t border-white/10"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            <motion.p
              className="text-[9px] text-gray-400 truncate font-mono"
              initial={{ opacity: 0, x: -5 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 }}
              key={`action-${agentId}-${lastAction}`}
            >
              {lastAction}
            </motion.p>
          </motion.div>
        )}

        {/* Selected State Highlight */}
        {selected && (
          <motion.div
            className="absolute inset-0 rounded-xl pointer-events-none"
            style={{ border: '2px solid white' }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.2 }}
          />
        )}
      </motion.div>

      {/* Connection Handles */}
      <Handle
        type="target"
        position={Position.Top}
        style={{
          background: color,
          width: 12,
          height: 12,
          border: `2px solid ${glowColor}`,
        }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        style={{
          background: color,
          width: 12,
          height: 12,
          border: `2px solid ${glowColor}`,
        }}
      />
    </div>
  );
});

AgentNode.displayName = 'AgentNode';

export default AgentNode;
