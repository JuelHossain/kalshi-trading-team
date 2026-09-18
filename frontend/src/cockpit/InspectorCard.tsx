/**
 * The draggable, dockable inspector: one agent or the Synapse, with what it
 * is working on now and its run history. Never covers the orbit: when it
 * sits docked at the left, the stage column shifts over (see Cockpit).
 */
import { Sparkles } from 'lucide-react';
import { useCallback, useEffect, useRef, type CSSProperties } from 'react';
import { AC, ACI, ACS, E, F, G, mix, R, RL, SG, SGS, T1, T2, T3, T4 } from './palette';
import { PALETTES } from './palette';
import { useCockpit, type Run } from './store';
import { N, STATIONS } from './stations';
import { useCockpitView } from './useCockpitView';

export const cardWidth = (vw: number) => (vw < 620 ? Math.max(240, vw - 24) : 344);
export const cardHeight = (vh: number) => Math.min(Math.max(320, vh - 150), 620);
export const defaultCardX = (vw: number) => (vw < 620 ? 12 : 80);
export const DEFAULT_CARD_Y = 86;

export function InspectorCard({ vw, vh }: { vw: number; vh: number }) {
  const s = useCockpit();
  const v = useCockpitView();
  const pal = PALETTES[s.palette];
  const drag = useRef<{ dx: number; dy: number } | null>(null);
  const C = s.card;

  const cw = cardWidth(vw);
  const ch = cardHeight(vh);
  const cardX = s.cardX ?? defaultCardX(vw);
  const cardY = s.cardY ?? DEFAULT_CARD_Y;

  const onMove = useCallback(
    (e: PointerEvent) => {
      if (!drag.current) return;
      const x = Math.max(8, Math.min(vw - cw - 8, e.clientX - drag.current.dx));
      const y = Math.max(8, Math.min(vh - 54, e.clientY - drag.current.dy));
      useCockpit.getState().setCardPos(x, y);
    },
    [vw, vh, cw]
  );
  const onUp = useCallback(() => {
    drag.current = null;
    useCockpit.getState().setDragging(false);
    window.removeEventListener('pointermove', onMove);
    window.removeEventListener('pointerup', onUp);
  }, [onMove]);
  const startDrag = (e: React.PointerEvent) => {
    if ((e.target as HTMLElement).tagName === 'BUTTON') return;
    drag.current = { dx: e.clientX - cardX, dy: e.clientY - cardY };
    useCockpit.getState().setDragging(true);
    useCockpit.getState().setCardPos(cardX, cardY);
    e.preventDefault();
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  };
  useEffect(() => () => onUp(), [onUp]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && useCockpit.getState().card) useCockpit.getState().closeCard();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  if (!C) return null;

  const cCore = C.kind === 'core';
  const cAgent = C.kind === 'agent' ? (C.i ?? 0) : -1;
  const station = cAgent >= 0 ? STATIONS[cAgent] : null;
  const Icon = station ? station.icon : Sparkles;
  const starC = v.coreAlarm ? ACS : SGS;

  const runsFor = s.runs.filter((r) => (cCore ? r.kind === 'core' : r.kind === 'agent' && r.agent === cAgent)).slice().reverse();
  const msList = runsFor.map((r) => r.ms).sort((a, b) => a - b);
  const median = msList.length ? msList[Math.floor(msList.length / 2)] : 0;
  const okN = runsFor.filter((r) => r.ok).length;
  const slow = runsFor.reduce<Run | null>((a, b) => (!a || b.ms > a.ms ? b : a), null);

  const tabBtn = (on: boolean): CSSProperties => ({
    flex: 1,
    border: 'none',
    borderRadius: 999,
    padding: '6px 12px',
    fontSize: 11,
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'background 0.18s, color 0.18s',
    background: on ? mix(ACS, 20) : 'transparent',
    color: on ? AC : T4,
  });
  const iconBtn: CSSProperties = {
    flex: 'none',
    width: 28,
    height: 28,
    borderRadius: 999,
    border: `1px solid ${mix(E, 75)}`,
    background: 'transparent',
    color: T3,
    fontSize: 11,
    lineHeight: 1,
    cursor: 'pointer',
  };

  return (
    <div
      role="dialog"
      aria-label={cCore ? 'Synapse inspector' : `${station?.name} inspector`}
      style={{
        position: 'fixed',
        left: cardX,
        top: cardY,
        width: cw,
        height: s.collapsed ? undefined : ch,
        zIndex: 30,
        display: 'flex',
        flexDirection: 'column',
        borderRadius: RL,
        overflow: 'hidden',
        background: mix(pal.p, 94, G),
        border: `1px solid ${mix(T1, pal.dark ? 18 : 0, E)}`,
        boxShadow: `0 24px 60px ${mix('#000000', pal.dark ? 52 : 20)}`,
        animation: 'saSlideIn 0.24s cubic-bezier(0.2,0.8,0.2,1)',
      }}
    >
      <div
        onPointerDown={startDrag}
        style={{
          flex: 'none',
          display: 'flex',
          alignItems: 'center',
          gap: 11,
          padding: '12px 12px 12px 14px',
          borderBottom: `1px solid ${mix(E, 55)}`,
          cursor: s.dragging ? 'grabbing' : 'grab',
          background: mix(G, 26),
          userSelect: 'none',
          touchAction: 'none',
        }}
      >
        <span
          style={{
            flex: 'none',
            width: 36,
            height: 36,
            borderRadius: 999,
            display: 'grid',
            placeItems: 'center',
            background: cCore ? `radial-gradient(circle at 40% 34%, ${mix(T1, 70, starC)}, ${starC} 70%)` : mix(SGS, 18),
            color: cCore ? ACI : SG,
          }}
        >
          <Icon size={18} strokeWidth={2.75} />
        </span>
        <span style={{ flex: 1, minWidth: 0 }}>
          <span style={{ display: 'block', fontFamily: 'var(--font-heading)', fontSize: 17, lineHeight: 1.1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: T1 }}>
            {cCore ? 'Synapse' : station?.name}
          </span>
          <span style={{ display: 'block', fontSize: 10, color: T4, marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {cCore ? 'The star · catches every throw' : `${station?.role} · ${station?.model}`}
          </span>
        </span>
        <button onClick={s.toggleCollapse} title="collapse" style={iconBtn}>
          {s.collapsed ? '▢' : '—'}
        </button>
        <button onClick={s.closeCard} title="close" aria-label="close" style={iconBtn}>
          ✕
        </button>
      </div>

      {!s.collapsed && (
        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <div style={{ flex: 'none', display: 'flex', gap: 3, padding: '9px 12px', borderBottom: `1px solid ${mix(E, 40)}` }}>
            <button onClick={() => s.setCardTab('now')} style={tabBtn(s.cardTab === 'now')}>
              {cCore ? 'Holding' : 'Working now'}
            </button>
            <button onClick={() => s.setCardTab('history')} style={tabBtn(s.cardTab === 'history')}>
              History
            </button>
          </div>
          <div className="sc" style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '13px 14px 16px' }}>
            {s.cardTab === 'now' ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {cCore && <CoreNow />}
                {cAgent === 0 && <SoulNow />}
                {cAgent === 1 && <SensesNow />}
                {cAgent === 2 && <BrainNow />}
                {cAgent === 3 && <HandNow />}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
                <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(2,minmax(0,1fr))', padding: '0 2px 12px', borderBottom: `1px solid ${mix(E, 50)}` }}>
                  {[
                    { label: 'Runs', value: String(runsFor.length) },
                    { label: 'Median', value: median ? `${(median / 1000).toFixed(2)}s` : '—' },
                    { label: 'Clean', value: runsFor.length ? `${Math.round((okN / runsFor.length) * 100)}%` : '—' },
                    { label: 'Slowest', value: slow ? `${(slow.ms / 1000).toFixed(2)}s · #${slow.cycle}` : '—' },
                  ].map((h) => (
                    <div key={h.label} style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 9, fontWeight: 600, letterSpacing: '0.09em', textTransform: 'uppercase', color: F }}>{h.label}</div>
                      <div className="num" style={{ fontFamily: 'var(--font-heading)', fontSize: 16, marginTop: 2, color: T1 }}>
                        {h.value}
                      </div>
                    </div>
                  ))}
                </div>
                {runsFor.map((r) => {
                  const open = s.openRun === r.id;
                  return (
                    <div
                      key={r.id}
                      style={{
                        borderRadius: R,
                        overflow: 'hidden',
                        border: `1px solid ${open ? mix(SGS, 40, E) : mix(E, 50)}`,
                        background: open ? mix(SGS, 5, G) : 'transparent',
                      }}
                    >
                      <button
                        onClick={() => s.toggleRun(r.id)}
                        style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 9, padding: '10px 11px', border: 'none', background: 'transparent', cursor: 'pointer', textAlign: 'left', color: 'inherit' }}
                      >
                        <span className="num" style={{ flex: 'none', width: 30, fontSize: 11, fontWeight: 600, color: T4 }}>
                          #{r.cycle}
                        </span>
                        <span style={{ flex: 1, minWidth: 0 }}>
                          <span style={{ display: 'block', fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: T1 }}>{r.summary}</span>
                          <span style={{ display: 'block', fontSize: 10, color: F, marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {new Date(r.ts).toLocaleTimeString('en-US', { hour12: false })}
                            {r.kind === 'core' && r.hop !== undefined ? ` · ${STATIONS[r.hop].name} → ${STATIONS[(r.hop + 1) % N].name}` : ''}
                          </span>
                        </span>
                        <span className="num" style={{ flex: 'none', fontSize: 11, fontWeight: 600, color: T3 }}>
                          {(r.ms / 1000).toFixed(2)}s
                        </span>
                        <span
                          style={{
                            flex: 'none',
                            fontSize: 8,
                            fontWeight: 600,
                            letterSpacing: '0.08em',
                            textTransform: 'uppercase',
                            padding: '3px 7px',
                            borderRadius: 999,
                            background: r.ok ? mix(SGS, 16) : mix(ACS, 18),
                            color: r.ok ? SG : AC,
                          }}
                        >
                          {r.ok ? 'clean' : 'flagged'}
                        </span>
                      </button>
                      {open && (
                        <div style={{ display: 'flex', flexDirection: 'column', padding: '0 11px 10px', animation: 'saFade 0.25s ease-out' }}>
                          {r.detail.map(([label, value]) => (
                            <div key={label} style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12, padding: '7px 0', borderTop: `1px solid ${mix(E, 45)}` }}>
                              <span style={{ flex: 'none', fontSize: 10, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: F }}>{label}</span>
                              <span className="num" style={{ minWidth: 0, textAlign: 'right', fontSize: 11, fontWeight: 600, color: T2 }}>
                                {value}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
                {runsFor.length === 0 && <div style={{ fontSize: 12, color: T4, padding: '10px 2px' }}>No runs yet this session.</div>}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Label({ children, ink = T4 }: { children: React.ReactNode; ink?: string }) {
  return <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: ink }}>{children}</div>;
}

function CoreNow() {
  const s = useCockpit();
  const v = useCockpitView();
  const alarm = v.coreAlarm;
  const holds = v.mode === 'choke' ? `${s.storeDepth} verdicts` : s.storeDepth && s.storeKind >= 0 ? STATIONS[s.storeKind].payload : s.storeDepth ? 'queued work' : 'nothing';
  const note =
    v.mode === 'choke'
      ? 'The Hand fills slower than the Brain decides, so the store hit its cap and the star stopped throwing back.'
      : v.mode === 'fault'
        ? 'The verdict is still here because the Hand never caught it.'
        : v.beat === 'flare'
          ? `Caught — the ${STATIONS[v.bi].payload} just landed and is now the store's contents.`
          : s.storeDepth
            ? 'Everything an agent throws lands here before the next agent is woken. These rows are the live Synapse queues.'
            : 'The store is empty between cycles; the star only glows when it holds something.';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ borderRadius: R, padding: 13, border: `1px solid ${alarm ? mix(ACS, 45, E) : mix(SGS, 35, E)}`, background: alarm ? mix(ACS, 7, G) : mix(SGS, 5, G) }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <div style={{ minWidth: 0 }}>
            <Label>Holding</Label>
            <div style={{ fontFamily: 'var(--font-heading)', fontSize: 20, lineHeight: 1.15, marginTop: 3, color: T1 }}>{holds}</div>
          </div>
          <div className="num" style={{ fontFamily: 'var(--font-heading)', fontSize: 24, lineHeight: 1, color: alarm ? AC : SG }}>
            {s.storeDepth}/10
          </div>
        </div>
        <div style={{ fontSize: 12, lineHeight: 1.55, color: T3, marginTop: 9, textWrap: 'pretty' }}>{note}</div>
      </div>
      {s.storeItems.map((q, i) => {
        const bad = q.state === 'blocked' || q.state === 'waiting';
        return (
          <div key={q.ticker + i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 10px', borderRadius: R, background: mix(G, 55), border: `1px solid ${bad ? mix(ACS, 30, E) : mix(E, 55)}` }}>
            <span style={{ flex: 'none', width: 8, height: 8, borderRadius: 999, background: bad ? ACS : SGS }} />
            <span style={{ flex: 1, minWidth: 0 }}>
              <span className="num" style={{ display: 'block', fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: T1 }}>
                {q.ticker}
              </span>
              <span style={{ display: 'block', fontSize: 11, color: T4, marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{q.title}</span>
            </span>
            <span style={{ flex: 'none', fontSize: 8, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', padding: '3px 8px', borderRadius: 999, background: bad ? mix(ACS, 20) : mix(SGS, 16), color: bad ? AC : SG }}>
              {q.state}
            </span>
          </div>
        );
      })}
      {s.storeItems.length === 0 && (
        <div style={{ padding: 16, textAlign: 'center', fontSize: 12, color: T4, border: `1px dashed ${E}`, borderRadius: R }}>
          {v.mode === 'locked' ? 'Halted — the store is sealed.' : 'Nothing stored right now.'}
        </div>
      )}
    </div>
  );
}

function SoulNow() {
  const s = useCockpit();
  const sealed = s.soul.sealed;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
      {s.soul.checks.map((c) => (
        <div
          key={c.label}
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, borderRadius: 999, padding: '6px 13px 6px 6px', border: `1px solid ${c.ok ? mix(SGS, 40, E) : mix(E, 70)}`, background: c.ok ? mix(SGS, 8, G) : mix(G, 40) }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 9, minWidth: 0 }}>
            <span style={{ flex: 'none', width: 19, height: 19, borderRadius: 999, display: 'grid', placeItems: 'center', fontSize: 11, fontWeight: 600, background: c.ok ? mix(SGS, 24) : E, color: c.ok ? SG : F }}>
              {c.ok ? '✓' : '·'}
            </span>
            <span style={{ fontSize: 11, fontWeight: 600, whiteSpace: 'nowrap', color: T3 }}>{c.label}</span>
          </div>
          <div className="num" style={{ fontSize: 11, fontWeight: 600, textAlign: 'right', color: c.ok ? T1 : T4 }}>
            {c.value}
          </div>
        </div>
      ))}
      <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.07em', textTransform: 'uppercase', padding: '10px 13px', borderRadius: R, background: sealed ? mix(SGS, 16) : mix(G, 60), color: sealed ? SG : T4 }}>
        {sealed ? `Authorization sealed · cycle ${s.cycle} may proceed` : 'Awaiting pre-flight'}
      </div>
      <div style={{ fontSize: 11, color: T4, lineHeight: 1.5 }}>
        Balance ${s.balance.toFixed(2)} · headroom above the $255 floor {s.balance ? `$${Math.max(0, s.balance - 255).toFixed(2)}` : '—'}
      </div>
    </div>
  );
}

function SensesNow() {
  const s = useCockpit();
  const rows = s.senses.markets.slice(-5).reverse();
  const maxVol = Math.max(1, ...rows.map((m) => m.volume));
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0 2px 8px', borderBottom: `1px solid ${E}`, fontSize: 9, fontWeight: 600, letterSpacing: '0.09em', textTransform: 'uppercase', color: F }}>
        <span style={{ width: 18, flex: 'none' }}>#</span>
        <span style={{ flex: 1, minWidth: 0 }}>Market</span>
        <span style={{ flex: 'none', width: 40, textAlign: 'right' }}>Yes</span>
      </div>
      {rows.map((m, i) => {
        const lead = i === 0;
        return (
          <div key={m.ticker} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 2px', borderBottom: `1px solid ${mix(E, 50)}` }}>
            <span className="num" style={{ flex: 'none', width: 18, fontWeight: 600, fontSize: 11, color: lead ? SG : F }}>
              {i + 1}
            </span>
            <span style={{ flex: 1, minWidth: 0 }}>
              <span className="num" style={{ display: 'block', fontSize: 11, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: lead ? T1 : T2 }}>
                {m.ticker}
              </span>
              <span style={{ display: 'block', height: 3, borderRadius: 999, background: G, marginTop: 5, overflow: 'hidden' }}>
                <span style={{ display: 'block', height: '100%', width: `${Math.round((m.volume / maxVol) * 100)}%`, borderRadius: 999, background: lead ? SGS : E, transition: 'width 0.5s ease' }} />
              </span>
            </span>
            <span className="num" style={{ flex: 'none', width: 40, textAlign: 'right', fontSize: 12, fontWeight: 600, color: lead ? SG : T2 }}>
              {m.yes}
            </span>
          </div>
        );
      })}
      {rows.length === 0 && <div style={{ fontSize: 12, color: T4, padding: '12px 2px' }}>No shortlist yet this cycle.</div>}
      <div style={{ fontSize: 11, color: T4, marginTop: 10, lineHeight: 1.5 }}>
        {s.senses.swept ? `Swept ${s.senses.swept.toLocaleString()} markets · ${s.senses.selected} cleared the filters (volume ≥ 200, spread ≤ 8¢, closing within 10 days).` : 'Volume bars scale to the best market in the list.'}
      </div>
    </div>
  );
}

function BrainNow() {
  const s = useCockpit();
  const b = s.brain;
  const conf = b.conf ?? 0;
  const decided = b.verdict !== null;
  const briefBox = (on: boolean, c: string): CSSProperties => ({ borderRadius: R, padding: '11px 13px', border: `1px solid ${on ? mix(c, 40, E) : E}`, background: on ? mix(c, 8, G) : mix(G, 60), transition: 'border-color 0.4s, background 0.4s' });
  const verdictLabel =
    b.verdict === 'approved'
      ? `Buy ${b.side} @ ${b.price}¢`
      : b.verdict === 'vetoed'
        ? `Vetoed · ${b.reason}`
        : b.verdict === 'skipped'
          ? `Skipped · ${b.reason}`
          : b.prob !== null
            ? 'Weighing the estimate against the price'
            : b.ticker
              ? 'Researching with Google Search grounding'
              : 'No verdict yet';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
      <div className="num" style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.04em', color: T3 }}>
        {b.ticker || 'No market under deliberation'}
      </div>
      <div style={briefBox(b.prob !== null, SGS)}>
        <Label ink={SG}>Estimate</Label>
        <div style={{ fontSize: 12, lineHeight: 1.5, marginTop: 4, color: T2, textWrap: 'pretty' }}>
          {b.prob !== null ? `Three grounded samples, median probability ${(b.prob * 100).toFixed(0)}% that the event happens.` : 'Awaiting the grounded estimate.'}
        </div>
      </div>
      <div style={briefBox(b.ev !== null, ACS)}>
        <Label ink={AC}>Against the price</Label>
        <div style={{ fontSize: 12, lineHeight: 1.5, marginTop: 4, color: T2, textWrap: 'pretty' }}>
          {b.ev !== null ? `Best side pays an expected ${b.ev >= 0 ? '+' : ''}${b.ev.toFixed(3)} per $1 contract before fees. The floor is +0.050.` : 'Awaiting the price comparison.'}
        </div>
      </div>
      <div style={{ borderRadius: R, padding: '12px 13px', background: mix(G, 60) }}>
        <Label>Judge</Label>
        <div style={{ fontWeight: 600, fontSize: 14, marginTop: 4, color: decided ? T1 : T3 }}>{verdictLabel}</div>
        <div style={{ height: 3, borderRadius: 999, background: E, overflow: 'hidden', marginTop: 8 }}>
          <div style={{ height: '100%', width: `${Math.min(100, conf)}%`, borderRadius: 999, background: ACS, transition: 'width 0.4s linear' }} />
        </div>
        <div style={{ display: 'flex', gap: 18, marginTop: 12 }}>
          <div>
            <div className="num" style={{ fontFamily: 'var(--font-heading)', fontSize: 21, lineHeight: 1, color: conf > 0 ? AC : F }}>
              {conf ? Math.round(conf) : '—'}
              {conf ? <span style={{ fontSize: '0.5em' }}>%</span> : null}
            </div>
            <div style={{ fontSize: 9, fontWeight: 600, letterSpacing: '0.09em', textTransform: 'uppercase', color: F }}>confidence</div>
          </div>
          <div>
            <div className="num" style={{ fontFamily: 'var(--font-heading)', fontSize: 21, lineHeight: 1, color: b.ev !== null && b.ev >= 0.05 ? SG : b.ev !== null ? AC : F }}>
              {b.ev !== null ? `${b.ev >= 0 ? '+' : ''}${b.ev.toFixed(3)}` : '—'}
            </div>
            <div style={{ fontSize: 9, fontWeight: 600, letterSpacing: '0.09em', textTransform: 'uppercase', color: F }}>exp. value</div>
          </div>
          <div>
            <div className="num" style={{ fontFamily: 'var(--font-heading)', fontSize: 21, lineHeight: 1, color: T1 }}>
              {b.approved}/{b.analysed}
            </div>
            <div style={{ fontSize: 9, fontWeight: 600, letterSpacing: '0.09em', textTransform: 'uppercase', color: F }}>approved</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function HandNow() {
  const s = useCockpit();
  const h = s.hand;
  const armed = !!h.ticker;
  const bad = !!h.fault;
  const cost = h.stake !== null ? `$${h.stake.toFixed(2)}` : '$0.00';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
      <div style={{ borderRadius: R, padding: 13, border: `1px ${armed ? 'solid' : 'dashed'} ${armed ? mix(bad ? ACS : SGS, 40, E) : E}`, background: mix(G, 60) }}>
        <div className="num" style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.04em', color: T3 }}>
          {armed ? h.ticker : 'NO TICKET ISSUED'}
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 9, marginTop: 7, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 9, fontWeight: 600, letterSpacing: '0.1em', padding: '3px 9px', borderRadius: 999, background: h.side === 'NO' ? mix(ACS, 18) : mix(SGS, 18), color: h.side === 'NO' ? AC : SG }}>
            {h.side || '—'}
          </span>
          <span className="num" style={{ fontFamily: 'var(--font-heading)', fontSize: 19, color: T1 }}>
            {h.count ?? 0} @ {h.price ?? 0}¢
          </span>
          <span className="num" style={{ marginLeft: 'auto', fontSize: 12, fontWeight: 600, color: armed ? T3 : F }}>
            {cost}
          </span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 7, marginTop: 13 }}>
          {h.steps.map((st) => (
            <div key={st.label} style={{ display: 'flex', alignItems: 'center', gap: 9, color: st.ok || st.bad ? T1 : T4 }}>
              <span style={{ flex: 'none', width: 18, height: 18, borderRadius: 999, display: 'grid', placeItems: 'center', fontSize: 10, fontWeight: 600, background: st.bad ? mix(ACS, 24) : st.ok ? mix(SGS, 22) : E, color: st.bad ? AC : st.ok ? SG : F }}>
                {st.bad ? '!' : st.ok ? '✓' : '·'}
              </span>
              <span style={{ flex: 1, minWidth: 0, fontSize: 12 }}>{st.label}</span>
              <span className="num" style={{ flex: 'none', fontSize: 11, color: st.bad ? AC : T4 }}>
                {st.meta}
              </span>
            </div>
          ))}
        </div>
      </div>
      {bad && (
        <div style={{ borderRadius: R, padding: 13, border: `1px solid ${mix(ACS, 50, E)}`, background: mix(ACS, 7, G), backgroundImage: `repeating-linear-gradient(135deg, transparent 0 7px, ${mix(AC, 12)} 7px 14px)` }}>
          <Label ink={AC}>Refused</Label>
          <div style={{ fontSize: 12, lineHeight: 1.5, marginTop: 5, color: T2, textWrap: 'pretty' }}>{h.fault}</div>
        </div>
      )}
    </div>
  );
}
