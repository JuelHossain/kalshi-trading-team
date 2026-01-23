import React, { useState, useEffect, useMemo } from 'react';

type TransactionType = 'PROFIT' | 'LOSS' | 'ASSET_ADDED' | 'WITHDRAWAL' | 'IDLE';
type TimeRange = '3D' | '1W' | '1M' | '3M' | '6M' | 'YTD';

interface DayData {
    id: string;
    dateObj: Date;
    date: string;
    fullDate: string;
    type: TransactionType;
    amount: number;
    reasoning: string;
}

const COLORS = {
    PROFIT_XL: '#10b981', // Emerald 500
    PROFIT_L: '#34d399',  // Emerald 400
    PROFIT_M: '#059669',  // Emerald 600
    PROFIT_S: '#064e3b',  // Emerald 900
    LOSS_L: '#ef4444',    // Red 500
    LOSS_S: '#7f1d1d',    // Red 900
    ASSET: '#fbbf24',     // Amber 400
    WITHDRAW: '#3b82f6',  // Blue 500
    IDLE: 'rgba(255,255,255,0.05)',
};

const RANGES: TimeRange[] = ['3D', '1W', '1M', '3M', '6M', 'YTD'];

const PnLHeatmap: React.FC = () => {
    const [activeRange, setActiveRange] = useState<TimeRange>('YTD');
    const [data, setData] = useState<DayData[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedDay, setSelectedDay] = useState<DayData | null>(null);

    // Initialize Data
    useEffect(() => {
        fetchHeatmapData();
    }, []);

    // Update selection when data or range changes
    useEffect(() => {
        if (data.length > 0) {
            // Default to the last day (today)
            setSelectedDay(data[data.length - 1]);
        }
    }, [data]);

    const fetchHeatmapData = async () => {
        setLoading(true);
        try {
            const url = `http://${window.location.hostname}:3001/api/pnl/heatmap`;
            const res = await fetch(url);
            if (!res.ok) throw new Error("API Failure");
            const raw = await res.json();

            // Process RAW data (assuming array of {created_at, balance_cents})
            // We need to group by day and calculate diff
            const daysMap = new Map<string, number>(); // DateString -> CloseBalance

            raw.forEach((r: any) => {
                const dt = new Date(r.created_at).toISOString().split('T')[0];
                daysMap.set(dt, r.balance_cents / 100);
            });

            // Now generate contiguous day list
            const days: DayData[] = [];
            const today = new Date();
            const totalDays = 365;

            let prevBalance = 300; // Base principal assumption
            // Optimization: Sort keys
            const sortedDates = Array.from(daysMap.keys()).sort();
            if (sortedDates.length > 0) {
                // Find finding close balance before start if possible
                // For now, simpler approach: just map the last year
            }

            for (let i = totalDays; i >= 0; i--) {
                const date = new Date(today);
                date.setDate(date.getDate() - i);
                const dateKey = date.toISOString().split('T')[0];

                const closeBalance = daysMap.get(dateKey);

                let type: TransactionType = 'IDLE';
                let amount = 0;
                let reasoning = 'No trading activity detected.';

                if (closeBalance !== undefined) {
                    amount = closeBalance - prevBalance;
                    prevBalance = closeBalance; // Update for next day

                    if (amount > 0) {
                        type = 'PROFIT';
                        reasoning = `Net Profit: $${amount.toFixed(2)}`;
                    } else if (amount < 0) {
                        type = 'LOSS';
                        reasoning = `Net Loss: $${amount.toFixed(2)}`;
                    } else {
                        type = 'IDLE';
                    }
                }

                days.push({
                    id: date.toISOString(),
                    dateObj: date,
                    date: date.toLocaleDateString('en-US', { day: 'numeric', month: 'short' }),
                    fullDate: date.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }),
                    type,
                    amount: parseFloat(amount.toFixed(2)),
                    reasoning
                });
            }

            setData(days);
            setLoading(false);

        } catch (e) {
            console.error("Heatmap Fetch Error:", e);
            // Fallback to empty
            setData([]);
            setLoading(false);
        }
    };

    const filteredData = useMemo(() => {
        const now = new Date();
        let daysBack = 0;

        switch (activeRange) {
            case '3D': daysBack = 3; break;
            case '1W': daysBack = 7; break;
            case '1M': daysBack = 30; break;
            case '3M': daysBack = 90; break;
            case '6M': daysBack = 180; break;
            case 'YTD':
                const startOfYear = new Date(now.getFullYear(), 0, 1);
                daysBack = Math.floor((now.getTime() - startOfYear.getTime()) / (1000 * 60 * 60 * 24));
                break;
        }

        return data.slice(-daysBack);
    }, [activeRange, data]);

    const getCellStyle = (day: DayData) => {
        let backgroundColor = COLORS.IDLE;
        if (day.type === 'PROFIT') {
            if (day.amount > 120) backgroundColor = COLORS.PROFIT_XL;
            else if (day.amount > 80) backgroundColor = COLORS.PROFIT_L;
            else if (day.amount > 40) backgroundColor = COLORS.PROFIT_M;
            else backgroundColor = COLORS.PROFIT_S;
        } else if (day.type === 'LOSS') {
            if (day.amount < -50) backgroundColor = COLORS.LOSS_L;
            else backgroundColor = COLORS.LOSS_S;
        } else if (day.type === 'ASSET_ADDED') backgroundColor = COLORS.ASSET;
        else if (day.type === 'WITHDRAWAL') backgroundColor = COLORS.WITHDRAW;

        return { backgroundColor };
    };

    const isListView = activeRange === '3D' || activeRange === '1W';

    return (
        <div className="glass-panel rounded-2xl h-full flex flex-col relative overflow-hidden border border-white/5">
            {/* Top Bar: Filters */}
            <div className="flex justify-between items-center p-4 border-b border-white/5 bg-black/20 shrink-0">
                <h3 className="text-gray-300 font-bold font-tech uppercase tracking-widest text-xs flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    Chronos Grid
                </h3>

                <div className="flex bg-black/40 rounded-lg p-1 border border-white/5">
                    {RANGES.map(range => (
                        <button
                            key={range}
                            onClick={() => setActiveRange(range)}
                            className={`
                            px-2 py-0.5 text-[9px] font-mono rounded-md transition-all duration-300
                            ${activeRange === range
                                    ? 'bg-emerald-500/20 text-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.2)] font-bold'
                                    : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'}
                        `}
                        >
                            {range}
                        </button>
                    ))}
                </div>
            </div>

            {/* Main Content Area: Split View */}
            <div className="flex flex-1 overflow-hidden">

                {/* Left: Visualization Grid/List */}
                <div className="flex-1 p-4 overflow-y-auto overflow-x-hidden relative">
                    {loading ? (
                        <div className="absolute inset-0 flex items-center justify-center">
                            <div className="flex flex-col items-center gap-2">
                                <div className="w-6 h-6 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin"></div>
                                <span className="text-[10px] text-emerald-500/50 font-mono animate-pulse">SYNCING CHAIN...</span>
                            </div>
                        </div>
                    ) : (
                        <>
                            {isListView ? (
                                <div className="flex flex-col gap-2">
                                    {filteredData.map(day => (
                                        <div
                                            key={day.id}
                                            onMouseEnter={() => setSelectedDay(day)}
                                            className={`
                                            flex items-center justify-between p-3 rounded-xl border transition-all cursor-pointer group
                                            ${selectedDay?.id === day.id
                                                    ? 'bg-white/10 border-emerald-500/50 shadow-lg translate-x-1'
                                                    : 'bg-white/5 border-white/5 hover:bg-white/10 hover:border-white/10'}
                                        `}
                                        >
                                            <div className="flex items-center gap-4">
                                                <div
                                                    className="w-2 h-10 rounded-full"
                                                    style={getCellStyle(day)}
                                                ></div>
                                                <div>
                                                    <div className="text-xs font-bold text-gray-200">{day.fullDate}</div>
                                                    <div className="text-[10px] text-gray-500 font-mono truncate max-w-[150px]">{day.reasoning}</div>
                                                </div>
                                            </div>
                                            <div className={`font-mono font-bold text-sm ${day.amount >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                                {day.amount > 0 ? '+' : ''}{day.amount === 0 ? '--' : `$${day.amount}`}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="flex flex-wrap gap-1.5 content-start">
                                    {filteredData.map(day => (
                                        <div
                                            key={day.id}
                                            onMouseEnter={() => setSelectedDay(day)}
                                            className={`
                                            w-3 h-3 rounded-[2px] cursor-pointer transition-transform duration-200 hover:scale-150 hover:z-20 hover:rounded-sm relative
                                            ${selectedDay?.id === day.id ? 'ring-1 ring-white scale-125 z-10' : ''}
                                        `}
                                            style={getCellStyle(day)}
                                        ></div>
                                    ))}
                                </div>
                            )}
                        </>
                    )}
                </div>

                {/* Right: Info Details Long on the Side */}
                <div className="w-[180px] bg-black/20 border-l border-white/5 p-4 flex flex-col shrink-0 backdrop-blur-sm relative z-10">
                    {selectedDay ? (
                        <div className="animate-[fadeIn_0.3s_ease-out]">
                            <div className="mb-4">
                                <span className="text-[9px] text-gray-500 font-mono uppercase tracking-widest block mb-1">Selected Date</span>
                                <div className="text-xl font-bold text-white leading-tight font-tech">{selectedDay.dateObj.getDate()}</div>
                                <div className="text-xs text-gray-400 font-mono uppercase">{selectedDay.dateObj.toLocaleString('default', { month: 'long', year: 'numeric' })}</div>
                                <div className="text-[10px] text-gray-600 font-mono">{selectedDay.dateObj.toLocaleString('default', { weekday: 'long' })}</div>
                            </div>

                            <div className="w-full h-[1px] bg-white/10 my-2"></div>

                            <div className="mb-4">
                                <span className="text-[9px] text-gray-500 font-mono uppercase tracking-widest block mb-1">Net Result</span>
                                <div className={`text-2xl font-black font-tech tracking-tight ${selectedDay.amount >= 0 ? 'text-emerald-400 drop-shadow-[0_0_8px_rgba(52,211,153,0.3)]' : 'text-red-400 drop-shadow-[0_0_8px_rgba(248,113,113,0.3)]'}`}>
                                    {selectedDay.amount > 0 ? '+' : ''}{selectedDay.amount === 0 ? 'IDLE' : `$${selectedDay.amount}`}
                                </div>
                            </div>

                            <div className="flex-1 overflow-y-auto no-scrollbar">
                                <span className="text-[9px] text-gray-500 font-mono uppercase tracking-widest block mb-2">AI Reasoning</span>
                                <div className="p-2 bg-white/5 rounded-lg border border-white/5">
                                    <p className="text-[10px] text-gray-300 leading-relaxed font-mono">
                                        "{selectedDay.reasoning}"
                                    </p>
                                </div>

                                <div className="mt-3">
                                    <span className={`inline-block px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider
                                    ${selectedDay.type === 'PROFIT' ? 'bg-emerald-500/20 text-emerald-400' :
                                            selectedDay.type === 'LOSS' ? 'bg-red-500/20 text-red-400' :
                                                selectedDay.type === 'ASSET_ADDED' ? 'bg-amber-500/20 text-amber-400' : 'bg-gray-700 text-gray-400'}
                                `}>
                                        {selectedDay.type.replace('_', ' ')}
                                    </span>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="h-full flex flex-col items-center justify-center opacity-30 text-center">
                            <div className="text-2xl mb-2">📅</div>
                            <span className="text-[9px] font-mono uppercase">Select a day</span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default PnLHeatmap;