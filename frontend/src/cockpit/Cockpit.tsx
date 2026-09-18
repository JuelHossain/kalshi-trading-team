/**
 * The app shell: icon rail, status bar, the Orbit and Config views, the
 * telemetry band and the floating inspector. Layout follows the design
 * handoff exactly; data comes from the engine through useEngineFeed.
 */
import { GitBranch, Settings2 } from 'lucide-react';
import type { CSSProperties } from 'react';
import { BeatBar } from './BeatBar';
import { Guardrails } from './Guardrails';
import { cardWidth, defaultCardX, InspectorCard } from './InspectorCard';
import { OrdersPanel } from './OrdersPanel';
import { OrreryPlate } from './OrreryPlate';
import { AC, ACI, ACS, E, G, glassStyle, mix, PALETTES, paletteVars, R, SG, T1, T3, T4 } from './palette';
import { useCockpit, type Mode } from './store';
import { STATIONS } from './stations';
import { Telemetry } from './Telemetry';
import { useViewport } from './useBoxSize';
import { useCockpitView } from './useCockpitView';
import { useEngineFeed } from './useEngineFeed';

const NAV = [
  { id: 'pipeline' as const, label: 'Orbit', icon: GitBranch },
  { id: 'config' as const, label: 'Config', icon: Settings2 },
];

const MODE_LABEL: Record<Mode, string> = {
  live: 'Engine live',
  idle: 'Standby',
  choke: 'Backpressure',
  fault: 'Fault',
  locked: 'Halted',
};

