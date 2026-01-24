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
    <div className="glass-panel rounded-2xl p-6 md:p-8 shadow-xl hover:border-emerald-500/20 transition-all duration-300 flex-1">
      <div className="text-center mb-8">
        <h3 className="text-sm text-blue-400 font-mono uppercase tracking-widest flex items-center justify-center gap-3">
          <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse shadow-lg shadow-blue-500/50"></span>
          🚛 Logistics Center
        </h3>
        <p className="text-xs text-gray-500 mt-2">Real-time operational dashboard</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-full">
        {/* Scout Monitor */}
        <div className="bg-gradient-to-br from-white/5 to-white/2 rounded-xl p-6 border border-white/10 hover:border-green-500/30 transition-all duration-300 group relative overflow-hidden flex flex-col">
          <div className="absolute inset-0 bg-gradient-to-br from-green-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
          <div className="relative">
            <div className="flex justify-between items-start mb-6">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                <h4 className="text-xs font-bold text-green-400 uppercase tracking-wider">
                  Scout Monitor
                </h4>
              </div>
              <span
                className={`text-xs uppercase px-3 py-1 rounded-full font-bold border ${
                  scoutStatus === 'active'
                    ? 'text-emerald-300 bg-emerald-500/20 border-emerald-500/30 shadow-lg shadow-emerald-500/20'
                    : 'text-yellow-300 bg-yellow-500/20 border-yellow-500/30'
                }`}
              >
                {scoutStatus === 'active' ? '🟢 Live' : '⏸️ Paused'}
              </span>
            </div>

            <div className="space-y-3">
              <div className="text-xs text-gray-400 uppercase tracking-wider font-semibold">
                Opportunity Queue ({opportunityQueue.length})
              </div>
              <div className="max-h-64 overflow-y-auto space-y-2">
                {opportunityQueue.length === 0 ? (
                  <div className="text-xs text-gray-500 font-mono italic p-3 bg-black/20 rounded-lg">
                    No opportunities queued
                  </div>
                ) : (
                  opportunityQueue.map((item, index) => (
                    <div
                      key={item.id}
                      className="bg-white/5 p-3 rounded-lg text-xs font-mono border border-white/10 hover:border-green-500/20 transition-colors"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-green-400 font-bold">{index + 1}.</span>
                        <span className="text-white truncate">{item.content}</span>
                      </div>
                      {item.source && (
                        <div className="text-gray-500 text-xs">Source: {item.source}</div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Intelligence Hub */}
        <div className="bg-gradient-to-br from-white/5 to-white/2 rounded-xl p-6 border border-white/10 hover:border-purple-500/30 transition-all duration-300 group relative overflow-hidden flex flex-col">
          <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
          <div className="relative">
            <div className="flex justify-between items-start mb-6">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 bg-purple-500 rounded-full animate-pulse"></span>
                <h4 className="text-xs font-bold text-purple-400 uppercase tracking-wider">
                  Intelligence Hub
                </h4>
              </div>
              <span
                className={`text-xs uppercase px-3 py-1 rounded-full font-bold border ${
                  brainStatus === 'processing'
                    ? 'text-blue-300 bg-blue-500/20 border-blue-500/30 shadow-lg shadow-blue-500/20'
                    : 'text-gray-300 bg-gray-500/20 border-gray-500/30'
                }`}
              >
                {brainStatus === 'processing' ? '🧠 Active' : '💤 Idle'}
              </span>
            </div>

            <div className="space-y-3">
              <div className="text-xs text-gray-400 uppercase tracking-wider font-semibold">
                Brain Status
              </div>
              <div className="p-4 bg-black/20 rounded-lg border border-white/5">
                <div className="text-sm text-white font-mono mb-2">
                  {brainStatus === 'processing'
                    ? 'Analyzing opportunities with AI debate...'
                    : 'Awaiting opportunities for processing'}
                </div>
                {brainStatus === 'processing' && (
                  <div className="flex items-center gap-2 mt-3">
                    <div className="flex space-x-1">
                      <div className="w-1 h-1 bg-purple-500 rounded-full animate-bounce"></div>
                      <div
                        className="w-1 h-1 bg-purple-500 rounded-full animate-bounce"
                        style={{ animationDelay: '0.1s' }}
                      ></div>
                      <div
                        className="w-1 h-1 bg-purple-500 rounded-full animate-bounce"
                        style={{ animationDelay: '0.2s' }}
                      ></div>
                    </div>
                    <span className="text-xs text-purple-300">Processing...</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Sniper Console */}
        <div className="bg-gradient-to-br from-white/5 to-white/2 rounded-xl p-6 border border-white/10 hover:border-red-500/30 transition-all duration-300 group relative overflow-hidden flex flex-col">
          <div className="absolute inset-0 bg-gradient-to-br from-red-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
          <div className="relative">
            <div className="flex justify-between items-start mb-6">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
                <h4 className="text-xs font-bold text-red-400 uppercase tracking-wider">
                  Sniper Console
                </h4>
              </div>
              <span
                className={`text-xs uppercase px-3 py-1 rounded-full font-bold border ${
                  sniperStatus === 'ready'
                    ? 'text-emerald-300 bg-emerald-500/20 border-emerald-500/30 shadow-lg shadow-emerald-500/20'
                    : 'text-orange-300 bg-orange-500/20 border-orange-500/30'
                }`}
              >
                {sniperStatus === 'ready' ? '🏹 Ready' : '⏳ Waiting'}
              </span>
            </div>

            <div className="space-y-3">
              <div className="text-xs text-gray-400 uppercase tracking-wider font-semibold">
                Execution Queue ({executionQueue.length})
              </div>
              <div className="max-h-64 overflow-y-auto space-y-2">
                {executionQueue.length === 0 ? (
                  <div className="text-xs text-gray-500 font-mono italic p-3 bg-black/20 rounded-lg">
                    No executions queued
                  </div>
                ) : (
                  executionQueue.map((item, index) => (
                    <div
                      key={item.id}
                      className="bg-white/5 p-3 rounded-lg text-xs font-mono border border-white/10 hover:border-red-500/20 transition-colors"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-red-400 font-bold">{index + 1}.</span>
                        <span className="text-white truncate">{item.content}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LogisticsCenter;
