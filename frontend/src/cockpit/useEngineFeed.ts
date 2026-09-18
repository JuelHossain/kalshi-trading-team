/**
 * Connects the cockpit store to the running engine.
 *
 * One SSE subscription carries the narrative (logs, vault, state, errors);
 * two light polls carry what the stream does not: the Synapse queue
 * contents and the ledger's executed orders. A 240 ms clock advances the
 * visual transit beats and the progress arcs. Nothing here animates the
 * orbit; that is CSS.
 */
import { useCallback, useEffect, useRef } from 'react';
import { interpretEvent, levelOf, orderFromLedger, type FeedAction } from './engineEvents';
import { STATIONS } from './stations';
import { clock, useCockpit, type EngineConfig, type SettingsGroup, type StoreItem, type UpdateReport } from './store';

export const ENGINE_URL = '/api';

/** GET /config and the POST /config reply share this shape. */
export function applyConfigPayload(data: {
  runtime?: EngineConfig;
  groups?: SettingsGroup[];
  env_file?: string | null;
}): void {
  const st = useCockpit.getState();
  if (data.runtime && data.runtime.vault) st.setConfig(data.runtime);
  if (Array.isArray(data.groups)) st.setSettingsGroups(data.groups, data.env_file ?? null);
}

const IDLE_AFTER_MS = 45000;

interface QueueItem {
  ticker: string;
  title: string;
  yes_price?: number;
  side?: string;
}

export function applyFeedAction(action: FeedAction): void {
  const s = useCockpit.getState();
  switch (action.type) {
    case 'log':
      s.pushLog({ agent: action.agent, level: action.level, msg: action.msg, t: action.t });
      return;
    case 'beginWork':
      s.beginWork(action.i, action.expected);
      return;
    case 'completeWork':
      s.completeWork(action.i, action.ok, action.summary, action.detail, action.advance ?? true);
      return;
    case 'cycleStart':
      s.startCycle(action.n);
      return;
    case 'cycleComplete':
      s.finishCycle(action.n);
      return;
    case 'brainDone':
      s.setBrainDone(true);
      return;
    case 'soul': {
      const checks = s.soul.checks.map((c, i) =>
        action.patch.check === i ? { ...c, value: action.patch.value ?? c.value, ok: action.patch.value !== 'failed' && action.patch.value !== 'breached' } : c
      );
      s.patchSoul({ checks, sealed: action.patch.sealed ?? s.soul.sealed });
      return;
    }
    case 'senses': {
      const { swept, selected, market } = action.patch;
      const markets = market
        ? [...s.senses.markets.filter((m) => m.ticker !== market.ticker), { ticker: market.ticker, volume: market.volume, yes: '—' }].slice(-10)
        : s.senses.markets;
      s.patchSenses({
        swept: swept ?? s.senses.swept,
        selected: selected ?? s.senses.selected,
        markets,
      });
      return;
    }
    case 'brain': {
      const p = action.patch;
      const verdictChanged = p.verdict && p.verdict !== s.brain.verdict;
      s.patchBrain({
        ...(p.ticker !== undefined ? { ticker: p.ticker } : {}),
        ...('prob' in p ? { prob: p.prob ?? null } : {}),
        ...('conf' in p ? { conf: p.conf ?? null } : {}),
        ...('ev' in p ? { ev: p.ev ?? null } : {}),
        ...('verdict' in p ? { verdict: p.verdict ?? null } : {}),
        ...(p.side !== undefined ? { side: p.side } : {}),
        ...(p.price !== undefined ? { price: p.price } : {}),
        ...(p.reason !== undefined ? { reason: p.reason } : {}),
        analysed: s.brain.analysed + (verdictChanged ? 1 : 0),
        approved: s.brain.approved + (p.verdict === 'approved' ? 1 : 0),
      });
      return;
    }
    case 'hand': {
      const p = action.patch;
      const steps = p.step
        ? s.hand.steps.map((st, i) =>
            i === p.step!.index ? { ...st, meta: p.step!.meta, ok: p.step!.ok, bad: p.step!.bad, label: p.step!.label ?? st.label } : st
          )
        : s.hand.steps;
      const fresh = p.ticker !== undefined && p.ticker !== s.hand.ticker;
      s.patchHand({
        ...(p.ticker !== undefined ? { ticker: p.ticker } : {}),
        ...(p.side !== undefined ? { side: p.side } : {}),
        ...(p.price !== undefined ? { price: p.price } : {}),
        ...(p.stake !== undefined ? { stake: p.stake } : {}),
        ...(p.count !== undefined ? { count: p.count } : {}),
        ...(p.fault !== undefined ? { fault: p.fault } : {}),
        steps: fresh && !p.step ? s.hand.steps.map((st) => ({ ...st, meta: '—', ok: false, bad: false })) : steps,
      });
      return;
    }
    case 'order':
      s.addOrder(action.order);
      return;
    case 'fault':
      s.markFault();
      return;
    case 'locked':
      s.setLocked(action.locked);
      return;
    case 'autopilot':
      s.setEngine({ autopilot: action.enabled });
      return;
    case 'processing':
      s.setEngine({ processing: action.processing });
      return;
    case 'balance':
      s.setBalance(action.balance, action.principal);
      return;
    case 'idle':
      s.setIdle();
      return;
    default:
      return;
  }
}

