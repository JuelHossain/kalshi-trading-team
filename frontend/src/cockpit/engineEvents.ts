/**
 * Turns the engine's event stream into cockpit store updates.
 *
 * The engine narrates itself through SYSTEM_LOG lines. This module knows
 * what those lines look like (the strings come from the agents' log calls)
 * and maps each one onto the beat machine: which agent is working, when it
 * finished, what it produced. Pure functions over the event payloads, so the
 * mapping is testable without a socket.
 */
import { agentIndexFor, STATIONS } from './stations';
import type { LogLevel, Order } from './store';
import { clock } from './store';

export interface EngineLog {
  id?: string;
  timestamp?: string;
  agentId: number;
  cycleId?: number;
  message: string;
  level: string;
}

export interface EngineEvent {
  type: 'LOG' | 'VAULT' | 'SIMULATION' | 'STATE' | 'ERROR' | string;
  log?: EngineLog;
  state?: Record<string, unknown>;
  error?: { agentId: number; code: string; message: string; severity: string; timestamp?: string };
}

export type FeedAction =
  | { type: 'log'; agent: string; level: LogLevel; msg: string; t?: string }
  | { type: 'beginWork'; i: number; expected?: number }
  | { type: 'completeWork'; i: number; ok: boolean; summary: string; detail?: [string, string][]; advance?: boolean }
  | { type: 'cycleStart'; n: number }
  | { type: 'cycleComplete'; n: number }
  | { type: 'brainDone' }
  | { type: 'soul'; patch: { check?: number; value?: string; sealed?: boolean } }
  | { type: 'senses'; patch: { swept?: number; selected?: number; market?: { ticker: string; volume: number } } }
  | {
      type: 'brain';
      patch: Partial<{
        ticker: string;
        prob: number;
        conf: number;
        ev: number;
        verdict: 'approved' | 'vetoed' | 'skipped';
        side: string;
        price: number;
        reason: string;
      }>;
    }
  | {
      type: 'hand';
      patch: Partial<{
        ticker: string;
        side: string;
        price: number;
        stake: number;
        count: number;
        step: { index: number; meta: string; ok: boolean; bad: boolean; label?: string };
        fault: string | null;
      }>;
    }
  | { type: 'order'; order: Order }
  | { type: 'fault' }
  | { type: 'locked'; locked: boolean }
  | { type: 'autopilot'; enabled: boolean }
  | { type: 'processing'; processing: boolean }
  | { type: 'balance'; balance: number; principal?: number }
  | { type: 'idle' };

const AGENT_NAMES: Record<number, string> = { 1: 'Soul', 2: 'Senses', 3: 'Brain', 4: 'Hand', 5: 'Gateway' };

export const levelOf = (level: string): LogLevel => {
  const l = (level || '').toUpperCase();
  if (l === 'SUCCESS') return 'ok';
  if (l === 'WARN' || l === 'WARNING') return 'warn';
  if (l === 'ERROR' || l === 'CRITICAL') return 'err';
  return 'info';
};

const money = (s: string) => parseFloat(s.replace(/[$,]/g, ''));

