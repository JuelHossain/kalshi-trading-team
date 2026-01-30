import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Radar, Database, TrendingUp } from 'lucide-react';
import { LogEntry } from '@shared/types';

interface SensesMetricsProps {
  logs: LogEntry[];
  cycleCount: number;
}

interface ParsedSensesData {
  marketsFetched: number;
  opportunitiesQueued: number;
  queueSize: number;
  maxVolume: number;
  lastScanned: string;
}

const SensesMetrics: React.FC<SensesMetricsProps> = ({ logs, cycleCount }) => {
  const sensesData = useMemo(() => {
    const data: ParsedSensesData = {
      marketsFetched: 0,
      opportunitiesQueued: 0,
      queueSize: 0,
      maxVolume: 0,
      lastScanned: 'Not started',
    };

    // Parse logs to extract Senses metrics
    logs.forEach((log) => {
      const message = log.message || '';

      // Extract markets fetched count
      const fetchedMatch = message.match(/Fetched (\d+) markets from Kalshi API/i);
      if (fetchedMatch) {
        data.marketsFetched = parseInt(fetchedMatch[1], 10);
      }

      // Extract opportunities queued count
      const queuedMatch = message.match(/Selected (\d+) top markets by volume/i);
      if (queuedMatch) {
        data.opportunitiesQueued = parseInt(queuedMatch[1], 10);
      }

      // Extract queue size
      const queueMatch = message.match(/Queue Size: (\d+)/i);
      if (queueMatch) {
        data.queueSize = parseInt(queueMatch[1], 10);
      }

      // Extract max volume
      const volumeMatch = message.match(/Max Volume: \$(\d+)/i);
      if (volumeMatch) {
        data.maxVolume = parseInt(volumeMatch[1], 10);
      }

      // Extract last scanned ticker
      const scanMatch = message.match(/\[OK\] Queued to Synapse: ([\w-]+)/i);
      if (scanMatch) {
        data.lastScanned = scanMatch[1];
      }
    });

    return data;
  }, [logs]);

  return (
    <motion.div
      className="bg-black/80 backdrop-blur-md border border-white/10 rounded-xl p-4"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-[10px] font-tech font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
          <Radar className="w-3 h-3" />
          Senses Workflow
        </h3>
        <span className="text-[9px] font-mono text-gray-500">Cycle #{cycleCount}</span>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-3">
        {/* Markets Fetched */}
        <div className="bg-white/5 rounded-lg p-3 border border-white/5">
          <div className="flex items-center gap-2 mb-1">
            <Database className="w-3 h-3 text-cyan-500" />
            <span className="text-[8px] text-gray-500 uppercase tracking-wider">Markets</span>
          </div>
          <div className="text-xl font-bold font-mono text-cyan-400">
            {sensesData.marketsFetched}
          </div>
          <div className="text-[8px] text-gray-600 mt-0.5">Scanned from Kalshi</div>
        </div>

        {/* Opportunities Queued */}
        <div className="bg-white/5 rounded-lg p-3 border border-white/5">
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className="w-3 h-3 text-emerald-500" />
            <span className="text-[8px] text-gray-500 uppercase tracking-wider">Opportunities</span>
          </div>
          <div className="text-xl font-bold font-mono text-emerald-400">
            {sensesData.opportunitiesQueued}
          </div>
          <div className="text-[8px] text-gray-600 mt-0.5">Top by volume</div>
        </div>
      </div>

      {/* Queue Size */}
      <div className="mt-3 bg-white/5 rounded-lg p-3 border border-white/5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="w-3 h-3 text-purple-500" />
            <span className="text-[8px] text-gray-500 uppercase tracking-wider">Queue Size</span>
          </div>
          <div className="text-lg font-bold font-mono text-purple-400">{sensesData.queueSize}</div>
        </div>
        {sensesData.queueSize > 0 && (
          <div className="mt-2 h-1.5 bg-white/10 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-cyan-500 to-purple-500"
              initial={{ width: 0 }}
              animate={{ width: `${Math.min(sensesData.queueSize / 10, 100)}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
        )}
      </div>

      {/* Last Scanned */}
      {sensesData.lastScanned !== 'Not started' && (
        <div className="mt-3 p-2 bg-white/5 rounded border border-white/5">
          <div className="text-[8px] text-gray-600 uppercase tracking-wider mb-1">Last Scanned</div>
          <div className="text-[9px] font-mono text-gray-400 truncate">
            {sensesData.lastScanned}
          </div>
        </div>
      )}

      {/* Status */}
      <div className="mt-3 flex items-center justify-center gap-2">
        <motion.div
          className={`w-2 h-2 rounded-full ${
            sensesData.marketsFetched > 0 ? 'bg-emerald-500' : 'bg-gray-600'
          }`}
          animate={
            sensesData.marketsFetched > 0 && sensesData.queueSize > 0
              ? {
                  scale: [1, 1.3, 1],
                  opacity: [1, 0.6, 1],
                }
              : {}
          }
          transition={{ duration: 1.5, repeat: sensesData.marketsFetched > 0 ? Infinity : 0 }}
        />
        <span className="text-[8px] text-gray-500 uppercase tracking-wider">
          {sensesData.marketsFetched > 0 ? 'Active' : 'Idle'}
        </span>
      </div>
    </motion.div>
  );
};

export default SensesMetrics;
