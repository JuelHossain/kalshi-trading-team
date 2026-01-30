import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  ConnectionMode,
  Panel,
  useNodesState,
  useEdgesState,
  addEdge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { motion, AnimatePresence } from 'framer-motion';
import AgentNode from './AgentNode';
import SynapseNode from './SynapseNode';
import DataFlowEdge from './DataFlowEdge';
import { useStore } from '@/store/useStore';
import { AgentSlice, AgentState, DataFlowTransition } from '@/store/slices/agentSlice';

// Node types for React Flow
const nodeTypes = {
  agentNode: AgentNode,
  synapseNode: SynapseNode,
};

// Edge types for React Flow
const edgeTypes = {
  dataFlow: DataFlowEdge,
};

interface AgentWorkflowGraphProps {
  className?: string;
}

const AgentWorkflowGraph: React.FC<AgentWorkflowGraphProps> = ({ className }) => {
  const [mounted, setMounted] = useState(false);

  // Get store data - REAL DATA from engine
  const timelineEvents = useStore((state) => state.timelineEvents);
  const activeAgentId = useStore((state) => state.activeAgentId);
  const isProcessing = useStore((state) => state.isProcessing);
  const agentStates = useStore((state) => state.agentStates);
  const vault = useStore((state) => state.vault);
  const cycleCount = useStore((state) => state.cycleCount);

  // Nodes with REAL data from store - Hub and Spoke layout with Synapse at center
  const initialNodes: Node[] = useMemo(
    () => [
      // Central Synapse Hub
      {
        id: 'synapse',
        type: 'synapseNode',
        position: { x: 350, y: 300 },
        data: {
          name: 'SYNAPSE',
          status: isProcessing ? 'processing' : 'active',
          color: '#ec4899',
          queueMetrics: {
            opportunities: timelineEvents.filter((e) => e.type === 'MARKET').length,
            executions: timelineEvents.filter((e) => e.type === 'TRADE').length,
            totalProcessed: timelineEvents.length,
          },
          lastAction: isProcessing ? 'Processing cycle...' : 'SQLite persistence active',
        },
      },
      // SOUL - Top (from real agentStates or defaults)
      {
        id: 'soul',
        type: 'agentNode',
        position: { x: 325, y: 20 },
        data: {
          agentId: 1,
          name: 'SOUL',
          role: 'Executive Director',
          status: agentStates[1]?.status || 'idle',
          color: '#f59e0b',
          metrics: {
            balance: vault?.total || 0,
            cyclesCompleted: cycleCount,
          },
          lastAction: agentStates[1]?.lastAction || 'System ready',
        },
      },
      // SENSES - Left
      {
        id: 'senses',
        type: 'agentNode',
        position: { x: 20, y: 300 },
        data: {
          agentId: 2,
          name: 'SENSES',
          role: 'Surveillance',
          status: agentStates[2]?.status || 'idle',
          color: '#06b6d4',
          metrics: {
            marketsScanned: timelineEvents.filter((e) => e.type === 'MARKET').length * 10,
            opportunitiesFound: timelineEvents.filter((e) => e.type === 'MARKET').length,
          },
          lastAction: agentStates[2]?.lastAction || 'Awaiting cycle',
        },
      },
      // BRAIN - Right
      {
        id: 'brain',
        type: 'agentNode',
        position: { x: 650, y: 300 },
        data: {
          agentId: 3,
          name: 'BRAIN',
          role: 'Intelligence',
          status: agentStates[3]?.status || 'idle',
          color: '#a855f7',
          metrics: {
            confidence: agentStates[3]?.metrics?.confidence || 0,
            simulationsRun: timelineEvents.filter((e) => e.type === 'SIMULATION').length,
          },
          lastAction: agentStates[3]?.lastAction || 'Awaiting opportunities',
        },
      },
      // HAND - Bottom
      {
        id: 'hand',
        type: 'agentNode',
        position: { x: 325, y: 580 },
        data: {
          agentId: 4,
          name: 'HAND',
          role: 'Execution',
          status: agentStates[4]?.status || 'idle',
          color: '#10b981',
          metrics: {
            ordersExecuted: timelineEvents.filter((e) => e.type === 'TRADE').length,
            pendingOrders: 0,
          },
          lastAction: agentStates[4]?.lastAction || 'Standing by',
        },
      },
    ],
    [agentStates, vault, cycleCount, timelineEvents, isProcessing]
  );

  // Hub-and-spoke edges - All agents connect to Synapse
  const initialEdges: Edge[] = useMemo(
    () => [
      // SOUL <-> SYNAPSE (Authorization flow)
      {
        id: 'soul-synapse-push',
        source: 'soul',
        target: 'synapse',
        sourceHandle: 'soul-out',
        targetHandle: 'soul-in',
        type: 'dataFlow',
        animated: false,
        data: {
          flowType: 'authorization',
          active: false,
          color: '#f59e0b',
          label: 'AUTH',
        },
      },
      {
        id: 'synapse-soul-pull',
        source: 'synapse',
        target: 'soul',
        sourceHandle: 'soul-out',
        targetHandle: 'soul-in',
        type: 'dataFlow',
        animated: false,
        data: {
          flowType: 'status',
          active: false,
          color: '#ec4899',
          label: 'STATE',
        },
      },

      // SENSES <-> SYNAPSE (Market data flow)
      {
        id: 'senses-synapse-push',
        source: 'senses',
        target: 'synapse',
        sourceHandle: 'senses-out',
        targetHandle: 'senses-in',
        type: 'dataFlow',
        animated: false,
        data: {
          flowType: 'opportunity',
          active: false,
          color: '#06b6d4',
          label: 'PUSH',
        },
      },
      {
        id: 'synapse-senses-pull',
        source: 'synapse',
        target: 'senses',
        sourceHandle: 'senses-out',
        targetHandle: 'senses-in',
        type: 'dataFlow',
        animated: false,
        data: {
          flowType: 'command',
          active: false,
          color: '#ec4899',
          label: 'POP',
        },
      },

      // BRAIN <-> SYNAPSE (Analysis flow)
      {
        id: 'brain-synapse-push',
        source: 'brain',
        target: 'synapse',
        sourceHandle: 'brain-out',
        targetHandle: 'brain-in',
        type: 'dataFlow',
        animated: false,
        data: {
          flowType: 'decision',
          active: false,
          color: '#a855f7',
          label: 'SIGNAL',
        },
      },
      {
        id: 'synapse-brain-pull',
        source: 'synapse',
        target: 'brain',
        sourceHandle: 'brain-out',
        targetHandle: 'brain-in',
        type: 'dataFlow',
        animated: false,
        data: {
          flowType: 'opportunity',
          active: false,
          color: '#ec4899',
          label: 'QUEUE',
        },
      },

      // HAND <-> SYNAPSE (Execution flow)
      {
        id: 'hand-synapse-push',
        source: 'hand',
        target: 'synapse',
        sourceHandle: 'hand-out',
        targetHandle: 'hand-in',
        type: 'dataFlow',
        animated: false,
        data: {
          flowType: 'execution',
          active: false,
          color: '#10b981',
          label: 'CONFIRM',
        },
      },
      {
        id: 'synapse-hand-pull',
        source: 'synapse',
        target: 'hand',
        sourceHandle: 'hand-out',
        targetHandle: 'hand-in',
        type: 'dataFlow',
        animated: false,
        data: {
          flowType: 'decision',
          active: false,
          color: '#ec4899',
          label: 'ORDER',
        },
      },
    ],
    []
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Handle new connections
  const onConnect = useCallback(
    (params: any) => {
      setEdges((eds) =>
        addEdge(
          {
            ...params,
            type: 'dataFlow',
            data: { flowType: 'execution', active: false, color: '#10b981' },
          },
          eds
        )
      );
    },
    [setEdges]
  );

  // Component mount
  useEffect(() => {
    setMounted(true);
  }, []);

  // Sync nodes with REAL agent states from store
  useEffect(() => {
    const agentMap: Record<number, string> = { 1: 'soul', 2: 'senses', 3: 'brain', 4: 'hand' };

    setNodes((nodes) =>
      nodes.map((node) => {
        // Update Synapse with real metrics
        if (node.id === 'synapse') {
          return {
            ...node,
            data: {
              ...node.data,
              status: isProcessing ? 'processing' : 'active',
              queueMetrics: {
                opportunities: timelineEvents.filter((e) => e.type === 'MARKET').length,
                executions: timelineEvents.filter((e) => e.type === 'TRADE').length,
                totalProcessed: timelineEvents.length,
              },
            },
          };
        }

        // Update agent nodes with real state
        const agentId = Object.keys(agentMap).find((key) => agentMap[Number(key)] === node.id);
        if (agentId && agentStates[Number(agentId)]) {
          const state = agentStates[Number(agentId)];
          return {
            ...node,
            data: {
              ...node.data,
              status: state.status,
              lastAction: state.lastAction,
              // Update metrics based on real data
              metrics: {
                ...node.data.metrics,
                ...(Number(agentId) === 1 && {
                  balance: vault?.total || 0,
                  cyclesCompleted: cycleCount,
                }),
                ...(Number(agentId) === 2 && {
                  marketsScanned: timelineEvents.filter((e) => e.type === 'MARKET').length * 10,
                  opportunitiesFound: timelineEvents.filter((e) => e.type === 'MARKET').length,
                }),
                ...(Number(agentId) === 3 && {
                  simulationsRun: timelineEvents.filter((e) => e.type === 'SIMULATION').length,
                }),
                ...(Number(agentId) === 4 && {
                  ordersExecuted: timelineEvents.filter((e) => e.type === 'TRADE').length,
                }),
              },
            },
          };
        }
        return node;
      })
    );
  }, [agentStates, timelineEvents, vault, cycleCount, isProcessing, setNodes]);

  // Activate edges based on active agent
  useEffect(() => {
    if (activeAgentId !== null) {
      const agentMap: Record<number, string> = { 1: 'soul', 2: 'senses', 3: 'brain', 4: 'hand' };
      const activeAgent = agentMap[activeAgentId];

      // Activate edges for the active agent
      setEdges((edges) =>
        edges.map((edge) => {
          if (
            edge.id.includes(`${activeAgent}-synapse`) ||
            edge.id.includes(`synapse-${activeAgent}`)
          ) {
            return { ...edge, data: { ...edge.data, active: true } };
          }
          return { ...edge, data: { ...edge.data, active: false } };
        })
      );

      // Reset edges after delay
      const timeout = setTimeout(() => {
        setEdges((edges) =>
          edges.map((edge) => ({ ...edge, data: { ...edge.data, active: false } }))
        );
      }, 1500);

      return () => clearTimeout(timeout);
    }
  }, [activeAgentId, setEdges]);

  // Animate edges when processing
  useEffect(() => {
    if (isProcessing) {
      // Sequential flow through Synapse
      const sequence = [
        ['senses-synapse-push', 'synapse-brain-pull'],
        ['brain-synapse-push', 'synapse-hand-pull'],
      ];

      sequence.forEach((edgeIds, index) => {
        setTimeout(() => {
          setEdges((edges) =>
            edges.map((edge) =>
              edgeIds.includes(edge.id)
                ? { ...edge, data: { ...edge.data, active: true } }
                : { ...edge, data: { ...edge.data, active: false } }
            )
          );
        }, index * 800);
      });

      // Reset after animation
      setTimeout(() => {
        setEdges((edges) =>
          edges.map((edge) => ({ ...edge, data: { ...edge.data, active: false } }))
        );
      }, 2500);
    }
  }, [isProcessing, setEdges]);

  return (
    <div className={`relative w-full h-full bg-black ${className || ''}`}>
      {/* Background Grid */}
      <div
        className="absolute inset-0 opacity-20"
        style={{
          backgroundImage: `
            linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px',
        }}
      />

      {/* Animated Background Pulse */}
      {mounted && (
        <motion.div
          className="absolute inset-0 pointer-events-none"
          animate={{
            background: [
              'radial-gradient(circle at 50% 50%, rgba(236,72,153,0) 0%, transparent 50%)',
              'radial-gradient(circle at 50% 50%, rgba(236,72,153,0.03) 0%, transparent 50%)',
              'radial-gradient(circle at 50% 50%, rgba(6,182,212,0.03) 0%, transparent 50%)',
              'radial-gradient(circle at 50% 50%, rgba(168,85,247,0.03) 0%, transparent 50%)',
              'radial-gradient(circle at 50% 50%, rgba(236,72,153,0) 0%, transparent 50%)',
            ],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: 'linear',
          }}
        />
      )}

      {/* React Flow Canvas */}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        connectionMode={ConnectionMode.Loose}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        minZoom={0.3}
        maxZoom={1.5}
        defaultEdgeOptions={{}}
        style={{ background: 'transparent' }}
      >
        {/* Animated Background Pattern */}
        <Background
          color={isProcessing ? '#ec4899' : '#333333'}
          gap={50}
          opacity={isProcessing ? 0.15 : 0.05}
          style={{
            transition: 'all 0.5s ease',
          }}
        />

        {/* Controls */}
        <Controls
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            background: 'rgba(0,0,0,0.8)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '8px',
            padding: '8px',
          }}
        />

        {/* MiniMap */}
        <MiniMap
          style={{
            background: 'rgba(0,0,0,0.8)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '8px',
          }}
          nodeColor={(node) => node.data.color}
          maskColor="rgba(0, 0, 0, 0.6)"
        />

        {/* Status Panel */}
        <Panel position="top-left" className="pointer-events-none">
          <motion.div
            className="bg-black/80 backdrop-blur-md border border-white/10 rounded-lg p-4 min-w-[280px]"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
          >
            <h3 className="text-[10px] font-tech font-bold text-gray-400 uppercase tracking-wider mb-2">
              Synapse Queue System
            </h3>
            <div className="flex items-center gap-2 mb-3">
              <motion.div
                className={`w-2 h-2 rounded-full ${isProcessing ? 'bg-pink-500' : 'bg-gray-500'}`}
                animate={
                  isProcessing
                    ? {
                        scale: [1, 1.5, 1],
                        opacity: [1, 0.7, 1],
                      }
                    : {}
                }
                transition={{ duration: 1, repeat: Infinity }}
              />
              <span className="text-[10px] font-mono text-gray-300">
                {isProcessing ? 'Data Flow Active' : 'Idle'}
              </span>
            </div>

            {/* Architecture Description */}
            <div className="space-y-2 text-[9px] text-gray-500 font-mono border-t border-white/10 pt-2">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-cyan-500"></span>
                <span>SENSES → queue_opportunities</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-purple-500"></span>
                <span>BRAIN ← Pop / Push → queue_executions</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                <span>HAND ← Pop → Execute</span>
              </div>
            </div>
          </motion.div>
        </Panel>

        {/* Processing Indicator */}
        <AnimatePresence>
          {isProcessing && (
            <Panel position="top-right">
              <motion.div
                className="bg-pink-500/20 backdrop-blur-md border border-pink-500/40 rounded-lg px-4 py-2"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
              >
                <div className="flex items-center gap-3">
                  <motion.div
                    className="w-3 h-3 rounded-full bg-pink-500"
                    animate={{
                      scale: [1, 1.5, 1],
                      opacity: [1, 0.5, 1],
                    }}
                    transition={{ duration: 0.8, repeat: Infinity }}
                  />
                  <span className="text-[10px] font-bold text-pink-300 uppercase tracking-wider">
                    Synapse Active
                  </span>
                </div>
              </motion.div>
            </Panel>
          )}
        </AnimatePresence>

        {/* Legend */}
        <Panel position="bottom-left" className="pointer-events-none">
          <motion.div
            className="bg-black/80 backdrop-blur-md border border-white/10 rounded-lg p-3"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <h4 className="text-[9px] font-bold text-gray-400 uppercase tracking-wider mb-2">
              Data Flow Types
            </h4>
            <div className="space-y-1.5">
              {[
                { color: '#06b6d4', label: 'Opportunities →' },
                { color: '#a855f7', label: 'Decisions →' },
                { color: '#10b981', label: 'Executions →' },
                { color: '#f59e0b', label: 'Authorization' },
                { color: '#ec4899', label: 'Synapse Queue' },
              ].map((item) => (
                <div key={item.label} className="flex items-center gap-2">
                  <div className="w-3 h-0.5 rounded" style={{ backgroundColor: item.color }} />
                  <span className="text-[9px] text-gray-500 font-mono">{item.label}</span>
                </div>
              ))}
            </div>
          </motion.div>
        </Panel>
      </ReactFlow>
    </div>
  );
};

export default AgentWorkflowGraph;
