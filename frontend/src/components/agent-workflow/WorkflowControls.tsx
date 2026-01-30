import React from 'react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Play, Square, RotateCcw, Zap } from 'lucide-react';

interface WorkflowControlsProps {
  isProcessing: boolean;
  autoPilot: boolean;
  killSwitchActive: boolean;
  isLoggedIn: boolean;
  onInitiateCycle: () => void;
  onCancelCycle: () => void;
  onToggleAutopilot: () => void;
  onReset: () => void;
  onDemoAnimation?: () => void;
}

const WorkflowControls: React.FC<WorkflowControlsProps> = ({
  isProcessing,
  autoPilot,
  killSwitchActive,
  isLoggedIn,
  onInitiateCycle,
  onCancelCycle,
  onToggleAutopilot,
  onReset,
  onDemoAnimation,
}) => {
  return (
    <motion.div
      className="flex items-center gap-3 bg-black/80 backdrop-blur-md border border-white/10 rounded-xl p-3"
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
    >
      {/* Main Action Button */}
      <div className="flex items-center gap-2">
        <Button
          onClick={isProcessing ? onCancelCycle : onInitiateCycle}
          disabled={killSwitchActive || !isLoggedIn}
          className={`!px-4 !py-2 !h-auto !text-[11px] font-bold tracking-wider uppercase transition-all ${
            killSwitchActive || !isLoggedIn
              ? 'opacity-50 cursor-not-allowed'
              : isProcessing
                ? 'bg-orange-500/20 hover:bg-orange-500/30 text-orange-400 border-orange-500/30'
                : 'bg-emerald-500 hover:bg-emerald-400 text-black'
          }`}
        >
          {isProcessing ? (
            <>
              <Square className="w-3.5 h-3.5 mr-2 fill-current" />
              Cancel Cycle
            </>
          ) : (
            <>
              <Play className="w-3.5 h-3.5 mr-2 fill-current" />
              Initiate Cycle
            </>
          )}
        </Button>

        {/* Autopilot Toggle */}
        <Button
          onClick={onToggleAutopilot}
          disabled={killSwitchActive || !isLoggedIn || isProcessing}
          className={`!px-4 !py-2 !h-auto !text-[11px] font-bold tracking-wider uppercase transition-all ${
            autoPilot
              ? 'bg-cyan-500 hover:bg-cyan-400 text-black'
              : 'bg-white/5 hover:bg-white/10 text-gray-300 border border-white/10'
          } ${killSwitchActive || !isLoggedIn ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <Zap className={`w-3.5 h-3.5 mr-2 ${autoPilot ? 'fill-current' : ''}`} />
          Autopilot
        </Button>

        {/* Reset */}
        <Button
          onClick={onReset}
          disabled={isProcessing}
          className="!px-3 !py-2 !h-auto !text-[11px] font-bold tracking-wider uppercase bg-white/5 hover:bg-white/10 text-gray-400 border border-white/10 transition-all"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </Button>

        {/* Demo Animation */}
        {onDemoAnimation && (
          <Button
            onClick={onDemoAnimation}
            disabled={isProcessing}
            className="!px-3 !py-2 !h-auto !text-[11px] font-bold tracking-wider uppercase bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 border border-purple-500/30 transition-all"
            title="Trigger demo animation to test workflow visualization"
          >
            <Zap className="w-3.5 h-3.5" />
          </Button>
        )}
      </div>

      {/* Status Divider */}
      <div className="h-8 w-px bg-white/10" />

      {/* Status Display */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <motion.div
            className={`w-2 h-2 rounded-full ${isProcessing ? 'bg-emerald-500' : 'bg-gray-500'}`}
            animate={
              isProcessing
                ? {
                    scale: [1, 1.5, 1],
                    opacity: [1, 0.5, 1],
                  }
                : {}
            }
            transition={{ duration: 1, repeat: Infinity }}
          />
          <span className="text-[10px] font-mono text-gray-400 uppercase tracking-wider">
            {isProcessing ? 'Processing' : 'Idle'}
          </span>
        </div>

        {autoPilot && (
          <motion.div
            className="flex items-center gap-1.5 px-2 py-1 bg-cyan-500/10 rounded border border-cyan-500/20"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <motion.div
              className="w-1.5 h-1.5 rounded-full bg-cyan-400"
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            />
            <span className="text-[9px] font-bold text-cyan-400 uppercase tracking-wider">
              Auto
            </span>
          </motion.div>
        )}

        {killSwitchActive && (
          <motion.div
            className="flex items-center gap-1.5 px-2 py-1 bg-red-500/10 rounded border border-red-500/20"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <motion.div
              className="w-1.5 h-1.5 rounded-full bg-red-500"
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ duration: 0.8, repeat: Infinity }}
            />
            <span className="text-[9px] font-bold text-red-400 uppercase tracking-wider">
              Locked
            </span>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};

export default WorkflowControls;