const post = (path: string, body?: unknown) =>
  fetch(`${ENGINE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

export function useEngineFeed(enabled: boolean, isPaperTrading: boolean) {
  const started = useRef(false);

  useEffect(() => {
    if (!enabled) return;
    const store = useCockpit;
    let alive = true;

    const syncStatus = async () => {
      try {
        const res = await fetch(`${ENGINE_URL}/autopilot/status`);
        const data = await res.json();
        if (!alive) return;
        store.getState().setEngine({
          connected: true,
          autopilot: !!data.autopilot_enabled,
          processing: !!data.is_processing,
          cycle: Number(data.cycle_count) || 0,
        });
        if (data.is_locked_down) store.getState().setLocked(true);
      } catch {
        if (alive) store.getState().setEngine({ connected: false });
      }
    };

    const pollHealth = async () => {
      try {
        const res = await fetch(`${ENGINE_URL}/health`);
        const data = await res.json();
        if (!alive) return;
        const st = store.getState();
        st.setEngine({
          connected: true,
          cycle: Math.max(st.cycle, Number(data.cycle) || 0),
          errorBox: Number(data.error_box) || 0,
          halted: Array.isArray(data.halted) ? data.halted.map(String) : [],
          ...(typeof data.processing === 'boolean' ? { processing: data.processing } : {}),
        });
        if (data.kill_switch === true && !st.kill) st.setLocked(true);
        if (data.kill_switch === false && st.kill) st.setLocked(false);
        if (typeof data.balance === 'number') st.setBalance(data.balance);
      } catch {
        if (alive) store.getState().setEngine({ connected: false });
      }
    };

    const pollConfig = async () => {
      try {
        const res = await fetch(`${ENGINE_URL}/config`);
        const data = await res.json();
        if (!alive || !data) return;
        applyConfigPayload(data);
      } catch {
        /* the Config screen says it is waiting */
      }
    };

    // Seed the trace with what the engine already logged, so an open
    // dashboard never starts blank after the engine has been running.
    const seedJournal = async () => {
      try {
        const res = await fetch(`${ENGINE_URL}/journal?topic=SYSTEM_LOG&limit=40`);
        const data = await res.json();
        if (!alive || !Array.isArray(data.events)) return;
        const st = store.getState();
        if (st.logs.length > 1) return;
        for (const ev of [...data.events].reverse()) {
          if (String(ev.level).toUpperCase() === 'DEBUG') continue;
          st.pushLog({
            agent: !ev.agent || ev.agent === 'GHOST' ? 'Engine' : ev.agent.charAt(0) + ev.agent.slice(1).toLowerCase(),
            level: levelOf(String(ev.level)),
            msg: String(ev.message || ''),
            t: clock(Date.parse(ev.ts) || Date.now()),
          });
        }
      } catch {
        /* optional */
      }
    };

    const pollQueues = async () => {
      try {
        const res = await fetch(`${ENGINE_URL}/synapse/queues`);
        const data = await res.json();
        if (!alive) return;
        const opp: QueueItem[] = data.opportunities?.items ?? [];
        const exe: QueueItem[] = data.executions?.items ?? [];
        const oppDepth = Number(data.opportunities?.size || 0);
        const execDepth = Number(data.executions?.size || 0);
        const depth = oppDepth + execDepth;
        const atLimit = !!data.flow_control?.execution_queue_at_limit;
        const items: StoreItem[] = [
          ...exe.map((e, i) => ({
            ticker: e.ticker,
            title: `Verdict · ${(e.side || 'YES').toUpperCase()}${e.title ? ' · ' + e.title : ''}`,
            state: (i === 0 ? 'next out' : atLimit ? 'waiting' : 'stored') as StoreItem['state'],
          })),
          ...opp.map((o) => ({
            ticker: o.ticker,
            title: o.title || 'Opportunity',
            state: 'stored' as StoreItem['state'],
          })),
        ];
        const st = store.getState();
        st.setQueues(oppDepth, execDepth, items, atLimit);
        if (opp.length) {
          const priced = st.senses.markets.map((m) => {
            const hit = opp.find((o) => o.ticker === m.ticker);
            return hit && typeof hit.yes_price === 'number' ? { ...m, yes: `${hit.yes_price}¢` } : m;
          });
          st.patchSenses({ markets: priced });
        }
        // Nothing queued, nothing processing, nothing heard for a while: the
        // engine is between cycles and the star should go dark.
        const now = Date.now();
        if (
          depth === 0 &&
          !st.processing &&
          st.brainDone &&
          st.beat === 'work' &&
          now - st.lastActivity > IDLE_AFTER_MS
        ) {
          st.setIdle();
        }
      } catch {
        /* the health poll owns the connected flag */
      }
    };

    const pollOrders = async () => {
      try {
        const res = await fetch(`${ENGINE_URL}/orders?limit=200`);
        const data = await res.json();
        if (!alive || !Array.isArray(data.orders)) return;
        const st = store.getState();
        const fromLedger = data.orders.map(orderFromLedger).reverse();
        // Live fills seen this session that the ledger has not yet exposed
        // stay; once the ledger row exists it replaces the live one.
        const known = new Set(fromLedger.map((o) => `${o.ticker}|${o.px}|${o.qty}`));
        const live = st.orders.filter((o) => o.id.startsWith('live-') && !known.has(`${o.ticker}|${o.px}|${o.qty}`));
        st.setOrders([...fromLedger, ...live].sort((a, b) => a.ts - b.ts));
      } catch {
        /* optional data */
      }
    };

    if (!started.current) {
      started.current = true;
      store.getState().pushLog({ agent: 'Cockpit', level: 'info', msg: 'Attached · listening to /api/stream' });
    }
    void syncStatus();
    void pollConfig();
    void seedJournal();
    void pollHealth();
    void pollQueues();
    void pollOrders();

    const es = new EventSource(`${ENGINE_URL}/stream`);
    es.onopen = () => store.getState().setEngine({ connected: true });
    es.onmessage = (event) => {
      let data;
      try {
        data = JSON.parse(event.data);
      } catch {
        return;
      }
      for (const action of interpretEvent(data)) applyFeedAction(action);
      if (data.type === 'LOG' && /ORDER EXECUTED/.test(data.log?.message || '')) {
        setTimeout(() => void pollOrders(), 1500);
      }
    };
    es.onerror = () => store.getState().setEngine({ connected: false });

    const ticker = setInterval(() => store.getState().tick(Date.now()), 240);
    const qi = setInterval(() => void pollQueues(), 2500);
    const hi = setInterval(() => void pollHealth(), 5000);
    const oi = setInterval(() => void pollOrders(), 20000);
    const ci = setInterval(() => void pollConfig(), 60000);

    return () => {
      alive = false;
      es.close();
      clearInterval(ticker);
      clearInterval(qi);
      clearInterval(hi);
      clearInterval(oi);
      clearInterval(ci);
    };
  }, [enabled]);

  const runCycle = useCallback(async () => {
    try {
      await post('/trigger', { isPaperTrading });
    } catch (e) {
      useCockpit.getState().pushLog({ agent: 'Engine', level: 'err', msg: `Trigger failed: ${String(e).slice(0, 60)}` });
    }
  }, [isPaperTrading]);

  const cancelCycle = useCallback(async () => {
    try {
      await post('/autopilot/stop', { isPaperTrading });
      await post('/cancel');
      useCockpit.getState().setEngine({ autopilot: false, processing: false });
    } catch (e) {
      useCockpit.getState().pushLog({ agent: 'Engine', level: 'err', msg: `Cancel failed: ${String(e).slice(0, 60)}` });
    }
  }, [isPaperTrading]);

  const setAutopilot = useCallback(
    async (enabled: boolean) => {
      try {
        const res = await post(enabled ? '/autopilot/start' : '/autopilot/stop', { isPaperTrading });
        if (res.ok) useCockpit.getState().setEngine({ autopilot: enabled });
      } catch (e) {
        useCockpit.getState().pushLog({ agent: 'Engine', level: 'err', msg: `Autopilot failed: ${String(e).slice(0, 60)}` });
      }
    },
    [isPaperTrading]
  );

  const setKill = useCallback(async (engaged: boolean) => {
    try {
      const res = await post(engaged ? '/kill-switch' : '/deactivate-kill-switch');
      if (res.ok) useCockpit.getState().setLocked(engaged);
    } catch (e) {
      useCockpit.getState().pushLog({ agent: 'Engine', level: 'err', msg: `Kill switch failed: ${String(e).slice(0, 60)}` });
    }
  }, []);

  /** POST /config. Returns the engine's report; the store is updated from the reply. */
  const updateSettings = useCallback(async (changes: Record<string, unknown>): Promise<UpdateReport> => {
    try {
      const res = await post('/config', { changes });
      const body = await res.json();
      const report: UpdateReport = {
        applied: body.applied ?? [],
        restart_required: body.restart_required ?? [],
        errors: body.errors ?? (res.ok ? {} : { _: body.message || `HTTP ${res.status}` }),
      };
      if (body.config) applyConfigPayload(body.config);
      useCockpit.getState().setReport(report);
      return report;
    } catch (e) {
      const report: UpdateReport = { applied: [], restart_required: [], errors: { _: String(e).slice(0, 80) } };
      useCockpit.getState().setReport(report);
      return report;
    }
  }, []);

  /** POST /reset: drain the error box and lift a lockdown so cycles can run again. */
  const resetEngine = useCallback(async () => {
    try {
      const res = await post('/reset');
      const body = await res.json();
      const st = useCockpit.getState();
      st.setEngine({ errorBox: 0, halted: [] });
      st.pushLog({ agent: 'Engine', level: 'ok', msg: `Reset · ${body.errors_cleared ?? 0} error(s) cleared from the box` });
    } catch (e) {
      useCockpit.getState().pushLog({ agent: 'Engine', level: 'err', msg: `Reset failed: ${String(e).slice(0, 60)}` });
    }
  }, []);

  const restartEngine = useCallback(async () => {
    try {
      const res = await post('/engine/restart');
      if (res.ok) {
        const st = useCockpit.getState();
        st.clearRestartPending();
        st.pushLog({ agent: 'Engine', level: 'warn', msg: 'Restarting…' });
        st.setEngine({ connected: false });
      }
    } catch (e) {
      useCockpit.getState().pushLog({ agent: 'Engine', level: 'err', msg: `Restart failed: ${String(e).slice(0, 60)}` });
    }
  }, []);

  return { runCycle, cancelCycle, setAutopilot, setKill, updateSettings, restartEngine, resetEngine };
}

export const stationLabel = (i: number) => STATIONS[i]?.name ?? '';
