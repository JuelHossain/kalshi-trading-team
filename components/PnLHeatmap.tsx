import React, { useState, useEffect } from 'react';

type TransactionType = 'PROFIT' | 'LOSS' | 'ASSET_ADDED' | 'WITHDRAWAL' | 'IDLE';

interface DayData {
  date: string;
  type: TransactionType;
  amount: number;
  reasoning: string;
}

const COLORS = {
  PROFIT_XL: '#00FF41',
  PROFIT_L: '#00C42E',
  PROFIT_M: '#008F24',
  PROFIT_S: '#005C17',
  LOSS_L: '#FF3131',
  LOSS_S: '#991B1B',
  ASSET: '#F1C40F',
  WITHDRAW: '#3498DB',
  IDLE: '#111111',
};

const PnLHeatmap: React.FC = () => {
  const [data, setData] = useState<DayData[][]>([]);
  const [loading, setLoading] = useState(true);
  const [hoveredDay, setHoveredDay] = useState<DayData | null>(null);

  useEffect(() => {
    const fetchData = async () => {
        setLoading(true);
        await new Promise(resolve => setTimeout(resolve, 1200));
        setData(generateCalendarData());
        setLoading(false);
    };
    fetchData();
  }, []);

  const generateCalendarData = (): DayData[][] => {
    const weeks: DayData[][] = [];
    const totalWeeks = 24; 
    const now = new Date();
    
    for (let w = 0; w < totalWeeks; w++) {
      const week: DayData[] = [];
      for (let d = 0; d < 7; d++) {
        const date = new Date(now);
        date.setDate(date.getDate() - ((totalWeeks - 1 - w) * 7) + d);
        let type: TransactionType = 'IDLE';
        let amount = 0;
        let reasoning = 'No Market Activity';

        const seed = Math.sin(w * 7 + d) * 10000;
        const rand = seed - Math.floor(seed);

        if (rand > 0.4) { 
          if (rand > 0.96) {
              type = 'WITHDRAWAL';
              amount = -150;
              reasoning = 'Agent 1: Vault Overflow -> Bank';
          } else if (rand > 0.93) {
              type = 'ASSET_ADDED';
              amount = 200;
              reasoning = 'Agent 1: Weekly Liquidity Inject';
          } else if (rand > 0.85) {
              type = 'LOSS';
              const lossSeverity = Math.random();
              amount = -Math.floor(lossSeverity * 80) - 10;
              reasoning = amount < -50 ? 'Agent 6: Bull Trap Triggered' : 'Agent 3: Odds Lag Slippage';
          } else {
              type = 'PROFIT';
              const profitMagnitude = Math.random();
              amount = Math.floor(profitMagnitude * profitMagnitude * 250) + 15; 
              if (amount > 150) reasoning = 'Agent 2: Whale Gap Detected (High Conf)';
              else if (amount > 100) reasoning = 'Agent 4: Committee Consensus YES';
              else if (amount > 50) reasoning = 'Agent 7: Order Book Front-run';
              else reasoning = 'Agent 5: Scalp (EV +4.2)';
          }
        }
        week.push({
          date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
          type,
          amount,
          reasoning
        });
      }
      weeks.push(week);
    }
    return weeks;
  };

  const getStyle = (day: DayData) => {
    let backgroundColor = COLORS.IDLE;
    if (day.type === 'PROFIT') {
        if (day.amount > 150) backgroundColor = COLORS.PROFIT_XL;
        else if (day.amount > 100) backgroundColor = COLORS.PROFIT_L;
        else if (day.amount > 50) backgroundColor = COLORS.PROFIT_M;
        else backgroundColor = COLORS.PROFIT_S;
    } else if (day.type === 'LOSS') {
        if (day.amount < -50) backgroundColor = COLORS.LOSS_L;
        else backgroundColor = COLORS.LOSS_S;
    } else if (day.type === 'ASSET_ADDED') backgroundColor = COLORS.ASSET;
    else if (day.type === 'WITHDRAWAL') backgroundColor = COLORS.WITHDRAW;
    return { backgroundColor };
  };

  return (
    <div className="cyber-card h-full relative group bg-black/40">
       <div className="corner corner-tl"></div>
       <div className="corner corner-tr"></div>
       <div className="corner corner-br"></div>
       <div className="corner corner-bl"></div>

       <div className="absolute inset-[1px] flex flex-col p-4 rounded-[1px] overflow-hidden">
           
           {/* Header Area */}
           <div className="flex justify-between items-start mb-2 shrink-0">
                <div className="flex flex-col">
                    <h3 className="text-gray-200 font-bold font-mono text-[10px] uppercase tracking-widest flex items-center gap-2">
                        <span className="text-emerald-500 animate-pulse">◆</span> Historical Grid
                    </h3>
                    <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[9px] text-gray-500 font-mono">DB: Agent_10</span>
                        {loading ? (
                            <span className="text-[9px] text-amber-500 font-mono animate-pulse">SYNCING...</span>
                        ) : (
                            <span className="text-[9px] text-emerald-800 font-mono">LINKED</span>
                        )}
                    </div>
                </div>

                {/* Inspector Panel - Replaces Floating Tooltip */}
                <div className="h-10 w-48 border border-gray-800 bg-black/80 flex flex-col justify-center px-2 relative overflow-hidden">
                    {hoveredDay ? (
                        <div className="animate-[fadeIn_0.1s]">
                            <div className="flex justify-between items-center border-b border-gray-800/50 pb-0.5 mb-0.5">
                                <span className="text-[9px] text-gray-400 font-mono">{hoveredDay.date}</span>
                                <span className={`text-[8px] font-bold ${hoveredDay.amount >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                                    {hoveredDay.amount >= 0 ? '+' : ''}${hoveredDay.amount}
                                </span>
                            </div>
                            <div className="text-[8px] text-emerald-400/70 truncate font-mono">
                                {hoveredDay.reasoning}
                            </div>
                        </div>
                    ) : (
                         <div className="text-[8px] text-gray-700 font-mono uppercase text-center tracking-widest">
                            Hover Node to Inspect
                         </div>
                    )}
                    {/* Decorative Scanline inside Inspector */}
                    <div className="absolute top-0 left-0 w-full h-[1px] bg-emerald-500/20 animate-[packetTravel_2s_linear_infinite]"></div>
                </div>
           </div>

           {/* Heatmap Grid */}
           <div className="flex-1 relative flex items-center justify-center overflow-hidden">
             {loading ? (
                <div className="font-mono text-xs text-emerald-500/50 flex flex-col items-center gap-2">
                    <div className="w-6 h-6 border-2 border-emerald-900 border-t-emerald-500 rounded-full animate-spin"></div>
                    <div className="text-[10px]">DECRYPTING...</div>
                </div>
             ) : (
                 <div className="flex gap-[2px] h-full items-center overflow-x-auto custom-scrollbar pb-1 w-full justify-start">
                    {data.map((week, wIndex) => (
                        <div key={wIndex} className="flex flex-col gap-[2px]">
                            {week.map((day, dIndex) => (
                                <div 
                                    key={dIndex} 
                                    className="w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-[1px] transition-all duration-150 hover:scale-125 hover:z-50 hover:ring-1 hover:ring-white cursor-crosshair relative"
                                    style={getStyle(day)}
                                    onMouseEnter={() => setHoveredDay(day)}
                                    onMouseLeave={() => setHoveredDay(null)}
                                />
                            ))}
                        </div>
                    ))}
                 </div>
             )}
           </div>
       </div>
    </div>
  );
};

export default PnLHeatmap;
