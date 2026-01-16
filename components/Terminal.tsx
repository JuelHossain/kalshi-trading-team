import React, { useEffect, useRef } from 'react';
import { LogEntry } from '../types';

interface TerminalProps {
  logs: LogEntry[];
}

const Terminal: React.FC<TerminalProps> = ({ logs }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="cyber-card h-full relative group bg-black/40">
      {/* 1. Holographic Corners (Outside the overflow container) */}
      <div className="corner corner-tl"></div>
      <div className="corner corner-tr"></div>
      <div className="corner corner-br"></div>
      <div className="corner corner-bl"></div>

      {/* 2. Inner Content Shell (Clips content, preserves corners) */}
      <div className="absolute inset-[1px] flex flex-col overflow-hidden rounded-[1px]">
          
          {/* Header */}
          <div className="flex justify-between items-center p-3 border-b border-gray-800/50 bg-black/20 backdrop-blur-md z-20 shrink-0">
            <h3 className="text-emerald-500 font-bold uppercase tracking-widest text-xs flex items-center gap-2">
              <span className="w-1.5 h-1.5 bg-emerald-500 rounded-sm animate-pulse shadow-[0_0_5px_#10b981]"></span>
              Live Trace // <span className="text-gray-500">Net_IO</span>
            </h3>
            <div className="flex gap-1 opacity-50">
              <span className="w-0.5 h-2 bg-emerald-900"></span>
              <span className="w-0.5 h-2 bg-emerald-800"></span>
              <span className="w-0.5 h-2 bg-emerald-700"></span>
            </div>
          </div>

          {/* Scrollable Log Area */}
          <div className="flex-1 overflow-y-auto p-3 space-y-1 scroll-smooth custom-scrollbar relative z-10 font-mono text-[10px] leading-relaxed">
            {/* Scanline Overlay for the terminal area specifically */}
            <div className="absolute inset-0 pointer-events-none bg-[url('https://www.transparenttextures.com/patterns/diagmonds-light.png')] opacity-[0.03] fixed"></div>

            {logs.length === 0 && (
                <div className="text-gray-600 italic p-2 opacity-50">
                    {'>'} System initialized...<br/>
                    {'>'} Awaiting datastream...
                </div>
            )}
            {logs.map(log => (
              <div key={log.id} className="flex gap-3 hover:bg-emerald-500/5 p-1 rounded-[1px] transition-colors border-l-2 border-transparent hover:border-emerald-500/30 animate-[fadeIn_0.1s_ease-out] group/line">
                <span className="text-gray-600 shrink-0 select-none w-14 opacity-70">[{log.timestamp.split('.')[0]}]</span>
                <span className={`font-bold shrink-0 w-16 tracking-tighter ${
                  log.level === 'INFO' ? 'text-blue-400' :
                  log.level === 'SUCCESS' ? 'text-emerald-400' :
                  log.level === 'WARN' ? 'text-amber-400' : 'text-red-500'
                }`}>
                  {log.level}
                </span>
                <span className="text-gray-400 group-hover/line:text-gray-200 transition-colors break-words flex-1">
                    {log.message}
                </span>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Background Watermark */}
          <div className="absolute bottom-2 right-2 text-6xl text-white/[0.015] font-black pointer-events-none select-none z-0 tracking-tighter">
            TERMINAL
          </div>
      </div>
    </div>
  );
};

export default Terminal;
