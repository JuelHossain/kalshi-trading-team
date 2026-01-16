import React, { useState } from 'react';
import { runCommitteeDebate } from '../services/geminiService';
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
      
      // Check if it was a fallback response by checking the text content
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
    <div className="cyber-card rounded-sm p-6 h-full flex flex-col relative">
       {/* Holographic Corners */}
       <div className="corner corner-tl"></div>
       <div className="corner corner-tr"></div>
       <div className="corner corner-br"></div>
       <div className="corner corner-bl"></div>

      <div className="mb-6 z-10">
        <h2 className="text-xl font-bold text-white mb-2 flex items-center gap-2 font-tech uppercase tracking-widest">
          <span className="text-purple-400 animate-[spin-slow_4s_linear_infinite] block text-xs">◆</span> 
          Agent 4: The Analyst
        </h2>
        <p className="text-gray-400 text-xs font-mono">Input hypothesis for committee validation.</p>
      </div>

      <div className="flex gap-2 mb-6 z-10">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="ENTER_MARKET_HYPOTHESIS..."
          className="flex-1 bg-black/50 border border-gray-700 text-emerald-400 px-4 py-3 rounded-[2px] focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all text-sm font-mono placeholder-gray-700"
          onKeyDown={(e) => e.key === 'Enter' && handleDebate()}
        />
        <button
          onClick={handleDebate}
          disabled={loading}
          className="bg-purple-900/20 hover:bg-purple-900/40 disabled:opacity-50 disabled:cursor-not-allowed text-purple-400 px-6 py-2 rounded-[2px] font-bold transition-all uppercase text-xs tracking-wider border border-purple-500/50 shadow-[0_0_15px_rgba(147,51,234,0.1)] hover:shadow-[0_0_20px_rgba(147,51,234,0.3)]"
        >
          {loading ? 'Simulating...' : 'CONVENE'}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar z-10">
        {loading && (
            <div className="flex flex-col items-center justify-center h-48 space-y-4">
                <div className="text-purple-400 font-mono text-xs animate-pulse">Accessing Gemini 3 Pro Context...</div>
                <div className="w-full max-w-md h-1 bg-gray-800 rounded overflow-hidden">
                    <div className="h-full bg-purple-500 w-1/3 animate-[slide_1s_ease-in-out_infinite]"></div>
                </div>
            </div>
        )}

        {result && (
          <div className="space-y-4 animate-[fadeIn_0.5s_ease-out]">
            {result.optimistArg.includes("[LOCAL_FALLBACK]") && (
                <div className="bg-amber-900/20 border border-amber-500/50 p-2 rounded-[1px] text-[10px] text-amber-500 font-mono uppercase tracking-wide flex items-center gap-2">
                    <span className="w-2 h-2 bg-amber-500 rounded-full animate-pulse"></span>
                    Warning: Remote API Unreachable. Showing Local Heuristic Analysis.
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-emerald-900/10 border border-emerald-500/30 p-4 rounded-[2px]">
                <h3 className="text-emerald-400 font-bold mb-2 text-xs uppercase tracking-wide border-b border-emerald-500/20 pb-1">The Optimist</h3>
                <p className="text-gray-300 text-sm leading-relaxed font-mono opacity-80">{result.optimistArg}</p>
              </div>
              <div className="bg-red-900/10 border border-red-500/30 p-4 rounded-[2px]">
                <h3 className="text-red-400 font-bold mb-2 text-xs uppercase tracking-wide border-b border-red-500/20 pb-1">The Pessimist</h3>
                <p className="text-gray-300 text-sm leading-relaxed font-mono opacity-80">{result.pessimistArg}</p>
              </div>
            </div>

            <div className="bg-blue-900/10 border border-blue-500/30 p-6 rounded-[2px] relative overflow-hidden">
              <div className="absolute top-0 left-0 w-1 h-full bg-blue-500 box-shadow-[0_0_10px_blue]"></div>
              <div className="flex justify-between items-start mb-3">
                 <h3 className="text-blue-400 font-bold text-lg uppercase tracking-widest font-tech">The Judge's Verdict</h3>
                 <div className="flex items-center gap-2">
                    <span className="text-[10px] text-gray-500 uppercase tracking-widest">Confidence</span>
                    <span className={`text-xl font-mono font-bold ${result.confidenceScore > 70 ? 'text-green-400' : result.confidenceScore > 40 ? 'text-yellow-400' : 'text-red-400'}`}>
                        {result.confidenceScore}%
                    </span>
                 </div>
              </div>
              <p className="text-gray-200 text-base font-medium leading-relaxed font-mono">
                "{result.judgeVerdict}"
              </p>
            </div>
          </div>
        )}
        
        {!loading && !result && (
            <div className="flex flex-col items-center justify-center h-full text-gray-800 font-mono text-xs uppercase tracking-widest opacity-30">
                <span>[ Awaiting Data Stream ]</span>
            </div>
        )}
      </div>
    </div>
  );
};

export default MarketAnalysis;
