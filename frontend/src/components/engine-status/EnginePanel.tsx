import React from 'react';
import ArmedBanner from './ArmedBanner';
import { useEngineStatus, type EngineStatus } from '../../hooks/useEngineStatus';

const dollars = (cents: number) =>
  `$${(cents / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

/** A label/value row. Values are tabular so columns of digits line up. */
const Row: React.FC<{ label: string; value: React.ReactNode; tone?: string }> = ({
  label,
  value,
  tone = 'text-white/80',
}) => (
  <div className="flex items-baseline justify-between gap-4 py-1.5">
    <span className="text-[11px] uppercase tracking-wider text-white/40">{label}</span>
    <span className={`font-mono text-xs tabular-nums ${tone}`}>{value}</span>
  </div>
);

/** What is stopping the engine, if anything. Each is a reason it will not trade. */
const Blockers: React.FC<{ status: EngineStatus }> = ({ status }) => {
  const blockers = [
    status.halted.kill_switch && 'Kill switch active',
    status.halted.manual_kill_switch && 'Manual kill switch',
    status.halted.below_hard_floor && 'Below hard floor',
    !status.venue.credentials_present &&
      `Missing ${status.venue.credential_vars.join(' and ')}`,
  ].filter(Boolean) as string[];

  if (blockers.length === 0) {
    return (
      <p data-testid="blockers-none" className="text-xs text-emerald-300/70">
        Nothing is blocking a cycle.
      </p>
    );
  }

  return (
    <ul data-testid="blockers" className="flex flex-col gap-1.5">
      {blockers.map((b) => (
        <li key={b} className="flex items-start gap-2 text-xs text-red-300/90">
          <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-red-400" />
          {b}
        </li>
      ))}
    </ul>
  );
};

/**
 * The engine's own account of itself: whether it can trade, what would stop it,
 * how much room it has above the floor, and what it is doing right now.
 *
 * Every value is read from the object that governs the behaviour it describes,
 * so this panel cannot disagree with the engine the way the old health check
 * did -- that one reported Kalshi "Authenticated" on the strength of a string
 * existing in the browser's own config, having never contacted Kalshi.
 */
const EnginePanel: React.FC = () => {
  const { status, error } = useEngineStatus();

  return (
    <div data-testid="engine-panel" className="flex flex-col gap-4">
      <ArmedBanner status={status} error={error} />

      {status && (
        <>
          <section className="rounded-2xl border border-white/5 bg-white/[0.02] px-5 py-4">
            <h3 className="mb-2 font-mono text-[11px] font-bold uppercase tracking-widest text-white/50">
              Vault
            </h3>
            <Row label="Balance" value={dollars(status.vault.balance_cents)} />
            <Row label="Hard floor" value={dollars(status.vault.hard_floor_cents)} />
            <Row
              label="Headroom"
              value={dollars(status.vault.headroom_cents)}
              tone={status.vault.headroom_cents <= 0 ? 'text-red-300' : 'text-emerald-300'}
            />
            <Row
              label="Principal"
              value={status.vault.principal_locked ? 'Locked' : 'At risk'}
              tone={status.vault.principal_locked ? 'text-emerald-300' : 'text-white/60'}
            />
          </section>

          <section className="rounded-2xl border border-white/5 bg-white/[0.02] px-5 py-4">
            <h3 className="mb-2 font-mono text-[11px] font-bold uppercase tracking-widest text-white/50">
              Blocking a cycle
            </h3>
            <Blockers status={status} />
          </section>

          <section className="rounded-2xl border border-white/5 bg-white/[0.02] px-5 py-4">
            <h3 className="mb-2 font-mono text-[11px] font-bold uppercase tracking-widest text-white/50">
              Right now
            </h3>
            <Row label="Cycle" value={`#${status.engine.cycle}`} />
            <Row
              label="State"
              value={status.engine.processing ? 'Processing' : 'Idle'}
              tone={status.engine.processing ? 'text-emerald-300' : 'text-white/60'}
            />
            <Row
              label="Agents"
              value={status.engine.agents.length ? status.engine.agents.join(' · ') : 'none'}
            />
            <Row
              label="Last cycle"
              value={
                status.engine.last_cycle
                  ? new Date(status.engine.last_cycle).toLocaleTimeString()
                  : 'never'
              }
            />
          </section>
        </>
      )}
    </div>
  );
};

export default EnginePanel;
