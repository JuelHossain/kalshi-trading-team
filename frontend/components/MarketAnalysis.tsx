import React, { useState } from 'react';
import { runCommitteeDebate } from '../agents/agent-4-analyst';
import { DebateResponse, LogEntry } from '../types';

interface MarketAnalysisProps {
  onLog?: (message: string, agentId: number, level: LogEntry['level']) => void;
}

const MarketAnalysis: React.FC<MarketAnalysisProps> = ({ onLog }) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DebateResponse | null>(null);

  const handleDebate = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setResult(null);

    if (onLog) onLog(`Agent 4: Processing hypothesis: "${query.substring(0, 20)}..."`, 4, 'INFO');

    try {
      const response = await runCommitteeDebate(query);

      if (response.optimistArg.includes("[LOCAL_FALLBACK]")) {
        if (onLog) {
          onLog("Agent 4: Connection to Gemini Matrix failed.", 4, 'ERROR');
          onLog("Agent 4: Engaging fallback: Python NLTK Heuristics.", 4, 'WARN');
        }
      } else {
        if (onLog) onLog("Agent 4: Committee Debate successfully convened via Gemini 3 Pro.", 4, 'SUCCESS');
      }

      setResult(response);
    } catch (e) {
      console.error(e);
      if (onLog) onLog("Agent 4: CRITICAL FAILURE. Unable to generate analysis.", 4, 'ERROR');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel rounded-3xl p-8 h-full flex flex-col relative overflow-hidden border border-white/5 organic-glow">
      {/* Background Decor */}
      <div className="absolute -right-20 -top-20 w-60 h-60 bg-purple-500/10 blur-[80px] rounded-full pointer-events-none"></div>

      <div className="mb-8 z-10 text-center">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-br from-purple-500/20 to-purple-900/20 border border-purple-500/30 mb-4 shadow-[0_0_20px_rgba(168,85,247,0.2)]">
          <span className="text-xl">🧠</span>
        </div>
        <h2 className="text-2xl font-bold text-white font-tech uppercase tracking-widest">
          The Analyst
        </h2>
        <p className="text-gray-400 text-xs font-mono mt-2 max-w-md mx-auto">
          Input a market hypothesis to convene the AI Committee (Gemini 3 Pro)
        </p>
      </div>

      <div className="flex gap-3 mb-8 z-10 max-w-2xl mx-auto w-full">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. Will Fed cut rates in September?"
          className="flex-1 bg-black/30 border border-white/10 text-emerald-100 px-6 py-4 rounded-2xl focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50 transition-all text-sm font-mono placeholder-gray-600 shadow-inner"
          onKeyDown={(e) => e.key === 'Enter' && handleDebate()}
        />
        <button
          onClick={handleDebate}
          disabled={loading}
          className="bg-purple-600 hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-8 py-4 rounded-2xl font-bold transition-all uppercase text-xs tracking-widest shadow-lg hover:shadow-purple-500/30 hover:-translate-y-0.5 active:translate-y-0"
        >
          {loading ? (
            <span className="animate-pulse">thinking...</span>
          ) : 'ANALYZE'}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto no-scrollbar z-10 relative">
        {loading && (
          <div className="flex flex-col items-center justify-center h-48 space-y-6">
            <div className="relative w-16 h-16">
              <div className="absolute inset-0 border-4 border-purple-500/30 rounded-full"></div>
              <div className="absolute inset-0 border-4 border-t-purple-500 rounded-full animate-spin"></div>
            </div>
            <div className="text-purple-400 font-mono text-xs animate-pulse">Processing High-Dimensional Context...</div>
          </div>
        )}

        {result && (
          <div className="space-y-6 animate-[fadeIn_0.5s_ease-out] pb-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Optimist Card */}
              <div className="bg-emerald-900/10 border border-emerald-500/20 p-6 rounded-3xl backdrop-blur-sm relative overflow-hidden group hover:border-emerald-500/40 transition-colors">
                <div className="absolute top-0 right-0 w-20 h-20 bg-emerald-500/10 blur-[40px] rounded-full group-hover:bg-emerald-500/20 transition-all"></div>
                <h3 className="text-emerald-400 font-bold mb-3 text-xs uppercase tracking-widest flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500"></span> The Optimist
                </h3>
                <p className="text-gray-300 text-sm leading-relaxed font-mono opacity-90">{result.optimistArg}</p>
              </div>

              {/* Pessimist Card */}
              <div className="bg-red-900/10 border border-red-500/20 p-6 rounded-3xl backdrop-blur-sm relative overflow-hidden group hover:border-red-500/40 transition-colors">
                <div className="absolute top-0 right-0 w-20 h-20 bg-red-500/10 blur-[40px] rounded-full group-hover:bg-red-500/20 transition-all"></div>
                <h3 className="text-red-400 font-bold mb-3 text-xs uppercase tracking-widest flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-red-500"></span> The Pessimist
                </h3>
                <p className="text-gray-300 text-sm leading-relaxed font-mono opacity-90">{result.pessimistArg}</p>
              </div>
            </div>

            {/* Verdict Card */}
            <div className="bg-gradient-to-r from-blue-900/20 to-purple-900/20 border border-blue-500/30 p-8 rounded-3xl relative overflow-hidden shadow-2xl">
              <div className="flex justify-between items-start mb-4 relative z-10">
                <h3 className="text-blue-300 font-bold text-xl uppercase tracking-widest font-tech">Final Verdict</h3>
                <div className="px-4 py-1.5 rounded-full bg-black/40 border border-white/10 flex items-center gap-2">
                  <span className="text-[10px] text-gray-400 uppercase tracking-widest">Confidence</span>
                  <span className={`text-lg font-mono font-bold ${result.confidenceScore > 70 ? 'text-emerald-400' : result.confidenceScore > 40 ? 'text-yellow-400' : 'text-red-400'}`}>
                    {result.confidenceScore}%
                  </span>
                </div>
              </div>
              <p className="text-white text-lg font-medium leading-relaxed font-mono relative z-10">
                "{result.judgeVerdict}"
              </p>
            </div>
          </div>
        )}

        {!loading && !result && (
          <div className="flex flex-col items-center justify-center h-full opacity-20">
            <div className="text-6xl mb-4 grayscale">⚖️</div>
            <span className="font-mono text-xs uppercase tracking-[0.2em]">Awaiting Hypothesis</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default MarketAnalysis;