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
  sniperStatus
}) => {
  return (
    <div className="bg-gray-900 text-white p-6 rounded-lg shadow-lg">
      <h2 className="text-2xl font-bold mb-6 text-center">🚛 Logistics Center</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Scout Monitor */}
        <div className="bg-gray-800 p-4 rounded-lg">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Scout Monitor</h3>
            <span className={`px-2 py-1 rounded text-sm ${
              scoutStatus === 'active' ? 'bg-green-500' : 'bg-yellow-500'
            }`}>
              {scoutStatus === 'active' ? '🟢 Live Scanning' : '⏸️ Paused'}
            </span>
          </div>
          <div className="space-y-2">
            <h4 className="font-medium">Opportunity Queue:</h4>
            {opportunityQueue.length === 0 ? (
              <p className="text-gray-400">No opportunities queued</p>
            ) : (
              opportunityQueue.map((item, index) => (
                <div key={item.id} className="bg-gray-700 p-2 rounded text-sm">
                  {index + 1}. {item.content}
                  {item.source && <span className="text-gray-400"> (Source: {item.source})</span>}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Intelligence Hub */}
        <div className="bg-gray-800 p-4 rounded-lg">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Intelligence Hub</h3>
            <span className={`px-2 py-1 rounded text-sm ${
              brainStatus === 'processing' ? 'bg-blue-500' : 'bg-gray-500'
            }`}>
              {brainStatus === 'processing' ? '🧠 Processing' : '💤 Idle'}
            </span>
          </div>
          <div className="space-y-2">
            <h4 className="font-medium">Brain Logic:</h4>
            <p className="text-gray-400 text-sm">
              {brainStatus === 'processing'
                ? 'Analyzing opportunities with Gemini debate...'
                : 'Waiting for opportunities to process'
              }
            </p>
          </div>
        </div>

        {/* Sniper Console */}
        <div className="bg-gray-800 p-4 rounded-lg">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Sniper Console</h3>
            <span className={`px-2 py-1 rounded text-sm ${
              sniperStatus === 'ready' ? 'bg-green-500' : 'bg-red-500'
            }`}>
              {sniperStatus === 'ready' ? '🏹 Ready' : '⏳ Waiting'}
            </span>
          </div>
          <div className="space-y-2">
            <h4 className="font-medium">Execution Queue:</h4>
            {executionQueue.length === 0 ? (
              <p className="text-gray-400">No executions queued</p>
            ) : (
              executionQueue.map((item, index) => (
                <div key={item.id} className="bg-gray-700 p-2 rounded text-sm">
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