/**
 * The bottom band: bankroll readout with a sparkline, and the live trace.
 */
import { AC, ACS, E, F, glassStyle, LEVEL_INK, mix, R, SG, SGS, T1, T2, T3, T4 } from './palette';
import { PALETTES } from './palette';
import { useCockpit } from './store';

export function sparkPath(arr: number[], w: number, h: number, close: boolean) {
  if (!arr || arr.length < 2) return { d: '', last: [0, 0] as [number, number] };
  const min = Math.min(...arr) - 2;
  const max = Math.max(...arr) + 2;
  const sx = w / (arr.length - 1);
  const sy = (h - 10) / (max - min || 1);
  const pts = arr.map((v, i) => [i * sx, h - 5 - (v - min) * sy] as [number, number]);
  let d = `M${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
  for (let i = 1; i < pts.length; i++) d += ` L${pts[i][0].toFixed(1)} ${pts[i][1].toFixed(1)}`;
  if (close) d += ` L${w} ${h} L0 ${h} Z`;
  return { d, last: pts[pts.length - 1] };
}

export function Telemetry({ narrow, short }: { narrow: boolean; short: boolean }) {
  const s = useCockpit();
  const pal = PALETTES[s.palette];
  const line = sparkPath(s.spark, 300, 48, false);
  const area = sparkPath(s.spark, 300, 48, true);
  const pnl = s.balance - s.principal;
  const up = pnl >= 0;
  const logs = s.logs.slice().reverse().slice(0, 30);

  return (
    <aside
      style={{
        gridArea: 'tele',
        minWidth: 0,
        minHeight: 0,
        overflow: 'hidden',
        ...glassStyle(pal),
        borderRadius: 0,
        borderWidth: '1px 0 0 0',
      }}
    >
      <div
        style={{
          height: '100%',
          display: 'grid',
          minHeight: 0,
          gridTemplateColumns: narrow ? 'minmax(0,1fr)' : '240px minmax(0,1fr)',
          gridTemplateRows: 'minmax(0,1fr)',
        }}
      >
        {!narrow && (
          <div style={{ minWidth: 0, padding: '14px 18px', borderRight: `1px solid ${mix(E, 70)}` }}>
            <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: T4 }}>Bankroll</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginTop: 4, flexWrap: 'wrap' }}>
              <span className="num" style={{ fontFamily: 'var(--font-heading)', fontSize: 30, lineHeight: 1, color: T1 }}>
                ${s.balance.toFixed(2)}
              </span>
              <span className="num" style={{ fontSize: 13, fontWeight: 600, color: up ? SG : AC }}>
                {s.balance ? `${up ? '+' : ''}${((pnl / s.principal) * 100).toFixed(2)}%` : '—'}
              </span>
            </div>
            <svg viewBox="0 0 300 48" preserveAspectRatio="none" style={{ width: '100%', height: 38, display: 'block', marginTop: 10, overflow: 'visible' }}>
              <defs>
                <linearGradient id="saSparkGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" style={{ stopColor: SGS, stopOpacity: 0.32 }} />
                  <stop offset="100%" style={{ stopColor: SGS, stopOpacity: 0 }} />
                </linearGradient>
              </defs>
              <path d={area.d} fill="url(#saSparkGrad)" />
              <path d={line.d} fill="none" strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" style={{ stroke: SGS }} />
              {line.d && <circle cx={line.last[0].toFixed(1)} cy={line.last[1].toFixed(1)} r="3" style={{ fill: SGS }} />}
            </svg>
            {!short && (
              <div style={{ fontSize: 10, color: F, marginTop: 6 }}>
                {s.spark.length < 2 ? 'Sparkline fills as the vault reports' : `${s.spark.length} readings · principal $${s.principal.toFixed(0)}`}
              </div>
            )}
          </div>
        )}

        <div style={{ minWidth: 0, minHeight: 0, display: 'flex', flexDirection: 'column', padding: narrow ? '12px 16px' : '14px 18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, flex: 'none', paddingBottom: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
              <span
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: 999,
                  background: s.paused ? F : s.connected ? SGS : ACS,
                  animation: s.paused ? undefined : 'saBreathe 1.8s ease-in-out infinite',
                }}
              />
              <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: T3 }}>
                Trace{s.connected ? '' : ' · engine unreachable'}
              </span>
            </div>
            <button
              onClick={s.togglePause}
              style={{
                border: `1px solid ${E}`,
                background: 'transparent',
                color: T3,
                borderRadius: 999,
                padding: '4px 12px',
                fontSize: 10,
                fontWeight: 600,
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
                cursor: 'pointer',
              }}
            >
              {s.paused ? 'resume' : 'pause'}
            </button>
          </div>
          <div className="sc" style={{ flex: 1, minHeight: 0, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 2, margin: '0 -8px', padding: '0 8px' }}>
            {logs.map((l) => {
              const ink = LEVEL_INK[l.level] || T3;
              return (
                <div
                  key={l.id}
                  style={{
                    display: 'flex',
                    gap: 9,
                    alignItems: 'baseline',
                    padding: '6px 9px',
                    borderRadius: R,
                    color: l.level === 'info' ? T2 : ink,
                    background: l.level === 'info' ? 'transparent' : mix(l.level === 'ok' ? SGS : ACS, 10),
                  }}
                >
                  <span className="num" style={{ fontSize: 10, color: F, flex: 'none' }}>
                    {l.t}
                  </span>
                  <span style={{ flex: 'none', width: 56, fontSize: 10, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: ink }}>
                    {l.agent}
                  </span>
                  <span style={{ flex: 1, minWidth: 0, fontSize: 12, lineHeight: 1.5 }}>{l.msg}</span>
                </div>
              );
            })}
            {logs.length === 0 && <div style={{ fontSize: 12, color: T4, padding: '6px 9px' }}>Waiting for the engine…</div>}
          </div>
        </div>
      </div>
    </aside>
  );
}
