/**
 * The Config view: the limits the Soul enforces, the autopilot switch and
 * the kill switch. Every number comes from GET /config, so the page shows
 * what the engine is running with, environment overrides included. Each
 * bar is a real ratio: how close the current state sits to that limit.
 */
import type { CSSProperties } from 'react';
import { AC, ACI, ACS, E, G, glassStyle, mix, RL, SG, T1, T3, T4 } from './palette';
import { PALETTES } from './palette';
import { SettingsEditor } from './SettingsEditor';
import { useCockpit, type UpdateReport } from './store';

const clamp = (x: number) => Math.max(0, Math.min(100, Math.round(x)));

export function Guardrails({
  narrow,
  onAutopilot,
  onKill,
  onSave,
  onRestart,
}: {
  narrow: boolean;
  onAutopilot: (enabled: boolean) => void;
  onKill: (engaged: boolean) => void;
  onSave: (changes: Record<string, unknown>) => Promise<UpdateReport>;
  onRestart: () => Promise<void>;
}) {
  const s = useCockpit();
  const pal = PALETTES[s.palette];
  const glassCard: CSSProperties = { borderRadius: RL, padding: 20, ...glassStyle(pal) };
  const c = s.config;

  const lastOrder = s.orders.length ? s.orders[s.orders.length - 1] : null;
  const lastStake = lastOrder ? (lastOrder.px * lastOrder.qty) / 100 : null;
  const latestEv = s.brain.ev;

  const limits = c
    ? [
        {
          label: 'Max stake / trade',
          value: `$${(c.hand.max_stake_cents / 100).toFixed(0)}`,
          pct: lastStake !== null ? clamp((lastStake / (c.hand.max_stake_cents / 100)) * 100) : 0,
          c: AC,
          note:
            lastStake !== null
              ? `Last fill staked $${lastStake.toFixed(2)}. Kelly sizing at ${c.hand.kelly_fraction} of full Kelly, capped here.`
              : `No fill yet this session. Kelly sizing at ${c.hand.kelly_fraction} of full Kelly, capped here.`,
        },
        {
          label: 'Minimum edge to trade',
          value: `${c.brain.min_edge >= 0 ? '+' : ''}${c.brain.min_edge.toFixed(3)}`,
          pct: latestEv !== null ? clamp((latestEv / c.brain.min_edge) * 100) : 0,
          c: SG,
          note:
            latestEv !== null
              ? `Latest verdict found ${latestEv >= 0 ? '+' : ''}${latestEv.toFixed(3)} per $1 contract. Confidence floor ${Math.round(c.brain.confidence_threshold * 100)}%.`
              : `Thinner than this is logged as a veto. Confidence floor ${Math.round(c.brain.confidence_threshold * 100)}%.`,
        },
        {
          label: 'Execution queue cap',
          value: String(c.queues.max_execution),
          pct: clamp((s.execDepth / c.queues.max_execution) * 100),
          c: AC,
          note: `${s.execDepth} verdict${s.execDepth === 1 ? '' : 's'} waiting for the Hand now. The star stops emitting when this is full.`,
        },
        {
          label: 'Hard floor',
          value: `$${(c.vault.hard_floor_cents / 100).toFixed(0)}`,
          pct: s.balance ? clamp((c.vault.hard_floor_cents / 100 / s.balance) * 100) : 0,
          c: SG,
          note: s.balance
            ? `Balance $${s.balance.toFixed(2)}; headroom $${Math.max(0, s.balance - c.vault.hard_floor_cents / 100).toFixed(2)}. Kill switch at ${Math.round(c.vault.kill_switch_pct * 100)}% of the $${(c.vault.principal_cents / 100).toFixed(0)} principal.`
            : `No cycle is authorised below it. Kill switch at ${Math.round(c.vault.kill_switch_pct * 100)}% of principal.`,
        },
      ]
    : [];

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
          The constitution the Soul enforces. Every line here is a hard limit, not a preference, and every value below is what the engine is running with right now.
          {c ? ` Kalshi ${c.kalshi_env}${c.paper_pinned ? ' · paper pinned on the server' : ''}.` : ''}
        </div>
      </div>
      <div className="sc" style={{ flex: 1, minHeight: 200, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 14, margin: '0 -4px', padding: '0 4px 4px' }}>
        {!c && (
          <div style={{ ...glassCard, fontSize: 12, color: T4 }}>
            {s.connected ? 'Reading the engine configuration…' : 'Engine unreachable; limits unknown until it answers.'}
          </div>
        )}
        <div style={{ display: 'grid', gap: 14, gridTemplateColumns: `repeat(auto-fit,minmax(${narrow ? 220 : 250}px,1fr))` }}>
          {limits.map((l) => (
            <div key={l.label} style={glassCard}>
              <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.09em', textTransform: 'uppercase', color: T4 }}>{l.label}</div>
              <div className="num" style={{ fontFamily: 'var(--font-heading)', fontSize: 28, color: T1, marginTop: 6 }}>
                {l.value}
              </div>
              <div style={{ height: 4, borderRadius: 999, background: E, marginTop: 12, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${l.pct}%`, borderRadius: 999, background: l.c, transition: 'width 0.4s' }} />
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
        <div style={{ flex: 'none' }}>
          <h2 style={{ fontFamily: 'var(--font-heading)', fontWeight: 400, fontSize: 22, margin: '10px 0 0', color: T1 }}>Settings</h2>
          <div style={{ fontSize: 13, color: T3, marginTop: 6, maxWidth: '62ch', textWrap: 'pretty' }}>
            Everything the engine can be told, grouped as it uses it. Live settings apply to the next market, order or cycle; the rest apply after a restart.
          </div>
        </div>
        <SettingsEditor onSave={onSave} onRestart={onRestart} />
      </div>
    </div>
  );
}
