/**
 * The Config view: the limits the Soul enforces, the autopilot switch and
 * the kill switch. Limits are the engine's v1 constants
 * (engine/core/constants.py); the switches call the engine.
 */
import type { CSSProperties } from 'react';
import { AC, ACI, ACS, E, G, glassStyle, mix, RL, SG, T1, T3, T4 } from './palette';
import { PALETTES } from './palette';
import { useCockpit } from './store';

const LIMITS = [
  { label: 'Max stake / trade', value: '$75', pct: 25, c: AC, note: 'HAND_MAX_STAKE_CENTS. Kelly sizing is capped here whatever the edge.' },
  { label: 'Minimum edge to trade', value: '+0.05', pct: 55, c: SG, note: 'BRAIN_MIN_EDGE. Thinner than this is logged as a veto and dropped.' },
  { label: 'Execution queue cap', value: '10', pct: 30, c: AC, note: 'MAX_EXECUTION_QUEUE_SIZE. The star stops emitting when the store is full.' },
  { label: 'Hard floor', value: '$255', pct: 94, c: SG, note: 'HARD_FLOOR_CENTS. No cycle is authorised below it; kill switch at 85% of principal.' },
];

export function Guardrails({
  narrow,
  onAutopilot,
  onKill,
}: {
  narrow: boolean;
  onAutopilot: (enabled: boolean) => void;
  onKill: (engaged: boolean) => void;
}) {
  const s = useCockpit();
  const pal = PALETTES[s.palette];
  const glassCard: CSSProperties = { borderRadius: RL, padding: 20, ...glassStyle(pal) };

  return (
    <div
      className="sc"
      style={{
        flex: 1,
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: 18,
        overflowY: 'auto',
        overflowX: 'hidden',
        padding: narrow ? 16 : '22px 26px',
      }}
    >
      <div style={{ flex: 'none' }}>
        <h1 style={{ fontFamily: 'var(--font-heading)', fontWeight: 400, fontSize: 30, margin: 0, color: T1 }}>Guardrails</h1>
        <div style={{ fontSize: 13, color: T3, marginTop: 6, maxWidth: '62ch', textWrap: 'pretty' }}>
          The constitution the Soul enforces. Every line here is a hard limit, not a preference.
        </div>
      </div>
      <div className="sc" style={{ flex: 1, minHeight: 200, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 14, margin: '0 -4px', padding: '0 4px 4px' }}>
        <div style={{ display: 'grid', gap: 14, gridTemplateColumns: `repeat(auto-fit,minmax(${narrow ? 220 : 250}px,1fr))` }}>
          {LIMITS.map((l) => (
            <div key={l.label} style={glassCard}>
              <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.09em', textTransform: 'uppercase', color: T4 }}>{l.label}</div>
              <div className="num" style={{ fontFamily: 'var(--font-heading)', fontSize: 28, color: T1, marginTop: 6 }}>
                {l.value}
              </div>
              <div style={{ height: 4, borderRadius: 999, background: E, marginTop: 12, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${l.pct}%`, borderRadius: 999, background: l.c }} />
              </div>
              <div style={{ fontSize: 12, color: T3, marginTop: 10, textWrap: 'pretty' }}>{l.note}</div>
            </div>
          ))}
        </div>
        <div style={{ display: 'grid', gap: 14, gridTemplateColumns: `repeat(auto-fit,minmax(${narrow ? 220 : 270}px,1fr))` }}>
          <div style={glassCard}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontFamily: 'var(--font-heading)', fontSize: 19, color: T1 }}>Autopilot</div>
                <div style={{ fontSize: 12, color: T3, marginTop: 5, textWrap: 'pretty' }}>
                  {s.autopilot
                    ? 'The Soul starts a new cycle after each one completes without asking you first.'
                    : 'Every cycle waits for you to press Run cycle.'}
                </div>
              </div>
              <button
                onClick={() => onAutopilot(!s.autopilot)}
                aria-label={`Autopilot ${s.autopilot ? 'on' : 'off'}`}
                disabled={s.kill}
                style={{
                  flex: 'none',
                  position: 'relative',
                  width: 52,
                  height: 30,
                  borderRadius: 999,
                  border: `1px solid ${s.autopilot ? ACS : E}`,
                  background: s.autopilot ? ACS : mix(G, 60),
                  cursor: s.kill ? 'not-allowed' : 'pointer',
                  padding: 0,
                  transition: 'background 0.2s',
                  opacity: s.kill ? 0.5 : 1,
                }}
              >
                <span
                  style={{
                    position: 'absolute',
                    top: 3,
                    left: s.autopilot ? 25 : 3,
                    width: 22,
                    height: 22,
                    borderRadius: 999,
                    background: s.autopilot ? ACI : T4,
                    transition: 'left 0.2s',
                  }}
                />
              </button>
            </div>
          </div>
          <div style={{ ...glassCard, borderColor: s.kill ? mix(ACS, 60, E) : mix(E, 70) }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontFamily: 'var(--font-heading)', fontSize: 19, color: T1 }}>Kill switch</div>
                <div style={{ fontSize: 12, color: T3, marginTop: 5, textWrap: 'pretty' }}>
                  {s.kill
                    ? 'Halted. No agent can move capital until you release it.'
                    : 'Stops every agent immediately and blocks all new orders.'}
                </div>
              </div>
              <button
                onClick={() => onKill(!s.kill)}
                style={{
                  flex: 'none',
                  border: `1px solid ${ACS}`,
                  background: s.kill ? 'transparent' : ACS,
                  color: s.kill ? AC : ACI,
                  borderRadius: 999,
                  padding: '10px 22px',
                  fontWeight: 600,
                  fontSize: 14,
                  cursor: 'pointer',
                }}
              >
                {s.kill ? 'Release' : 'Engage'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
