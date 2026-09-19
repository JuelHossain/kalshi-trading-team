/**
 * Persistent history for the inspector, straight from the engine's stores:
 * the Brain's decisions from the ledger, the Hand's fills, and every other
 * agent's journal lines. Survives restarts, unlike the session's measured
 * runs, which sit above it in the card.
 */
import { useEffect, useState } from 'react';
import { ENGINE_URL } from './useEngineFeed';

export interface HistoryRow {
  id: string;
  ts: number;
  title: string;
  detail: string;
  ok: boolean | null;
  cycle?: number | null;
}

interface Decision {
  id: number;
  decided_at: string;
  ticker: string;
  market_price: number;
  estimated_probability: number | null;
  confidence: number | null;
  edge: number | null;
  outcome: string;
  veto_reason: string | null;
  stake_cents: number | null;
  order_id: string | null;
  settled_yes: number | null;
}

interface JournalEvent {
  id: number;
  ts: string;
  topic: string;
  agent: string | null;
  level: string;
  cycle: number | null;
  message: string;
}

const AGENT_NAMES = ['SOUL', 'SENSES', 'BRAIN', 'HAND'];

export function useEngineHistory(kind: 'agent' | 'core', agent: number, refreshKey: number): { rows: HistoryRow[]; loading: boolean; source: string } {
  const [rows, setRows] = useState<HistoryRow[]>([]);
  const [loading, setLoading] = useState(false);

  const source = kind === 'core' ? 'journal' : agent === 2 ? 'ledger' : 'journal';

  useEffect(() => {
    let alive = true;
    setLoading(true);
    const load = async () => {
      try {
        if (kind === 'agent' && agent === 2) {
          const res = await fetch(`${ENGINE_URL}/decisions?limit=60`);
          const data = await res.json();
          if (!alive) return;
          const out: HistoryRow[] = (data.decisions as Decision[]).map((d) => {
            const est = d.estimated_probability !== null && d.estimated_probability !== undefined ? `p ${(d.estimated_probability * 100).toFixed(0)}%` : 'no estimate';
            const edge = d.edge !== null && d.edge !== undefined ? ` · edge ${d.edge >= 0 ? '+' : ''}${d.edge.toFixed(3)}` : '';
            const conf = d.confidence !== null && d.confidence !== undefined ? ` · conf ${Math.round(d.confidence * 100)}%` : '';
            const reason = d.veto_reason ? ` · ${d.veto_reason}` : '';
            return {
              id: `d${d.id}`,
              ts: Date.parse(d.decided_at) || 0,
              title: `${d.outcome.toLowerCase()} · ${d.ticker}`,
              detail: `price ${Math.round(d.market_price * 100)}¢ · ${est}${edge}${conf}${reason}`,
              ok: d.outcome === 'APPROVED' ? true : d.outcome === 'VETOED' ? null : false,
            };
          });
          setRows(out);
        } else {
          const params = new URLSearchParams({ limit: '60' });
          if (kind === 'agent') params.set('agent', AGENT_NAMES[agent]);
          else params.set('topic', 'EXECUTION_READY');
          const res = await fetch(`${ENGINE_URL}/journal?${params.toString()}`);
          const data = await res.json();
          if (!alive) return;
          const events = (data.events as JournalEvent[]).filter((e) => e.level !== 'DEBUG');
          setRows(
            events.map((e) => ({
              id: `j${e.id}`,
              ts: Date.parse(e.ts) || 0,
              title: e.message,
              detail: `${e.topic.toLowerCase().replace(/_/g, ' ')}${e.cycle ? ` · cycle ${e.cycle}` : ''}`,
              ok: e.level === 'ERROR' || e.level === 'WARN' ? false : null,
              cycle: e.cycle,
            }))
          );
        }
      } catch {
        if (alive) setRows([]);
      } finally {
        if (alive) setLoading(false);
      }
    };
    void load();
    return () => {
      alive = false;
    };
  }, [kind, agent, refreshKey]);

  return { rows, loading, source };
}
