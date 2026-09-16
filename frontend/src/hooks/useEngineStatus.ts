import { useEffect, useState } from 'react';

/** What the engine will actually do, as reported by the engine itself. */
export interface EngineStatus {
  orders_are_real: boolean;
  venue: {
    env: 'demo' | 'prod';
    base_url: string | null;
    is_production: boolean;
    credentials_present: boolean;
    credential_vars: string[];
  };
  paper_pinned_by_env: boolean;
  halted: {
    kill_switch: boolean;
    manual_kill_switch: boolean;
    below_hard_floor: boolean;
  };
  vault: {
    balance_cents: number;
    hard_floor_cents: number;
    headroom_cents: number;
    principal_locked: boolean;
  };
  engine: {
    running: boolean;
    processing: boolean;
    cycle: number;
    agents: string[];
    last_cycle: string | null;
  };
}

/**
 * Poll /api/status.
 *
 * `status` is null until the engine answers, and goes back to null when it
 * stops answering. Nothing here invents a default: a dashboard that displays
 * "paper" because it could not reach the engine is worse than one that says it
 * does not know, since the reassuring answer is the dangerous one to guess.
 */
export function useEngineStatus(pollMs = 3000) {
  const [status, setStatus] = useState<EngineStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const read = async () => {
      try {
        const res = await fetch('/api/status');
        if (!res.ok) throw new Error(`engine returned ${res.status}`);
        const data = (await res.json()) as EngineStatus;
        if (!cancelled) {
          setStatus(data);
          setError(null);
        }
      } catch (e: any) {
        if (!cancelled) {
          setStatus(null);
          setError(e?.message ?? 'cannot reach the engine');
        }
      }
    };

    read();
    const timer = setInterval(read, pollMs);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [pollMs]);

  return { status, error };
}
