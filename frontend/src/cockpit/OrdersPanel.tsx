/**
 * Executed orders with range and outcome filters. Rows come from the
 * engine's ledger (GET /orders) plus fills seen live this session.
 */
import { Filter } from 'lucide-react';
import type { CSSProperties } from 'react';
import { AC, ACS, E, F, G, glassStyle, mix, RL, SG, SGS, T1, T3, T4 } from './palette';
import { PALETTES } from './palette';
import { useCockpit, type Order } from './store';

export interface OrderFilters {
  range: 'all' | 'today' | 'week' | 'month';
  outcome: 'all' | 'won' | 'lost';
}

export function filterOrders(orders: Order[], f: OrderFilters, now = new Date()): Order[] {
  const today0 = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const week0 = today0 - ((now.getDay() + 6) % 7) * 86400000;
  const month0 = new Date(now.getFullYear(), now.getMonth(), 1).getTime();
  const inRange = (ts: number) =>
    f.range === 'all' ? true : f.range === 'today' ? ts >= today0 : f.range === 'week' ? ts >= week0 : ts >= month0;
  const inOutcome = (o: Order) =>
    f.outcome === 'all'
      ? true
      : f.outcome === 'won'
        ? o.status === 'filled' && (o.pnl ?? 0) > 0
        : o.status === 'rejected' || (o.status === 'filled' && (o.pnl ?? 0) <= 0);
  return orders.filter((o) => inRange(o.ts) && inOutcome(o));
}

export function orderStats(visible: Order[]) {
  const settled = visible.filter((o) => o.status === 'filled');
  const wins = settled.filter((o) => (o.pnl ?? 0) > 0).length;
  const realized = settled.reduce((a, o) => a + (o.pnl ?? 0), 0);
  const open = visible.filter((o) => o.status === 'open').length;
  return { settled: settled.length, wins, realized, open };
}

