import React from 'react';

interface QueueItem {
  id: string;
  content: string;
  source?: string;
}

interface LogisticsCenterProps {
  opportunityQueue: QueueItem[];
  executionQueue: QueueItem[];
  scoutStatus: string;
  brainStatus: string;
  sniperStatus: string;
}

const LogisticsCenter: React.FC<LogisticsCenterProps> = ({
  opportunityQueue,
  executionQueue,
  scoutStatus,
  brainStatus,
  sniperStatus,
}) => {
  return (
    <div className="glass-panel rounded-[2rem] p-8 shadow-lg hover:border-white/10 transition-colors">
      <div className="text-center mb-6">
        <span className="text-[10px] text-blue-400/80 uppercase font-mono tracking-widest flex items-center justify-center gap-2">
          <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></span>
          🚛 Logistics Center
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Scout Monitor */}
        <div className="bg-white/5 rounded-2xl p-5 border border-white/5 relative overflow-hidden group">
          <div className="flex justify-between items-center mb-4">
            <span className="text-[10px] text-blue-400/80 uppercase font-mono tracking-widest flex items-center gap-2">
              <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></span>
              Scout Monitor
            </span>
            <span
              className={`text-[9px] uppercase px-2 py-0.5 rounded-full font-bold ${
                scoutStatus === 'active'
                  ? 'text-emerald-400 bg-emerald-400/10 border border-emerald-400/20'
                  : 'text-yellow-400 bg-yellow-400/10 border border-yellow-400/20'
              }`}
            >
              {scoutStatus === 'active' ? '🟢 Live Scanning' : '⏸️ Paused'}
            </span>
          </div>
          <div className="space-y-2">
            <div className="text-[8px] text-gray-500 uppercase tracking-widest mb-2">
              Opportunity Queue:
            </div>
            {opportunityQueue.length === 0 ? (
              <div className="text-[10px] text-gray-600 font-mono">No opportunities queued</div>
            ) : (
              opportunityQueue.map((item, index) => (
                <div
                  key={item.id}
                  className="bg-white/5 p-2 rounded text-[10px] font-mono border border-white/10"
                >
                  {index + 1}. {item.content}
                  {item.source && <span className="text-gray-500"> (Source: {item.source})</span>}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Intelligence Hub */}
        <div className="bg-white/5 rounded-2xl p-5 border border-white/5 relative overflow-hidden group">
          <div className="flex justify-between items-center mb-4">
            <span className="text-[10px] text-blue-400/80 uppercase font-mono tracking-widest flex items-center gap-2">
              <span className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-pulse"></span>
              Intelligence Hub
            </span>
            <span
              className={`text-[9px] uppercase px-2 py-0.5 rounded-full font-bold ${
                brainStatus === 'processing'
                  ? 'text-blue-400 bg-blue-400/10 border border-blue-400/20'
                  : 'text-gray-400 bg-gray-400/10 border border-gray-400/20'
              }`}
            >
              {brainStatus === 'processing' ? '🧠 Processing' : '💤 Idle'}
            </span>
          </div>
          <div className="space-y-2">
            <div className="text-[8px] text-gray-500 uppercase tracking-widest mb-2">
              Brain Logic:
            </div>
            <div className="text-[10px] text-gray-600 font-mono">
              {brainStatus === 'processing'
                ? 'Analyzing opportunities with Gemini debate...'
                : 'Waiting for opportunities to process'}
            </div>
          </div>
        </div>

        {/* Sniper Console */}
        <div className="bg-white/5 rounded-2xl p-5 border border-white/5 relative overflow-hidden group">
          <div className="flex justify-between items-center mb-4">
            <span className="text-[10px] text-blue-400/80 uppercase font-mono tracking-widest flex items-center gap-2">
              <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse"></span>
              Sniper Console
            </span>
            <span
              className={`text-[9px] uppercase px-2 py-0.5 rounded-full font-bold ${
                sniperStatus === 'ready'
                  ? 'text-emerald-400 bg-emerald-400/10 border border-emerald-400/20'
                  : 'text-orange-400 bg-orange-400/10 border border-orange-400/20'
              }`}
            >
              {sniperStatus === 'ready' ? '🏹 Ready' : '⏳ Waiting'}
            </span>
          </div>
          <div className="space-y-2">
            <div className="text-[8px] text-gray-500 uppercase tracking-widest mb-2">
              Execution Queue:
            </div>
            {executionQueue.length === 0 ? (
              <div className="text-[10px] text-gray-600 font-mono">No executions queued</div>
            ) : (
              executionQueue.map((item, index) => (
                <div
                  key={item.id}
                  className="bg-white/5 p-2 rounded text-[10px] font-mono border border-white/10"
                >
                  {index + 1}. {item.content}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LogisticsCenter;
