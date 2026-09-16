import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ArmedBanner from './ArmedBanner';
import type { EngineStatus } from '../../hooks/useEngineStatus';

const status = (over: Partial<EngineStatus> = {}): EngineStatus => ({
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
  engine: { running: true, processing: false, cycle: 3, agents: [], last_cycle: null },
  ...over,
});

describe('ArmedBanner', () => {
  it('reads paper when the engine is not armed', () => {
    render(<ArmedBanner status={status({ orders_are_real: false })} />);

    expect(screen.getByTestId('armed-banner')).toHaveAttribute('data-state', 'paper');
    expect(screen.getByTestId('armed-headline')).toHaveTextContent('simulated');
  });

  it('distinguishes armed-against-demo from real money', () => {
    render(
      <ArmedBanner
        status={status({
          orders_are_real: true,
          venue: { ...status().venue, env: 'demo', is_production: false },
        })}
      />
    );

    expect(screen.getByTestId('armed-banner')).toHaveAttribute('data-state', 'armed-demo');
    expect(screen.getByTestId('armed-headline')).toHaveTextContent('demo money');
  });

  it('shouts when real money is at stake', () => {
    render(
      <ArmedBanner
        status={status({
          orders_are_real: true,
          venue: {
            ...status().venue,
            env: 'prod',
            is_production: true,
            base_url: 'https://api.kalshi.co/trade-api/v2',
          },
        })}
      />
    );

    const banner = screen.getByTestId('armed-banner');
    expect(banner).toHaveAttribute('data-state', 'live');
    expect(banner.className).toContain('red');
    expect(screen.getByTestId('armed-headline')).toHaveTextContent('real money');
  });

  it('does not call it live merely because the venue is production', () => {
    // Pointing at production while disarmed still cannot place an order. Crying
    // wolf here would teach someone to ignore the one banner that matters.
    render(
      <ArmedBanner
        status={status({
          orders_are_real: false,
          venue: { ...status().venue, env: 'prod', is_production: true },
        })}
      />
    );

    expect(screen.getByTestId('armed-banner')).toHaveAttribute('data-state', 'paper');
  });

  it('says it does not know rather than guessing safe', () => {
    // The reassuring guess is the dangerous one: a dashboard that shows "paper"
    // because it could not reach the engine is worse than one that admits it.
    render(<ArmedBanner status={null} error="connection refused" />);

    const banner = screen.getByTestId('armed-banner');
    expect(banner).toHaveAttribute('data-state', 'unknown');
    expect(banner.className).not.toContain('emerald');
    expect(screen.getByText(/connection refused/)).toBeInTheDocument();
  });

  it('surfaces the server-side paper pin', () => {
    render(<ArmedBanner status={status({ paper_pinned_by_env: true })} />);

    expect(screen.getByTestId('armed-detail')).toHaveTextContent('IS_PAPER_TRADING');
  });

  it('shows which venue it would trade against', () => {
    render(<ArmedBanner status={status()} />);

    expect(screen.getByTestId('armed-detail')).toHaveTextContent('demo-api.kalshi.co');
  });
});
