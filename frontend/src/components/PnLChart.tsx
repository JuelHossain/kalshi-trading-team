import React, { useState, useEffect } from 'react';
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';

interface ChartData {
  time: string;
  pnl: number;
  velocity: number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    payload: {
      velocity: number;
    };
  }>;
  label?: string;
}

const CustomTooltip = ({ active, payload, label }: CustomTooltipProps) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-black/90 border border-emerald-500/50 p-3 rounded-sm shadow-[0_0_20px_rgba(16,185,129,0.2)] backdrop-blur-md">
        <div className="text-[10px] text-gray-400 font-mono mb-1 border-b border-gray-800 pb-1">
          {label} HRS
        </div>
        <div className="text-lg font-bold text-emerald-400 font-mono">
          ${payload[0].value.toFixed(2)}
        </div>
        <div className="text-[9px] text-emerald-600 uppercase tracking-wider font-mono mt-1">
          Velocity: {(payload[0].payload.velocity ?? 0).toFixed(2)} bps
        </div>
      </div>
    );
  }
  return null;
};

interface PulsingDotProps {
  cx?: number;
  cy?: number;
  index?: number;
  dataLength: number;
}

// Custom Dot for the last data point to simulate a "Live" pulse
const PulsingDot = (props: PulsingDotProps) => {
  const { cx, cy, index, dataLength } = props;
  if (index === dataLength - 1) {
    return (
      <g>
        <circle cx={cx} cy={cy} r={4} fill="#10b981" className="animate-ping opacity-75" />
        <circle cx={cx} cy={cy} r={3} fill="#10b981" stroke="#fff" strokeWidth={1} />
      </g>
    );
  }
  return null;
};

const PnLChart: React.FC = () => {
  const [data, setData] = useState<ChartData[]>([]);
  const [currentPnL, setCurrentPnL] = useState(300);
  const [percent, setPercent] = useState('0.00');
  const [loading, setLoading] = useState(true);

  // Hardcoded Principal for now
  const startPrincipal = 300;

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Use relative path (proxied by Vite)
        const url = '/api/pnl';
        const res = await fetch(url);
        if (!res.ok) throw new Error('Failed to fetch');
        const raw = await res.json();
        const history = raw.history || [];

        if (history.length === 0) {
          setData([]);
          setLoading(false);
          return;
        }

        // Transform
        const transformed: ChartData[] = history.map((d: any, i: number) => {
          const prev = i > 0 ? history[i - 1].balance : d.balance;
          const velocity = d.balance - prev;
          const time = new Date(d.timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          });
          return {
            time,
            pnl: d.balance,
            velocity,
          };
        });

        setData(transformed);
        const last = transformed[transformed.length - 1];
        setCurrentPnL(last.pnl);
        const diff = last.pnl - startPrincipal;
        setPercent(((diff / startPrincipal) * 100).toFixed(2));
        setLoading(false);
      } catch (e) {
        console.error('PnL Fetch Error:', e);
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, []);

  if (loading && data.length === 0) {
    return (
      <div className="h-full w-full flex items-center justify-center text-xs text-gray-500 font-mono animate-pulse">
        ACQUIRING FEED...
      </div>
    );
  }

  return (
    <div className="h-full w-full relative bg-black/40 rounded-2xl border border-white/5 overflow-hidden flex flex-col backdrop-blur-sm group">
      {/* Background Grid Texture */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(16,185,129,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(16,185,129,0.03)_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none"></div>

      {/* Header HUD */}
      <div className="flex justify-between items-start p-5 z-20">
        <div>
          <h3 className="text-[10px] font-mono text-emerald-600/80 uppercase tracking-[0.2em] mb-1 flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></span>
            Alpha Seismograph
          </h3>
          <div className="flex items-baseline gap-3">
            <span className="text-3xl font-black text-white font-tech tracking-tighter drop-shadow-[0_0_10px_rgba(16,185,129,0.5)]">
              ${currentPnL.toFixed(2)}
            </span>
            <span
              className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded border border-white/10 ${Number(percent) >= 0 ? 'text-emerald-400 bg-emerald-900/20' : 'text-red-400 bg-red-900/20'}`}
            >
              {Number(percent) >= 0 ? '+' : ''}
              {percent}%
            </span>
          </div>
        </div>

        {/* Technical Stats Right - Static for now, can be hooked up if metrics exist */}
        <div className="text-right hidden sm:block">
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-end gap-2 text-[9px] font-mono text-gray-500 uppercase">
              <span>Win Rate</span>
              <div className="w-16 h-1 bg-gray-800 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 w-[72%]"></div>
              </div>
              <span className="text-emerald-400">72%</span>
            </div>
            <div className="flex items-center justify-end gap-2 text-[9px] font-mono text-gray-500 uppercase">
              <span>Sharpe</span>
              <span className="text-blue-400">2.41</span>
            </div>
          </div>
        </div>
      </div>

      {/* Chart Container */}
      <div
        className="flex-1 w-full min-h-[200px] relative z-10 -ml-2"
        style={{ minHeight: '200px' }}
      >
        <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={200}>
          <ComposedChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="cyberGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
              <filter id="glow" height="300%" width="300%" x="-75%" y="-75%">
                <feGaussianBlur stdDeviation="4" result="coloredBlur" />
                <feMerge>
                  <feMergeNode in="coloredBlur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            <CartesianGrid stroke="#222" strokeDasharray="3 3" vertical={false} />

            <XAxis
              dataKey="time"
              stroke="#444"
              fontSize={9}
              tickLine={false}
              axisLine={false}
              fontFamily="monospace"
              dy={10}
            />

            {/* Hide Y Axis but keep scale */}
            <YAxis domain={['dataMin - 5', 'dataMax + 5']} hide />

            <Tooltip
              content={<CustomTooltip />}
              cursor={{ stroke: '#333', strokeWidth: 1, strokeDasharray: '4 4' }}
            />

            {/* The "Floor" (Principal) */}
            <ReferenceLine
              y={startPrincipal}
              stroke="#333"
              strokeDasharray="5 5"
              strokeWidth={1}
              label={{
                position: 'right',
                value: 'PRINCIPAL',
                fill: '#444',
                fontSize: 8,
                fontFamily: 'monospace',
              }}
            />

            {/* The Area Glow */}
            <Area type="monotone" dataKey="pnl" stroke="none" fill="url(#cyberGradient)" />

            {/* The Sharp Line */}
            <Line
              type="monotone"
              dataKey="pnl"
              stroke="#10b981"
              strokeWidth={2}
              dot={<PulsingDot dataLength={data.length} />}
              activeDot={{ r: 5, strokeWidth: 0, fill: '#fff' }}
              filter="url(#glow)"
              animationDuration={1500}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default PnLChart;
