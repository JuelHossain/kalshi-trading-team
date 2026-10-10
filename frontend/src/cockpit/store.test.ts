import { beforeEach, describe, expect, it } from 'vitest';
import { storeCapacity, typicalMs, useCockpit } from './store';
import { STATIONS } from './stations';

describe('the beat machine is driven by measured events, not guesses', () => {
  beforeEach(() => {
    useCockpit.getState().reset();
  });

  it('measures a hand-off at the star from completion to the next agent starting', async () => {
    const s = useCockpit.getState();
    s.startCycle(1);
    s.beginWork(0);
    s.completeWork(0, true, 'Authorized the cycle');
    await new Promise((r) => setTimeout(r, 30));
    s.beginWork(1);

    const hops = useCockpit.getState().runs.filter((r) => r.kind === 'core');
    expect(hops).toHaveLength(1);
    expect(hops[0].hop).toBe(0);
    expect(hops[0].ms).toBeGreaterThanOrEqual(25);
    expect(hops[0].detail[2]).toEqual(['Woke', 'Senses']);
  });

  it('does not invent a hop for a veto', () => {
    const s = useCockpit.getState();
    s.beginWork(2);
    s.completeWork(2, true, 'Stood down', [], false);
    s.beginWork(3);
    expect(useCockpit.getState().runs.filter((r) => r.kind === 'core')).toHaveLength(0);
  });

  it('keeps the star depth exactly what the queues report', () => {
    const s = useCockpit.getState();
    s.setQueues(6, 1, [], false);
    s.beginWork(1);
    s.completeWork(1, true, 'Swept');
    // advance through the visual throw and catch
    s.tick(Date.now() + 2000);
    expect(useCockpit.getState().storeDepth).toBe(7);
    expect(useCockpit.getState().beat).toBe('flare');
  });

  it('uses the station fallback until a run is measured, then the median', () => {
    expect(typicalMs([], 2)).toBe(STATIONS[2].dur);
    const runs = [900, 12000, 15000].map((ms, i) => ({
      id: String(i),
      kind: 'agent' as const,
      agent: 2,
      cycle: 1,
      ok: true,
      ms,
      ts: 0,
      summary: '',
      detail: [] as [string, string][],
    }));
    expect(typicalMs(runs, 2)).toBe(12000);
    expect(typicalMs(runs, 0)).toBe(STATIONS[0].dur);
  });

  it('takes the store capacity from the engine config', () => {
    expect(storeCapacity(null)).toBe(10);
    const s = useCockpit.getState();
    s.setConfig({
      paper_pinned: true,
      live_armed: false,
      kalshi_env: 'demo',
      brain: { model: 'm', min_edge: 0.05, confidence_threshold: 0.85, estimate_samples: 3, max_disagreement: 0.2, stale_opportunity_seconds: 300, search_grounding: true },
      senses: { min_volume: 200, max_spread_cents: 8, max_days_to_close: 10, stock_buffer_size: 30, queue_batch_size: 10 },
      hand: { max_stake_cents: 7500, kelly_fraction: 0.25, stop_loss_pct: 0.5, take_profit_pct: 0.8, exit_before_expiry_hours: 2 },
      vault: { principal_cents: 30000, hard_floor_cents: 25500, kill_switch_pct: 0.85, profit_lock_cents: 5000, is_locked: false, kill_switch_active: false },
      queues: { max_execution: 10, max_opportunity: 20 },
      min_cycle_interval_seconds: 30,
    });
    expect(storeCapacity(useCockpit.getState().config)).toBe(30);
    expect(useCockpit.getState().principal).toBe(300);
  });
});