export function Cockpit({ isPaperTrading, onSignOut }: { isPaperTrading: boolean; onSignOut: () => void }) {
  const s = useCockpit();
  const v = useCockpitView();
  const vp = useViewport();
  const { runCycle, cancelCycle, setAutopilot, setKill } = useEngineFeed(true, isPaperTrading);
  const pal = PALETTES[s.palette];
  const W = vp.w;
  const H = vp.h;
  const narrow = W < 900;
  const wide = W >= 1320;
  const short = H < 720;
  const mode = v.mode;
  const glass = glassStyle(pal);

  const stateInk = mode === 'locked' || mode === 'fault' || mode === 'choke' ? AC : mode === 'live' ? SG : T3;
  const secs = Math.floor((s.now - s.t0) / 1000);
  const teleH = short ? 140 : 168;
  const cw = cardWidth(W);
  const cardX = s.cardX ?? defaultCardX(W);
  const docked = !!s.card && !narrow && !s.collapsed && cardX < 260;

  const segWrap: CSSProperties = { display: 'flex', gap: 2, padding: 3, borderRadius: 999, ...glass };
  const pill = (on: boolean, disabled = false): CSSProperties => ({
    border: 'none',
    background: on ? ACS : 'transparent',
    color: on ? ACI : T4,
    borderRadius: 999,
    padding: '5px 12px',
    fontSize: 11,
    fontWeight: 600,
    letterSpacing: '0.04em',
    cursor: disabled ? 'default' : 'pointer',
    transition: 'background 0.18s',
  });

  return (
    <div
      style={{
        ...paletteVars(pal),
        position: 'relative',
        height: '100vh',
        width: '100%',
        overflow: 'hidden',
        background: G,
        color: T1,
        fontFamily: 'var(--font-body)',
        ...(s.dragging ? { userSelect: 'none', cursor: 'grabbing' } : {}),
      }}
    >
      <Drift />

      <div
        style={{
          position: 'relative',
          zIndex: 1,
          height: '100%',
          display: 'grid',
          gap: 0,
          ...(narrow
            ? { gridTemplateColumns: 'minmax(0,1fr)', gridTemplateRows: 'minmax(0,1fr) 140px 60px', gridTemplateAreas: '"orbit" "tele" "nav"' }
            : { gridTemplateColumns: '72px minmax(0,1fr)', gridTemplateRows: `minmax(0,1fr) ${teleH}px`, gridTemplateAreas: '"rail orbit" "rail tele"' }),
        }}
      >
        {!narrow && (
          <aside
            style={{
              gridArea: 'rail',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              padding: '18px 10px 20px',
              ...glass,
              borderTop: 'none',
              borderBottom: 'none',
              borderLeft: 'none',
              borderRight: `1px solid ${mix(E, 70)}`,
            }}
          >
            <div style={{ width: 36, height: 36, borderRadius: 999, background: ACS, display: 'grid', placeItems: 'center', color: ACI, fontWeight: 600, fontSize: 17, flex: 'none' }}>S</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 26, width: '100%' }}>
              {NAV.map((n) => {
                const on = s.view === n.id;
                return (
                  <button
                    key={n.id}
                    onClick={() => s.setView(n.id)}
                    style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, width: '100%', padding: '9px 0', border: 'none', borderRadius: R, cursor: 'pointer', background: on ? mix(E, 80) : 'transparent', color: on ? T1 : T4 }}
                  >
                    <span style={{ display: 'block', color: on ? AC : T4 }}>
                      <n.icon size={17} strokeWidth={2.75} />
                    </span>
                    <span style={{ fontSize: 9, fontWeight: 600, letterSpacing: '0.05em' }}>{n.label}</span>
                  </button>
                );
              })}
            </div>
            <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, width: '100%' }}>
              <span style={{ width: 10, height: 10, borderRadius: 999, background: stateInk, animation: mode === 'live' ? 'saBreathe 1.8s ease-in-out infinite' : undefined }} />
              <button
                onClick={onSignOut}
                style={{ border: `1px solid ${E}`, background: 'transparent', color: T4, borderRadius: 999, padding: '6px 10px', fontSize: 10, fontWeight: 600, letterSpacing: '0.06em', cursor: 'pointer', width: '100%' }}
              >
                Exit
              </button>
            </div>
          </aside>
        )}

        <main style={{ gridArea: 'orbit', minWidth: 0, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div
            style={{
              flex: 'none',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 14,
              flexWrap: 'wrap',
              padding: narrow ? '12px 16px' : '12px 22px',
              borderBottom: `1px solid ${mix(E, 70)}`,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0, flexWrap: 'wrap' }}>
              <span style={{ width: 8, height: 8, borderRadius: 999, flex: 'none', background: stateInk, animation: mode === 'live' ? 'saBreathe 1.8s ease-in-out infinite' : undefined }} />
              <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: stateInk }}>
                {s.connected ? MODE_LABEL[mode] : 'Engine offline'}
              </span>
              <span style={{ width: 1, height: 12, background: E }} />
              <span className="num" style={{ fontSize: 12, color: T3 }}>
                Cycle {s.cycle}
              </span>
              <span style={{ width: 1, height: 12, background: E }} />
              <span className="num" style={{ fontSize: 12, color: T4 }}>
                {(v.working ? STATIONS[v.bi].name : 'Star') + ' · ' + (secs < 1 ? '0' : secs) + 's'}
              </span>
              <span style={{ width: 1, height: 12, background: E }} />
              <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: isPaperTrading ? SG : AC }}>
                {isPaperTrading ? 'Paper' : 'Live funds'}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              {!narrow && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 2, padding: 3, borderRadius: 999, ...glass }}>
                  {(['cream', 'night'] as const).map((k) => (
                    <button key={k} onClick={() => s.setPalette(k)} style={pill(k === s.palette)}>
                      {PALETTES[k].name}
                    </button>
                  ))}
                </div>
              )}
              <div style={segWrap} aria-label="engine state">
                {(
                  [
                    ['live', 'Live'],
                    ['idle', 'Idle'],
                    ['choke', 'Choke'],
                    ['fault', 'Fault'],
                    ['locked', 'Lock'],
                  ] as const
                ).map(([id, label]) => (
                  <span key={id} style={pill(mode === id, true)} aria-current={mode === id ? 'true' : undefined}>
                    {label}
                  </span>
                ))}
              </div>
              <div style={segWrap}>
                <button
                  onClick={() => (s.processing ? cancelCycle() : runCycle())}
                  disabled={s.kill || !s.connected}
                  style={{ ...pill(!s.processing), opacity: s.kill || !s.connected ? 0.5 : 1, cursor: s.kill || !s.connected ? 'not-allowed' : 'pointer' }}
                >
                  {s.processing ? 'Cancel' : 'Run cycle'}
                </button>
                <button
                  onClick={() => setAutopilot(!s.autopilot)}
                  disabled={s.kill || !s.connected}
                  style={{ ...pill(s.autopilot), opacity: s.kill || !s.connected ? 0.5 : 1, cursor: s.kill || !s.connected ? 'not-allowed' : 'pointer' }}
                >
                  Autopilot
                </button>
              </div>
            </div>
          </div>

          {s.view === 'pipeline' ? (
            <div
              className="sc"
              style={{
                flex: 1,
                minHeight: 0,
                display: 'flex',
                ...(narrow ? { flexDirection: 'column', overflowY: 'auto' } : { flexDirection: 'row', overflow: 'hidden' }),
                gap: narrow ? 12 : 16,
                padding: narrow ? '12px 14px' : short ? '12px 18px' : '16px 22px',
              }}
            >
              <div
                style={{
                  minWidth: 0,
                  ...(narrow ? { flex: 'none' } : { flex: '1 1 0', minHeight: 0 }),
                  display: 'flex',
                  flexDirection: 'column',
                  gap: short ? 10 : 13,
                  marginLeft: docked ? cw + 14 : 0,
                  transition: 'margin-left 0.28s cubic-bezier(0.2,0.8,0.2,1)',
                }}
              >
                <div style={{ position: 'relative', ...(narrow ? { flex: 'none', height: 320 } : { flex: '1 1 0', minHeight: 0 }) }}>
                  <OrreryPlate />
                </div>
                <BeatBar narrow={narrow} short={short} />
              </div>
              <OrdersPanel narrow={narrow} wide={wide} />
            </div>
          ) : (
            <Guardrails narrow={narrow} onAutopilot={setAutopilot} onKill={setKill} />
          )}
        </main>

        <Telemetry narrow={narrow} short={short} />

        {narrow && (
          <nav
            style={{
              gridArea: 'nav',
              display: 'flex',
              alignItems: 'stretch',
              ...glass,
              borderTop: `1px solid ${mix(E, 70)}`,
              borderLeft: 'none',
              borderRight: 'none',
              borderBottom: 'none',
            }}
          >
            {NAV.map((n) => {
              const on = s.view === n.id;
              return (
                <button
                  key={n.id}
                  onClick={() => s.setView(n.id)}
                  style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 4, minHeight: 44, border: 'none', background: 'transparent', cursor: 'pointer', color: on ? T1 : T4 }}
                >
                  <span style={{ display: 'block', color: on ? AC : T4 }}>
                    <n.icon size={17} strokeWidth={2.75} />
                  </span>
                  <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.04em' }}>{n.label}</span>
                </button>
              );
            })}
            <button
              onClick={onSignOut}
              style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 44, border: 'none', background: 'transparent', cursor: 'pointer', color: T4, fontSize: 10, fontWeight: 600, letterSpacing: '0.06em' }}
            >
              Exit
            </button>
          </nav>
        )}
      </div>

      <InspectorCard vw={W} vh={H} />
    </div>
  );
}

/** Two slow-drifting colour fields behind everything. */
export function Drift() {
  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none', zIndex: 0 }}>
      <div
        style={{
          position: 'absolute',
          left: '-16vw',
          top: '-24vh',
          width: '72vw',
          height: '72vw',
          borderRadius: 999,
          background: `radial-gradient(circle at 50% 50%, var(--acs) 0%, ${mix('var(--acs)', 50)} 30%, transparent 70%)`,
          opacity: 0.15,
          willChange: 'transform',
          animation: 'saDrift1 44s ease-in-out infinite alternate',
        }}
      />
      <div
        style={{
          position: 'absolute',
          right: '-20vw',
          bottom: '-30vh',
          width: '76vw',
          height: '76vw',
          borderRadius: 999,
          background: `radial-gradient(circle at 50% 50%, var(--sgs) 0%, ${mix('var(--sgs)', 50)} 30%, transparent 70%)`,
          opacity: 0.13,
          willChange: 'transform',
          animation: 'saDrift2 52s ease-in-out infinite alternate',
        }}
      />
    </div>
  );
}
