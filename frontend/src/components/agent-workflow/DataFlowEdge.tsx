import React from 'react';
import { BaseEdge, EdgeProps, getBezierPath, EdgeLabelRenderer } from '@xyflow/react';
import { motion } from 'framer-motion';

interface DataFlowEdgeData {
  flowType: 'authorization' | 'opportunity' | 'decision' | 'execution';
  active: boolean;
  color: string;
  label?: string;
}

const DataFlowEdge = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
}: EdgeProps<DataFlowEdgeData>) => {
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    curvature: 0.25,
  });

  const isActive = data?.active ?? false;
  const color = data?.color ?? '#666';
  const flowType = data?.flowType ?? 'authorization';

  // Particle animation variants
  const particleCount = isActive ? 3 : 0;
  const particles = Array.from({ length: particleCount }, (_, i) => i);

  // Flow-specific colors
  const flowColors = {
    authorization: '#f59e0b', // Gold
    opportunity: '#06b6d4', // Cyan
    decision: '#a855f7', // Purple
    execution: '#10b981', // Green
  };

  const particleColor = flowColors[flowType] || color;

  return (
    <>
      {/* Base edge line with glow */}
      <g style={{ filter: 'url(#glow)' }}>
        <BaseEdge
          id={id}
          path={edgePath}
          style={{
            stroke: isActive ? particleColor : '#333',
            strokeWidth: isActive ? 3 : 2,
            opacity: isActive ? 0.8 : 0.2,
            transition: 'all 0.3s ease',
          }}
        />

        {/* Animated glow overlay for active edges */}
        {isActive && (
          <motion.path
            d={edgePath}
            fill="none"
            stroke={particleColor}
            strokeWidth={6}
            strokeOpacity={0.3}
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{
              pathLength: [0, 1],
              opacity: [0, 0.5, 0.5, 0],
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
            style={{ filter: `url(#glow-${particleColor})` }}
          />
        )}
      </g>

      {/* Animated flow particles */}
      {isActive &&
        particles.map((index) => (
          <g key={`${id}-particle-${index}`}>
            {/* Outer glow particle */}
            <circle r="4" fill={particleColor} opacity="0.4">
              <animateMotion
                dur={`${1.5 + index * 0.3}s`}
                repeatCount="indefinite"
                begin={`${index * 0.4}s`}
                path={edgePath}
                rotate="auto"
              />
            </circle>

            {/* Inner bright particle */}
            <circle r="2.5" fill="#ffffff" opacity="0.9">
              <animateMotion
                dur={`${1.5 + index * 0.3}s`}
                repeatCount="indefinite"
                begin={`${index * 0.4}s`}
                path={edgePath}
                rotate="auto"
              />
            </circle>

            {/* Core particle */}
            <circle r="1.5" fill="#ffffff">
              <animateMotion
                dur={`${1.5 + index * 0.3}s`}
                repeatCount="indefinite"
                begin={`${index * 0.4}s`}
                path={edgePath}
                rotate="auto"
              />
              <animate
                attributeName="opacity"
                values="1;0.5;1"
                dur={`${0.3 + index * 0.1}s`}
                repeatCount="indefinite"
              />
            </circle>
          </g>
        ))}

      {/* Pulse wave effect for active edges */}
      {isActive && (
        <>
          <motion.path
            d={edgePath}
            fill="none"
            stroke={particleColor}
            strokeWidth={8}
            strokeOpacity={0}
            initial={{ pathLength: 0 }}
            animate={{
              pathLength: [0, 1],
              opacity: [0, 0.2, 0],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: 'easeOut',
            }}
          />
          <motion.path
            d={edgePath}
            fill="none"
            stroke={particleColor}
            strokeWidth={8}
            strokeOpacity={0}
            initial={{ pathLength: 0 }}
            animate={{
              pathLength: [0, 1],
              opacity: [0, 0.15, 0],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: 'easeOut',
              delay: 1,
            }}
          />
        </>
      )}

      {/* Edge label (optional) */}
      {data?.label && isActive && (
        <EdgeLabelRenderer>
          <motion.div
            className="absolute px-2 py-1 rounded text-[8px] font-bold uppercase tracking-wider"
            style={{
              left: (sourceX + targetX) / 2,
              top: (sourceY + targetY) / 2 - 20,
              transform: 'translate(-50%, -50%)',
              backgroundColor: `${particleColor}20`,
              color: particleColor,
              border: `1px solid ${particleColor}60`,
              backdropFilter: 'blur(4px)',
            }}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
          >
            {data.label}
          </motion.div>
        </EdgeLabelRenderer>
      )}

      {/* SVG filters for glow effects */}
      <defs>
        <filter id={`glow-${particleColor}`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur" />
          <feColorMatrix
            in="blur"
            type="matrix"
            values={`1 0 0 0 0
                     0 1 0 0 0
                     0 0 1 0 0
                     0 0 0 18 -7`}
            result="glow"
          />
          <feMerge>
            <feMergeNode in="glow" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Selection highlight */}
      {selected && (
        <motion.path
          d={edgePath}
          fill="none"
          stroke="#ffffff"
          strokeWidth={6}
          strokeOpacity={0.3}
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.3 }}
          transition={{ duration: 0.2 }}
        />
      )}
    </>
  );
};

export default DataFlowEdge;
