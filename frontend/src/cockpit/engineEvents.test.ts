import { describe, it, expect } from 'vitest';
import { interpretEvent, interpretLog, orderFromLedger } from './engineEvents';

// Every message below is a real line from an engine run log.
const log = (agentId: number, message: string, level = 'INFO') => ({
  id: 'x',
  timestamp: '2026-09-18T02:53:27',
  agentId,
  message,
  level,
});

const types = (actions: { type: string }[]) => actions.map((a) => a.type);

describe('interpretLog', () => {
  it('opens the cycle and puts the Soul to work', () => {
    const a = interpretLog(log(1, '[GHOST] CYCLE #3 START - 4 Pillars Activated'));
    expect(types(a)).toEqual(['log', 'cycleStart', 'beginWork']);
    expect(a[1]).toMatchObject({ n: 3 });
    expect(a[2]).toMatchObject({ i: 0 });
  });

  it('turns the Soul hand-off into a completed run and a throw', () => {
    const a = interpretLog(log(1, 'Pre-flight complete. Handing off to SENSES.'));
    expect(types(a)).toEqual(['log', 'soul', 'completeWork']);
    expect(a[2]).toMatchObject({ i: 0, ok: true, summary: 'Authorized the cycle' });
  });

  it('reads the Senses selection line', () => {
    const a = interpretLog(
      log(2, 'Selected 7 tradeable markets from 4000 scanned (volume >= 200, spread <= 8c, closing within 10d)')
    );
    expect(a[1]).toEqual({ type: 'senses', patch: { selected: 7, swept: 4000 } });
  });

  it('adds a queued market to the shortlist', () => {
    const a = interpretLog(
      log(2, '[OK] Queued to Synapse: KXNFLGAME-26SEP21NYGLAR-NYG (Queue Size: 3) | Volume: 41230.0')
    );
    expect(a[1]).toEqual({
      type: 'senses',
      patch: { market: { ticker: 'KXNFLGAME-26SEP21NYGLAR-NYG', volume: 41230 } },
    });
  });

  it('starts Brain work per market and records the estimate', () => {
    expect(types(interpretLog(log(3, 'Synapse Input: KXNASCARRACE-BASPSN26-DEHA')))).toEqual([
      'log',
      'beginWork',
      'brain',
    ]);
    const est = interpretLog(log(3, 'AI Prob: 0.02 | Conf: 88.0% | EV: 0.010'));
    expect(est[1]).toEqual({ type: 'brain', patch: { prob: 0.02, conf: 88, ev: 0.01 } });
  });

  it('turns an approval into a verdict and a throw', () => {
    const a = interpretLog(
      log(3, '[OK] APPROVED: KXNFLGAME-26SEP21NYGLAR-LAR | Buying NO @ 23c | Pushing to execution.')
    );
    expect(a[1]).toMatchObject({ type: 'brain', patch: { verdict: 'approved', side: 'NO', price: 23 } });
    expect(a[2]).toMatchObject({ type: 'completeWork', i: 2, ok: true });
  });

  it('records a veto as a clean stand-down, not a failure', () => {
    const a = interpretLog(
      log(3, '[X] VETOED: KXNFLSPREAD-26SEP21NYGLAR-LAR3 | Reason: Edge +0.020 below minimum +0.050')
    );
    expect(a[1]).toMatchObject({ type: 'brain', patch: { verdict: 'vetoed' } });
    // A veto is a clean run, but nothing leaves the Brain: no throw.
    expect(a[2]).toMatchObject({ type: 'completeWork', ok: true, advance: false });
    expect((a[2] as { summary: string }).summary).toMatch(/Stood down/);
  });

  it('marks the batch drained', () => {
    const a = interpretLog(log(3, 'Batch complete. All opportunities processed.', 'SUCCESS'));
    expect(types(a)).toEqual(['log', 'brainDone']);
    expect(a[0]).toMatchObject({ level: 'ok', msg: 'Batch complete. All opportunities processed.' });
  });

  it('parses the Hand sizing and the fill into an order', () => {
    const sizing = interpretLog(log(4, 'Kelly sizing: $3.28 (NO p=0.98 @ 23c, edge +0.010)'));
    expect(sizing[1]).toMatchObject({ type: 'hand', patch: { side: 'NO', price: 23, stake: 3.28, count: 14 } });

    const fill = interpretLog(log(4, 'ORDER EXECUTED: NO KXNFLGAME-26SEP21NYGLAR-LAR @ 23¢ for $3.28'));
    const order = fill.find((a) => a.type === 'order') as { order: { qty: number; px: number; side: string } };
    expect(order.order).toMatchObject({ side: 'NO', px: 23, qty: 14 });
    expect(fill.at(-1)).toMatchObject({ type: 'completeWork', i: 3, ok: true });
  });

  it('flags a failed order as a fault', () => {
    const a = interpretLog(log(4, 'ORDER FAILED: Insufficient funds: available=$1.00, required=$3.28', 'ERROR'));
    expect(types(a)).toContain('fault');
    expect(a.at(-1)).toMatchObject({ type: 'completeWork', ok: false });
  });

  it('ignores DEBUG chatter entirely', () => {
    expect(interpretLog(log(3, 'Starting continuous queue monitoring loop...', 'DEBUG'))).toEqual([]);
  });

  it('locks and unlocks on the kill switch lines', () => {
    expect(interpretLog(log(1, '[GHOST] MANUAL KILL SWITCH ACTIVATED - Engine Halted', 'ERROR'))[1]).toEqual({
      type: 'locked',
      locked: true,
    });
    expect(interpretLog(log(1, '[GHOST] MANUAL KILL SWITCH DEACTIVATED'))[1]).toEqual({ type: 'locked', locked: false });
  });
});

describe('interpretEvent', () => {
  it('reads the balance from a VAULT frame', () => {
    const a = interpretEvent({ type: 'VAULT', state: { total: 328.13, principal: 300, currentProfit: 0 } });
    expect(a).toEqual([{ type: 'balance', balance: 328.13, principal: 300 }]);
  });

  it('reads processing from a STATE frame', () => {
    expect(interpretEvent({ type: 'STATE', state: { isProcessing: false, activeAgentId: null } })).toEqual([
      { type: 'processing', processing: false },
    ]);
  });

  it('logs an ERROR frame and faults on high severity', () => {
    const a = interpretEvent({
      type: 'ERROR',
      error: { agentId: 4, code: 'EXECUTION_FAILED', message: 'gateway 502', severity: 'HIGH' },
    });
    expect(types(a)).toEqual(['log', 'fault']);
  });
});

describe('orderFromLedger', () => {
  it('shapes a settled ledger row', () => {
    const o = orderFromLedger({
      id: 7,
      decided_at: '2026-09-18T02:55:00+00:00',
      ticker: 'T',
      side: 'no',
      price_cents: 23,
      count: 8,
      pnl_cents: -184,
      settled_yes: 1,
    });
    expect(o).toMatchObject({ id: 'ledger-7', side: 'NO', px: 23, qty: 8, status: 'filled', pnl: -1.84 });
  });

  it('keeps an unsettled row open with no P&L', () => {
    const o = orderFromLedger({
      id: 8,
      decided_at: '2026-09-18T02:55:00+00:00',
      ticker: 'T',
      side: 'yes',
      price_cents: 60,
      count: 3,
      pnl_cents: null,
      settled_yes: null,
    });
    expect(o).toMatchObject({ status: 'open', pnl: null });
  });
});