/** Map one SYSTEM_LOG line onto cockpit actions. */
export function interpretLog(log: EngineLog): FeedAction[] {
  const raw = (log.message || '').trim();
  const level = (log.level || 'INFO').toUpperCase();
  if (level === 'DEBUG') return [];

  const msg = raw.replace(/^SUCCESS:\s*/, '');
  const isGhost = /^\[GHOST\]/.test(msg) || /^CYCLE #\d+ COMPLETE/.test(msg) || /^Cycle \d+ not authorized/.test(msg);
  const agentName = isGhost ? 'Engine' : AGENT_NAMES[log.agentId] || 'Engine';
  const t = log.timestamp ? clock(Date.parse(log.timestamp) || Date.now()) : undefined;
  const out: FeedAction[] = [{ type: 'log', agent: agentName, level: levelOf(level), msg, t }];
  const push = (a: FeedAction) => out.push(a);
  let m: RegExpMatchArray | null;

  // ── the engine itself
  if ((m = msg.match(/CYCLE #(\d+) START/))) {
    push({ type: 'cycleStart', n: Number(m[1]) });
    push({ type: 'beginWork', i: 0 });
    return out;
  }
  if ((m = msg.match(/CYCLE #(\d+) COMPLETE/))) {
    push({ type: 'cycleComplete', n: Number(m[1]) });
    return out;
  }
  if (/MANUAL KILL SWITCH ACTIVATED/.test(msg)) {
    push({ type: 'locked', locked: true });
    return out;
  }
  if (/MANUAL KILL SWITCH DEACTIVATED/.test(msg)) {
    push({ type: 'locked', locked: false });
    return out;
  }
  if (/Cycle cancelled by user/.test(msg)) {
    push({ type: 'autopilot', enabled: false });
    push({ type: 'idle' });
    return out;
  }

  const i = agentIndexFor(log.agentId);

  // ── Soul
  if (i === 0) {
    if (/Initiating pre-flight sequence/.test(msg)) push({ type: 'beginWork', i: 0 });
    else if ((m = msg.match(/PRE-FLIGHT API CHECK PASSED \(([^)]*)\)/))) {
      // The engine names only what actually passed; Gemini is left out when
      // it did not answer, so the tile must not claim it.
      const passed = m[1].split(',').map((x) => x.trim()).filter(Boolean);
      push({ type: 'soul', patch: { check: 0, value: `${passed.join(' · ')} reachable` } });
    }
    else if (/OPENING PRE-FLIGHT CHECK FAILED/.test(msg)) {
      push({ type: 'soul', patch: { check: 0, value: 'failed' } });
      push({ type: 'fault' });
      push({ type: 'completeWork', i: 0, ok: false, summary: 'Refused — pre-flight failed', detail: [['Pre-flight', msg.slice(0, 80)]], advance: false });
    } else if (/Health check: All systems nominal/.test(msg)) {
      push({ type: 'soul', patch: { check: 1, value: 'above the $255 floor' } });
      push({ type: 'soul', patch: { check: 2, value: 'all systems nominal' } });
    } else if (/^EMERGENCY:/.test(msg)) {
      push({ type: 'soul', patch: { check: 1, value: 'breached' } });
      push({ type: 'fault' });
      push({ type: 'completeWork', i: 0, ok: false, summary: 'Refused — hard floor breached', detail: [['Vault', msg.slice(11, 90)]], advance: false });
    } else if (/Pre-flight complete/.test(msg)) {
      push({ type: 'soul', patch: { sealed: true } });
      push({ type: 'completeWork', i: 0, ok: true, summary: 'Authorized the cycle', detail: [['Pre-flight', 'passed'], ['Hand-off', 'Senses']] });
    } else if (/AUTOPILOT ENABLED/.test(msg)) push({ type: 'autopilot', enabled: true });
    else if (/AUTOPILOT DISABLED/.test(msg)) push({ type: 'autopilot', enabled: false });
    else if (/SYSTEM LOCKDOWN|FATAL ERROR/.test(msg)) push({ type: 'fault' });
    return out;
  }

  // ── Senses
  if (i === 1) {
    if (/Initiating passive market scan|Restock request received|Stock buffer low|rescanning|Brain idle; queueing/.test(msg))
      push({ type: 'beginWork', i: 1 });
    else if ((m = msg.match(/Selected (\d+) tradeable markets from (\d+) scanned/))) {
      push({ type: 'senses', patch: { selected: Number(m[1]), swept: Number(m[2]) } });
    } else if ((m = msg.match(/Queued to Synapse: (\S+) \(Queue Size: (\d+)\)(?: \| Volume: ([\d.]+))?/))) {
      push({ type: 'senses', patch: { market: { ticker: m[1], volume: Number(m[3] || 0) } } });
    } else if ((m = msg.match(/Signaled Brain: OPPORTUNITIES_READY|Restocked: (\d+) opportunities/))) {
      // Logged only when markets were actually queued. "Scan complete" is
      // logged after an empty scan too, so it cannot mean success.
      const n = m[1] ? Number(m[1]) : undefined;
      push({
        type: 'completeWork',
        i: 1,
        ok: true,
        summary: n !== undefined ? `Restocked ${n} markets` : 'Swept the board and shortlisted',
        detail: n !== undefined ? [['Queued', `${n} markets`]] : [],
      });
    } else if (/No markets found to scan|No new tradeable markets to queue|Stock buffer empty|Nothing cleared|No tradeable/.test(msg)) {
      push({ type: 'completeWork', i: 1, ok: false, summary: 'Nothing new cleared the filters', detail: [['Queued', '0 markets']], advance: false });
    } else if (/already complete\. Senses in STANDBY/.test(msg)) {
      // Nothing to fetch this cycle: stock on hand or the Brain still busy.
      push({ type: 'completeWork', i: 1, ok: true, summary: 'Standby — markets already queued', detail: [], advance: false });
    } else if (/Kalshi fetch error on page \d+/.test(msg)) {
      // One page failed; the scan keeps what it had and still reports.
    } else if (/Kalshi fetch error|Kalshi client not initialized/.test(msg)) {
      push({ type: 'fault' });
      push({ type: 'completeWork', i: 1, ok: false, summary: 'Kalshi fetch failed', detail: [['Error', msg.slice(0, 90)]], advance: false });
    }
    return out;
  }

  // ── Brain
  if (i === 2) {
    if ((m = msg.match(/Found (\d+) opportunities\. Processing batch/))) push({ type: 'beginWork', i: 2 });
    else if ((m = msg.match(/^Synapse Input: (\S+)/))) {
      push({ type: 'beginWork', i: 2 });
      push({ type: 'brain', patch: { ticker: m[1], prob: undefined, conf: undefined, ev: undefined, verdict: undefined, reason: '' } });
    } else if ((m = msg.match(/AI Prob: ([\d.]+|N\/A) \| Conf: ([\d.]+)% \| EV: (-?[\d.]+)/))) {
      push({
        type: 'brain',
        patch: {
          prob: m[1] === 'N/A' ? undefined : Number(m[1]),
          conf: Number(m[2]),
          ev: Number(m[3]),
        },
      });
    } else if ((m = msg.match(/APPROVED: (\S+) \| Buying (YES|NO) @ (\d+)c/))) {
      push({ type: 'brain', patch: { ticker: m[1], verdict: 'approved', side: m[2], price: Number(m[3]) } });
      push({
        type: 'completeWork',
        i: 2,
        ok: true,
        summary: `Issued a verdict · buy ${m[2]} @ ${m[3]}¢`,
        detail: [['Market', m[1]], ['Verdict', `buy ${m[2]} @ ${m[3]}¢`]],
      });
    } else if ((m = msg.match(/VETOED: (\S+) \| (?:Reason: )?(.+)$/))) {
      push({ type: 'brain', patch: { ticker: m[1], verdict: 'vetoed', reason: m[2] } });
      push({
        type: 'completeWork',
        i: 2,
        ok: true,
        summary: `Stood down — ${m[2].slice(0, 60)}`,
        detail: [['Market', m[1]], ['Reason', m[2].slice(0, 90)]],
        advance: false,
      });
    } else if ((m = msg.match(/\[STALE\] Opportunity expired: (\S+)/))) {
      push({ type: 'brain', patch: { ticker: m[1], verdict: 'skipped', reason: 'stale' } });
    } else if ((m = msg.match(/SKIPPED: (\S+)/))) {
      push({ type: 'brain', patch: { ticker: m[1], verdict: 'skipped', reason: 'no usable probability' } });
    } else if (/Batch complete/.test(msg)) push({ type: 'brainDone' });
    else if (/Monitor loop DIED|Primary AI failed/.test(msg)) push({ type: 'fault' });
    return out;
  }

  // ── Hand
  if (i === 3) {
    if (/Execution signal received/.test(msg)) push({ type: 'beginWork', i: 3 });
    else if ((m = msg.match(/^Target acquired: (\S+)/))) push({ type: 'hand', patch: { ticker: m[1], fault: null } });
    else if ((m = msg.match(/^Already holding (\S+)/))) {
      push({ type: 'hand', patch: { ticker: m[1], step: { index: 0, meta: 'held', ok: false, bad: true, label: 'Already holding this market' } } });
      push({ type: 'completeWork', i: 3, ok: false, summary: 'Skipped — already holding', detail: [['Market', m[1]], ['Guard', 'no stacking']], advance: false });
    } else if ((m = msg.match(/Snipe check failed: (.+)$/))) {
      push({ type: 'hand', patch: { fault: m[1], step: { index: 0, meta: m[1].slice(0, 28), ok: false, bad: true } } });
      push({ type: 'completeWork', i: 3, ok: false, summary: `Refused — ${m[1].slice(0, 50)}`, detail: [['Snipe check', m[1].slice(0, 90)]], advance: false });
    } else if ((m = msg.match(/No stake for (\S+)/))) {
      push({ type: 'hand', patch: { ticker: m[1], step: { index: 1, meta: 'no stake', ok: false, bad: true } } });
      push({ type: 'completeWork', i: 3, ok: false, summary: 'Stood down — edge does not justify a stake', detail: [['Market', m[1]]], advance: false });
    } else if ((m = msg.match(/Kelly sizing: \$([\d.]+) \((YES|NO) p=([\d.]+) @ (\d+)c, edge ([+-]?[\d.]+)\)/))) {
      push({
        type: 'hand',
        patch: {
          side: m[2],
          price: Number(m[4]),
          stake: money(m[1]),
          count: Math.floor((money(m[1]) * 100) / Number(m[4])),
          step: { index: 0, meta: `${m[4]}¢ ask`, ok: true, bad: false },
        },
      });
      push({ type: 'hand', patch: { step: { index: 1, meta: `$${m[1]} · edge ${m[5]}`, ok: true, bad: false } } });
    } else if ((m = msg.match(/ORDER EXECUTED: (YES|NO) (\S+) @ (\d+)¢ for \$([\d.]+)/))) {
      const px = Number(m[3]);
      const stake = money(m[4]);
      const qty = Math.max(1, Math.floor((stake * 100) / px));
      push({ type: 'hand', patch: { ticker: m[2], side: m[1], price: px, stake, count: qty, step: { index: 2, meta: 'paper fill', ok: true, bad: false }, fault: null } });
      push({
        type: 'order',
        order: {
          id: `live-${log.id || Date.now()}`,
          ts: log.timestamp ? Date.parse(log.timestamp) || Date.now() : Date.now(),
          t: t ?? clock(),
          ticker: m[2],
          side: m[1] as 'YES' | 'NO',
          qty,
          px,
          status: 'open',
          pnl: null,
        },
      });
      push({
        type: 'completeWork',
        i: 3,
        ok: true,
        summary: `Filled ${qty} ${m[1]} @ ${px}¢`,
        detail: [['Market', m[2]], ['Fill', `${qty} @ ${px}¢ · $${stake.toFixed(2)}`], ['Slippage', '0¢ · paper']],
      });
    } else if ((m = msg.match(/ORDER FAILED: (.+)$/))) {
      push({ type: 'hand', patch: { fault: m[1], step: { index: 2, meta: 'failed', ok: false, bad: true } } });
      push({ type: 'fault' });
      push({ type: 'completeWork', i: 3, ok: false, summary: `Rejected — ${m[1].slice(0, 50)}`, detail: [['Error', m[1].slice(0, 90)]], advance: false });
    } else if ((m = msg.match(/^EXIT (YES|NO) (\S+): (.+)$/))) {
      push({ type: 'hand', patch: { ticker: m[2], side: m[1] } });
    }
    return out;
  }

  return out;
}

/** Map one SSE frame onto cockpit actions. */
export function interpretEvent(ev: EngineEvent): FeedAction[] {
  if (ev.type === 'LOG' && ev.log) return interpretLog(ev.log);
  if (ev.type === 'VAULT' && ev.state) {
    const total = Number(ev.state.total);
    const principal = Number(ev.state.principal);
    if (Number.isFinite(total)) return [{ type: 'balance', balance: total, principal: Number.isFinite(principal) && principal > 0 ? principal : undefined }];
    return [];
  }
  if (ev.type === 'SIMULATION' && ev.state) {
    // The Brain's own maths for the market it just judged: EV per $1
    // contract and whether the gates vetoed it.
    const ticker = String(ev.state.ticker || '');
    const ev_score = Number(ev.state.ev_score);
    if (!ticker || !Number.isFinite(ev_score)) return [];
    return [{ type: 'brain', patch: { ticker, ev: ev_score } }];
  }
  if (ev.type === 'STATE' && ev.state) {
    const out: FeedAction[] = [];
    if (typeof ev.state.isProcessing === 'boolean') out.push({ type: 'processing', processing: ev.state.isProcessing });
    return out;
  }
  if (ev.type === 'ERROR' && ev.error) {
    const e = ev.error;
    const out: FeedAction[] = [
      { type: 'log', agent: AGENT_NAMES[e.agentId] || 'Engine', level: 'err', msg: `${e.code} — ${e.message}` },
    ];
    if (/CRITICAL|HIGH/i.test(e.severity)) out.push({ type: 'fault' });
    return out;
  }
  return [];
}

/** Shape a ledger row from GET /orders into an Order. */
export function orderFromLedger(row: {
  id: number;
  decided_at: string;
  ticker: string;
  side: string;
  price_cents: number | null;
  count: number | null;
  pnl_cents: number | null;
  settled_yes: number | null;
  exited_at?: string | null;
  closed?: boolean;
}): Order {
  const ts = Date.parse(row.decided_at) || Date.now();
  // A position closed early (an exit, or Ragnarok) has no settled_yes for
  // however long it takes the market to resolve, but it is not "open" any
  // more -- and once ledger.recent_fills has an exit price, pnl_cents is
  // already the realised result, not a settlement placeholder. Fall back to
  // settled_yes/exited_at for older payloads that predate `closed`.
  const closed =
    row.closed ??
    ((row.settled_yes !== null && row.settled_yes !== undefined) ||
      (row.exited_at !== null && row.exited_at !== undefined));
  return {
    id: `ledger-${row.id}`,
    ts,
    t: clock(ts),
    ticker: row.ticker,
    side: (row.side || 'yes').toUpperCase() === 'NO' ? 'NO' : 'YES',
    qty: row.count ?? 0,
    px: row.price_cents ?? 0,
    status: closed ? 'filled' : 'open',
    pnl: row.pnl_cents === null || row.pnl_cents === undefined ? null : row.pnl_cents / 100,
  };
}

export const stationName = (i: number) => STATIONS[i]?.name ?? 'Engine';