export function OrdersPanel({ narrow, wide, style }: { narrow: boolean; wide: boolean; style?: CSSProperties }) {
  const s = useCockpit();
  const pal = PALETTES[s.palette];
  const now = new Date();
  const today0 = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const visible = filterOrders(s.orders, { range: s.range, outcome: s.outcome }, now);
  const stats = orderStats(visible);
  const unfiltered = s.range === 'all' && s.outcome === 'all';

  const chip = (on: boolean): CSSProperties => ({
    border: 'none',
    borderRadius: 999,
    padding: '4px 11px',
    fontSize: 11,
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'background 0.18s',
    background: on ? mix(ACS, 20) : mix(G, 45),
    color: on ? AC : T4,
  });

  const rows = visible.slice().reverse();
  const summaryLabel =
    (s.range === 'all' ? 'All time' : s.range === 'today' ? 'Today' : s.range === 'week' ? 'This week' : 'This month') +
    (s.outcome === 'all' ? '' : ` · ${s.outcome === 'won' ? 'Won' : 'Lost'}`);

  return (
    <div
      style={{
        minWidth: 0,
        ...(narrow ? { flex: 'none', minHeight: 340 } : { flex: `0 0 ${wide ? 350 : 300}px`, minHeight: 0 }),
        display: 'flex',
        flexDirection: 'column',
        borderRadius: RL,
        overflow: 'hidden',
        ...glassStyle(pal),
        ...style,
      }}
    >
      <div style={{ flex: 'none', padding: '14px 16px 12px', borderBottom: `1px solid ${mix(E, 50)}` }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontFamily: 'var(--font-heading)', fontSize: 19, lineHeight: 1.1, color: T1 }}>Orders</div>
            <div style={{ fontSize: 11, color: T4, marginTop: 3 }}>
              {stats.settled} settled · {stats.open} open · {visible.length - stats.settled - stats.open} rejected
            </div>
          </div>
          <button
            onClick={s.toggleFilters}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              border: `1px solid ${unfiltered ? E : ACS}`,
              background: s.filtersOpen ? mix(ACS, 18) : 'transparent',
              color: unfiltered && !s.filtersOpen ? T3 : AC,
              borderRadius: 999,
              padding: '4px 10px',
              fontSize: 10,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <Filter size={12} strokeWidth={2.75} />
            <span style={{ whiteSpace: 'nowrap' }}>{summaryLabel}</span>
          </button>
        </div>
        <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(3,minmax(0,1fr))', marginTop: 12 }}>
          {[
            { label: 'Tickets', value: String(visible.length), ink: T1 },
            { label: 'Win rate', value: stats.settled ? `${Math.round((stats.wins / stats.settled) * 100)}%` : '—', ink: T1 },
            {
              label: 'Realized',
              value: `${stats.realized >= 0 ? '+$' : '−$'}${Math.abs(stats.realized).toFixed(2)}`,
              ink: stats.realized >= 0 ? SG : AC,
            },
          ].map((x) => (
            <div key={x.label} style={{ minWidth: 0 }}>
              <div style={{ fontSize: 9, fontWeight: 600, letterSpacing: '0.09em', textTransform: 'uppercase', color: F }}>{x.label}</div>
              <div className="num" style={{ fontFamily: 'var(--font-heading)', fontSize: 18, marginTop: 3, color: x.ink }}>
                {x.value}
              </div>
            </div>
          ))}
        </div>
      </div>

      {s.filtersOpen && (
        <div style={{ flex: 'none', padding: '11px 16px 12px', borderBottom: `1px solid ${mix(E, 50)}`, background: mix(G, 28) }}>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {(
              [
                ['all', 'All time'],
                ['today', 'Today'],
                ['week', 'This week'],
                ['month', 'This month'],
              ] as const
            ).map(([k, label]) => (
              <button key={k} onClick={() => s.setRange(k)} style={chip(s.range === k)}>
                {label}
              </button>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 7 }}>
            {(
              [
                ['all', 'All'],
                ['won', 'Won'],
                ['lost', 'Lost / rejected'],
              ] as const
            ).map(([k, label]) => (
              <button key={k} onClick={() => s.setOutcome(k)} style={chip(s.outcome === k)}>
                {label}
              </button>
            ))}
          </div>
        </div>
      )}

      <div
        style={{
          flex: 'none',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '9px 16px 7px',
          fontSize: 9,
          fontWeight: 600,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          color: F,
          borderBottom: `1px solid ${mix(E, 50)}`,
        }}
      >
        <span style={{ flex: 1, minWidth: 0 }}>Ticket</span>
        <span style={{ flex: 'none' }}>P&amp;L</span>
      </div>
      <div className="sc" style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '0 16px 12px' }}>
        {rows.map((o, i) => {
          const yes = o.side === 'YES';
          const pnlText = o.status === 'rejected' ? 'rej' : o.pnl === null ? 'open' : `${o.pnl >= 0 ? '+$' : '−$'}${Math.abs(o.pnl).toFixed(2)}`;
          const pnlInk = o.status === 'rejected' || o.pnl === null ? F : o.pnl >= 0 ? SG : AC;
          return (
            <div
              key={o.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '9px 0',
                borderBottom: `1px solid ${mix(E, 50)}`,
                animation: i === 0 ? 'saSlideIn 0.4s ease-out' : undefined,
              }}
            >
              <span
                style={{
                  flex: 'none',
                  width: 30,
                  textAlign: 'center',
                  fontSize: 8,
                  fontWeight: 600,
                  letterSpacing: '0.08em',
                  padding: '3px 0',
                  borderRadius: 999,
                  background: yes ? mix(SGS, 18) : mix(ACS, 18),
                  color: yes ? SG : AC,
                }}
              >
                {o.side}
              </span>
              <span style={{ flex: 1, minWidth: 0 }}>
                <span
                  className="num"
                  style={{ display: 'block', fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: T1 }}
                >
                  {o.ticker}
                </span>
                <span className="num" style={{ display: 'block', fontSize: 10, color: F, marginTop: 2 }}>
                  {(o.ts >= today0 ? o.t : new Date(o.ts).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })) + ` · ${o.qty} @ ${o.px}¢`}
                </span>
              </span>
              <span className="num" style={{ flex: 'none', textAlign: 'right', fontSize: 12, fontWeight: 600, color: pnlInk }}>
                {pnlText}
              </span>
            </div>
          );
        })}
        {rows.length === 0 && (
          <div style={{ padding: '26px 0', textAlign: 'center', fontSize: 12, color: T4 }}>
            {s.orders.length === 0 ? 'No tickets yet. Run a cycle to see paper fills here.' : 'No tickets match this filter.'}
          </div>
        )}
      </div>
    </div>
  );
}
