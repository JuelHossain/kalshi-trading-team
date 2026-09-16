import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import EnginePanel from './EnginePanel';

const payload = (over: any = {}) => ({
  orders_are_real: false,
  venue: {
    env: 'demo',
    base_url: 'https://demo-api.kalshi.co/trade-api/v2',
    is_production: false,
    credentials_present: true,
    credential_vars: ['KALSHI_DEMO_KEY_ID', 'KALSHI_DEMO_PRIVATE_KEY'],
  },
  paper_pinned_by_env: false,
  halted: { kill_switch: false, manual_kill_switch: false, below_hard_floor: false },
  vault: {
    balance_cents: 30000,
    hard_floor_cents: 25500,
    headroom_cents: 4500,
    principal_locked: false,
  },
  engine: { running: true, processing: true, cycle: 12, agents: ['SOUL', 'HAND'], last_cycle: null },
  ...over,
});

const serve = (body: any, ok = true) =>
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({ ok, status: ok ? 200 : 500, json: async () => body })
  );

beforeEach(() => vi.clearAllMocks());
afterEach(() => vi.unstubAllGlobals());

describe('EnginePanel', () => {
  it('shows money in dollars, not cents', async () => {
    serve(payload());
    render(<EnginePanel />);

    await waitFor(() => expect(screen.getByText('$300.00')).toBeInTheDocument());
    expect(screen.getByText('$255.00')).toBeInTheDocument();
    expect(screen.getByText('$45.00')).toBeInTheDocument();
  });

  it('lists every reason a cycle cannot run', async () => {
    serve(
      payload({
        halted: { kill_switch: true, manual_kill_switch: false, below_hard_floor: true },
        venue: { ...payload().venue, credentials_present: false },
      })
    );
    render(<EnginePanel />);

    await waitFor(() => expect(screen.getByTestId('blockers')).toBeInTheDocument());
    expect(screen.getByText(/Kill switch active/)).toBeInTheDocument();
    expect(screen.getByText(/Below hard floor/)).toBeInTheDocument();
    expect(screen.getByText(/Missing KALSHI_DEMO_KEY_ID/)).toBeInTheDocument();
  });

  it('says so plainly when nothing is blocking', async () => {
    serve(payload());
    render(<EnginePanel />);

    await waitFor(() => expect(screen.getByTestId('blockers-none')).toBeInTheDocument());
  });

  it('treats missing credentials as a blocker, not a detail', async () => {
    // Without them the engine cannot place an order at all, so it belongs with
    // the kill switch rather than buried in a config list.
    serve(payload({ venue: { ...payload().venue, credentials_present: false } }));
    render(<EnginePanel />);

    await waitFor(() => expect(screen.getByTestId('blockers')).toBeInTheDocument());
  });

  it('reports unknown rather than a stale reading when the engine stops answering', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('connection refused')));
    render(<EnginePanel />);

    await waitFor(() =>
      expect(screen.getByTestId('armed-banner')).toHaveAttribute('data-state', 'unknown')
    );
    // The detail sections must be gone, not left showing the last good numbers.
    expect(screen.queryByText('$300.00')).not.toBeInTheDocument();
  });

  it('treats a non-200 as unreachable rather than parsing it as status', async () => {
    serve({ orders_are_real: false }, false);
    render(<EnginePanel />);

    await waitFor(() =>
      expect(screen.getByTestId('armed-banner')).toHaveAttribute('data-state', 'unknown')
    );
  });

  it('flags negative headroom in red', async () => {
    serve(payload({ vault: { ...payload().vault, headroom_cents: -1200 } }));
    render(<EnginePanel />);

    await waitFor(() => {
      const value = screen.getByText('$-12.00');
      expect(value.className).toContain('red');
    });
  });
});
