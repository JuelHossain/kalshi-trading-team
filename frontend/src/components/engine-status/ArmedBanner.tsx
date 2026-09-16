import React from 'react';
import type { EngineStatus } from '../../hooks/useEngineStatus';

/**
 * The one fact the dashboard exists to make unmissable: can this place a real
 * order right now, and against which venue?
 *
 * Both values come from the engine. The previous indicator derived "Live
 * Trading" from an auth-session flag, which is not what decides whether money
 * moves, so it could read reassuringly while the engine was armed.
 *
 * Unknown is styled as a warning rather than as safe. If the engine cannot be
 * reached, the honest answer is that we do not know, and the reassuring guess
 * is the dangerous one.
 */
const ArmedBanner: React.FC<{ status: EngineStatus | null; error?: string | null }> = ({
  status,
  error,
}) => {
  if (!status) {
    return (
      <div
        data-testid="armed-banner"
        data-state="unknown"
        className="flex items-center gap-3 rounded-2xl border border-amber-500/30 bg-amber-500/5 px-5 py-4"
      >
        <span className="h-2.5 w-2.5 rounded-full bg-amber-400" />
        <div>
          <p className="font-mono text-xs font-bold uppercase tracking-widest text-amber-300">
            Engine unreachable
          </p>
          <p className="mt-0.5 text-xs text-amber-200/60">
            {error ?? 'No answer from /api/status'} — assume nothing about trading state.
          </p>
        </div>
      </div>
    );
  }

  const armed = status.orders_are_real;
  const live = armed && status.venue.is_production;

  // Real money is the only state that gets the alarming treatment. Armed
  // against demo is worth noticing but cannot cost anything.
  const tone = live
    ? {
        box: 'border-red-500/40 bg-red-500/10 animate-pulse',
        dot: 'bg-red-400',
        label: 'text-red-300',
        sub: 'text-red-200/70',
      }
    : armed
      ? {
          box: 'border-amber-500/30 bg-amber-500/5',
          dot: 'bg-amber-400',
          label: 'text-amber-300',
          sub: 'text-amber-200/60',
        }
      : {
          box: 'border-emerald-500/25 bg-emerald-500/5',
          dot: 'bg-emerald-400',
          label: 'text-emerald-300',
          sub: 'text-emerald-200/60',
        };

  const headline = live
    ? 'Live — real money'
    : armed
      ? 'Armed — demo money'
      : 'Paper — orders are simulated';

  return (
    <div
      data-testid="armed-banner"
      data-state={live ? 'live' : armed ? 'armed-demo' : 'paper'}
      className={`flex items-center gap-3 rounded-2xl border px-5 py-4 ${tone.box}`}
    >
      <span className={`h-2.5 w-2.5 rounded-full ${tone.dot}`} />
      <div className="min-w-0">
        <p
          data-testid="armed-headline"
          className={`font-mono text-xs font-bold uppercase tracking-widest ${tone.label}`}
        >
          {headline}
        </p>
        <p data-testid="armed-detail" className={`mt-0.5 truncate text-xs ${tone.sub}`}>
          {status.venue.base_url ?? 'no venue'}
          {status.paper_pinned_by_env && ' · pinned to paper by IS_PAPER_TRADING'}
        </p>
      </div>
    </div>
  );
};

export default ArmedBanner;
