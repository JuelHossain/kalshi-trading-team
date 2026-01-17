import React from 'react';
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';

const data = [
  { time: '09:00', pnl: 300, velocity: 12 },
  { time: '10:00', pnl: 302, velocity: 8 },
  { time: '11:00', pnl: 298, velocity: -4 },
  { time: '12:00', pnl: 305, velocity: 15 },
  { time: '13:00', pnl: 315, velocity: 22 },
  { time: '14:00', pnl: 322, velocity: 18 },
  { time: '15:00', pnl: 345, velocity: 40 },
  { time: '16:00', pnl: 352, velocity: 10 },
  { time: '17:00', pnl: 368, velocity: 25 },
  { time: '18:00', pnl: 385, velocity: 30 },
  { time: '19:00', pnl: 405, velocity: 45 },
];

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
        <div className="text-[10px] text-gray-400 font-mono mb-1 border-b border-gray-800 pb-1">{label} HRS</div>
        <div className="text-lg font-bold text-emerald-400 font-mono">
          ${payload[0].value}
        </div>
        <div className="text-[9px] text-emerald-600 uppercase tracking-wider font-mono mt-1">
          Velocity: {payload[0].payload.velocity} bps
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
  const currentPnL = 405;
  const startPrincipal = 300;
  const profit = currentPnL - startPrincipal;
  const percent = ((profit / startPrincipal) * 100).toFixed(2);

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
            <span className="text-xs font-mono font-bold text-emerald-400 bg-emerald-900/20 px-1.5 py-0.5 rounded border border-emerald-500/20">
              +{percent}%
            </span>
          </div>
        </div>

        {/* Technical Stats Right */}
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
      <div className="flex-1 w-full min-h-0 relative z-10 -ml-2">
        <ResponsiveContainer width="100%" height="100%">
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
            <YAxis domain={['dataMin - 20', 'dataMax + 20']} hide />

            <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#333', strokeWidth: 1, strokeDasharray: '4 4' }} />

            {/* The "Floor" (Principal) */}
            <ReferenceLine y={300} stroke="#333" strokeDasharray="5 5" strokeWidth={1} label={{ position: 'right', value: 'PRINCIPAL', fill: '#444', fontSize: 8, fontFamily: 'monospace' }} />

            {/* The Area Glow */}
            <Area
              type="monotone"
              dataKey="pnl"
              stroke="none"
              fill="url(#cyberGradient)"
            />

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