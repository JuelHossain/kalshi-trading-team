/**
 * The cockpit's single store. Holds the beat machine that drives the orrery,
 * everything the engine has told us this session, and the UI chrome state.
 *
 * The beat machine's shape is the prototype's (work → throw → flare → signal)
 * but it is driven by real engine events, not a simulated tick. Transit beats
 * are visual and advance on their own timers; work beats last until the
 * engine says the agent finished.
 */
import { create } from 'zustand';
import { FLARE_MS, N, RETRY_MS, SIGNAL_MS, STATIONS, STORE_CAP, THROW_MS } from './stations';
import type { PaletteKey } from './palette';

export type Beat = 'work' | 'throw' | 'flare' | 'signal' | 'retry' | 'idle' | 'locked';
export type Mode = 'live' | 'idle' | 'choke' | 'fault' | 'locked';
export type LogLevel = 'ok' | 'info' | 'warn' | 'err';

export interface LogRow {
  id: string;
  t: string;
  agent: string;
  level: LogLevel;
  msg: string;
}

export interface Order {
  id: string;
  ts: number;
  t: string;
  ticker: string;
  side: 'YES' | 'NO';
  qty: number;
  px: number;
  status: 'filled' | 'rejected' | 'open';
  /** Dollars; null while the market is unsettled. */
  pnl: number | null;
}

export interface Run {
  id: string;
  kind: 'agent' | 'core';
  agent?: number;
  hop?: number;
  cycle: number;
  ok: boolean;
  ms: number;
  ts: number;
  summary: string;
  detail: [string, string][];
}

export interface StoreItem {
  ticker: string;
  title: string;
  state: 'next out' | 'stored' | 'waiting' | 'blocked' | 'executing';
}

export interface SoulArtifact {
  checks: { label: string; value: string; ok: boolean }[];
  sealed: boolean;
}
export interface SensesArtifact {
  swept: number;
  selected: number;
  markets: { ticker: string; volume: number; yes: string }[];
}
export interface BrainArtifact {
  ticker: string;
  prob: number | null;
  conf: number | null;
  ev: number | null;
  verdict: 'approved' | 'vetoed' | 'skipped' | null;
  side: string;
  price: number | null;
  reason: string;
  analysed: number;
  approved: number;
}
export interface HandArtifact {
  ticker: string;
  side: string;
  price: number | null;
  stake: number | null;
  count: number | null;
  steps: { label: string; meta: string; ok: boolean; bad: boolean }[];
  fault: string | null;
}

export interface CardRef {
  kind: 'agent' | 'core';
  i?: number;
}

export interface CockpitState {
  view: 'pipeline' | 'config';
  palette: PaletteKey;
  connected: boolean;
  kill: boolean;
  autopilot: boolean;
  processing: boolean;
  paused: boolean;

  beat: Beat;
  bi: number;
  t0: number;
  now: number;
  expected: number;
  retries: number;
  workStart: number | null;
  brainDone: boolean;
  lastActivity: number;
  faultUntil: number;

  cycle: number;
  balance: number;
  principal: number;
  spark: number[];
  storeDepth: number;
  storeKind: number;
  storeItems: StoreItem[];
  execAtLimit: boolean;

  logs: LogRow[];
  orders: Order[];
  runs: Run[];

  soul: SoulArtifact;
  senses: SensesArtifact;
  brain: BrainArtifact;
  hand: HandArtifact;

  card: CardRef | null;
  cardTab: 'now' | 'history';
  openRun: string | null;
  cardX: number | null;
  cardY: number | null;
  collapsed: boolean;
  dragging: boolean;
  range: 'all' | 'today' | 'week' | 'month';
  outcome: 'all' | 'won' | 'lost';
  filtersOpen: boolean;

  setView: (view: 'pipeline' | 'config') => void;
  setPalette: (palette: PaletteKey) => void;
  setEngine: (patch: Partial<Pick<CockpitState, 'connected' | 'kill' | 'autopilot' | 'processing' | 'cycle'>>) => void;
  setBalance: (balance: number, principal?: number) => void;
  setQueues: (depth: number, items: StoreItem[], execAtLimit: boolean) => void;
  setOrders: (orders: Order[]) => void;
  addOrder: (order: Order) => void;
  pushLog: (row: Omit<LogRow, 'id' | 't'> & { t?: string }) => void;
  beginWork: (i: number, expected?: number) => void;
  completeWork: (i: number, ok: boolean, summary: string, detail?: [string, string][], advance?: boolean) => void;
  setIdle: () => void;
  setLocked: (locked: boolean) => void;
  setRetry: () => void;
  markFault: (ms?: number) => void;
  tick: (now: number) => void;
  startCycle: (n: number) => void;
  finishCycle: (n: number) => void;
  patchSoul: (patch: Partial<SoulArtifact>) => void;
  patchSenses: (patch: Partial<SensesArtifact>) => void;
  patchBrain: (patch: Partial<BrainArtifact>) => void;
  patchHand: (patch: Partial<HandArtifact>) => void;
  setBrainDone: (done: boolean) => void;

  openCard: (card: CardRef) => void;
  closeCard: () => void;
  setCardTab: (tab: 'now' | 'history') => void;
  toggleRun: (id: string) => void;
  setCardPos: (x: number, y: number) => void;
  setDragging: (dragging: boolean) => void;
  toggleCollapse: () => void;
  setRange: (range: CockpitState['range']) => void;
  setOutcome: (outcome: CockpitState['outcome']) => void;
  toggleFilters: () => void;
  togglePause: () => void;
  reset: () => void;
}

const PALETTE_KEY = 'sentient_alpha_palette';

// Node 22+ exposes an experimental `localStorage` global that throws unless
// a storage file is configured, so feature-detect the methods, not the name.
const safeStorage = (): Storage | null => {
  try {
    const ls = globalThis.localStorage;
    return ls && typeof ls.getItem === 'function' && typeof ls.setItem === 'function' ? ls : null;
  } catch {
    return null;
  }
};

const storedPalette = (): PaletteKey => {
  try {
    const v = safeStorage()?.getItem(PALETTE_KEY);
    return v === 'night' ? 'night' : 'cream';
  } catch {
    return 'cream';
  }
};

export const clock = (ts = Date.now()) =>
  new Date(ts).toLocaleTimeString('en-US', { hour12: false });

let seq = 0;
const uid = (prefix: string) => `${prefix}${Date.now().toString(36)}${(seq++).toString(36)}`;

export const emptySoul = (): SoulArtifact => ({
  checks: [
    { label: 'API pre-flight', value: 'pending', ok: false },
    { label: 'Hard floor', value: 'pending', ok: false },
    { label: 'Health check', value: 'pending', ok: false },
  ],
  sealed: false,
});
export const emptySenses = (): SensesArtifact => ({ swept: 0, selected: 0, markets: [] });
export const emptyBrain = (): BrainArtifact => ({
  ticker: '',
  prob: null,
  conf: null,
  ev: null,
  verdict: null,
  side: '',
  price: null,
  reason: '',
  analysed: 0,
  approved: 0,
});
export const emptyHand = (): HandArtifact => ({
  ticker: '',
  side: '',
  price: null,
  stake: null,
  count: null,
  steps: [
    { label: 'Snipe check · orderbook depth', meta: '—', ok: false, bad: false },
    { label: 'Kelly sizing', meta: '—', ok: false, bad: false },
    { label: 'Filled · paper receipt', meta: '—', ok: false, bad: false },
  ],
  fault: null,
});

const initial = (): Omit<CockpitState, keyof Actions> => ({
  view: 'pipeline',
  palette: storedPalette(),
  connected: false,
  kill: false,
  autopilot: false,
  processing: false,
  paused: false,

  beat: 'idle',
  bi: 0,
  t0: Date.now(),
  now: Date.now(),
  expected: STATIONS[0].dur,
  retries: 0,
  workStart: null,
  brainDone: true,
  lastActivity: 0,
  faultUntil: 0,

  cycle: 0,
  balance: 0,
  principal: 300,
  spark: [],
  storeDepth: 0,
  storeKind: -1,
  storeItems: [],
  execAtLimit: false,

  logs: [],
  orders: [],
  runs: [],

  soul: emptySoul(),
  senses: emptySenses(),
  brain: emptyBrain(),
  hand: emptyHand(),

  card: null,
  cardTab: 'now',
  openRun: null,
  cardX: null,
  cardY: null,
  collapsed: false,
  dragging: false,
  range: 'all',
  outcome: 'all',
  filtersOpen: false,
});

type Actions = Pick<
  CockpitState,
  | 'setView'
  | 'setPalette'
  | 'setEngine'
  | 'setBalance'
  | 'setQueues'
  | 'setOrders'
  | 'addOrder'
  | 'pushLog'
  | 'beginWork'
  | 'completeWork'
  | 'setIdle'
  | 'setLocked'
  | 'setRetry'
  | 'markFault'
  | 'tick'
  | 'startCycle'
  | 'finishCycle'
  | 'patchSoul'
  | 'patchSenses'
  | 'patchBrain'
  | 'patchHand'
  | 'setBrainDone'
  | 'openCard'
  | 'closeCard'
  | 'setCardTab'
  | 'toggleRun'
  | 'setCardPos'
  | 'setDragging'
  | 'toggleCollapse'
  | 'setRange'
  | 'setOutcome'
  | 'toggleFilters'
  | 'togglePause'
  | 'reset'
>;

export const useCockpit = create<CockpitState>()((set, get) => ({
  ...initial(),

  setView: (view) => set({ view }),
  setPalette: (palette) => {
    try {
      safeStorage()?.setItem(PALETTE_KEY, palette);
    } catch {
      /* palette preference is a nicety */
    }
    set({ palette });
  },
  setEngine: (patch) => set(patch),
  setBalance: (balance, principal) =>
    set((s) => ({
      balance,
      principal: principal ?? s.principal,
      spark:
        s.spark.length && Math.abs(s.spark[s.spark.length - 1] - balance) < 0.005
          ? s.spark
          : [...s.spark, balance].slice(-52),
    })),
  setQueues: (depth, items, execAtLimit) =>
    set((s) => {
      const idle = s.beat === 'idle' || s.beat === 'locked';
      return {
        storeDepth: Math.min(STORE_CAP, depth),
        storeItems: items,
        execAtLimit,
        // A depth reading while idle means the queues still hold work from a
        // previous session; show it without pretending an agent is active.
        storeKind: depth === 0 ? -1 : idle && s.storeKind < 0 ? 1 : s.storeKind,
      };
    }),
  setOrders: (orders) => set({ orders: orders.slice(-200) }),
  addOrder: (order) => set((s) => ({ orders: [...s.orders, order].slice(-200) })),
  pushLog: (row) =>
    set((s) => {
      if (s.paused) return {};
      const entry: LogRow = { id: uid('l'), t: row.t ?? clock(), agent: row.agent, level: row.level, msg: row.msg };
      return { logs: [...s.logs, entry].slice(-60) };
    }),

  beginWork: (i, expected) => {
    const s = get();
    const now = Date.now();
    // A provisional work beat (set by the transit timer) is confirmed, not
    // restarted, when the real event arrives a moment later.
    if (s.beat === 'work' && s.bi === i && now - s.t0 < 2500) {
      set({ expected: expected ?? s.expected, lastActivity: now });
      return;
    }
    // The engine hands off instantly, but the throw takes ~3.4 s on screen.
    // If the star is mid-flight towards this very agent, let the flight land
    // (tick() then starts the work beat) rather than cutting it short.
    const inTransit = s.beat === 'throw' || s.beat === 'flare' || s.beat === 'signal';
    if (inTransit && (s.bi + 1) % N === i && now - s.t0 < THROW_MS + FLARE_MS + SIGNAL_MS) {
      set({ lastActivity: now, brainDone: i === 2 ? false : s.brainDone });
      return;
    }
    set({
      beat: 'work',
      bi: i,
      t0: now,
      now,
      expected: expected ?? STATIONS[i].dur,
      workStart: now,
      lastActivity: now,
      brainDone: i === 2 ? false : s.brainDone,
    });
  },

  completeWork: (i, ok, summary, detail = [], advance = true) => {
    const s = get();
    const now = Date.now();
    const ms = s.workStart && s.bi === i ? now - s.workStart : Math.round(STATIONS[i].dur * 0.6);
    const run: Run = {
      id: uid('r'),
      kind: 'agent',
      agent: i,
      cycle: s.cycle,
      ok,
      ms,
      ts: now,
      summary,
      detail,
    };
    // Only a hand-off throws at the star. A veto, a stand-down or a refusal
    // ends the run where it is: the Brain stays on station because more
    // markets usually follow; a Hand refusal is the end of that signal, so
    // the star goes dark until the engine speaks again.
    const parked = !advance && i === N - 1;
    set({
      beat: advance ? 'throw' : parked ? 'idle' : 'work',
      bi: i,
      t0: now,
      now,
      expected: advance ? THROW_MS : STATIONS[i].dur,
      workStart: advance ? null : now,
      lastActivity: now,
      runs: [...s.runs, run].slice(-120),
    });
  },

  setIdle: () => set({ beat: 'idle', t0: Date.now(), now: Date.now(), workStart: null }),
  setLocked: (locked) =>
    set((s) => ({
      kill: locked,
      beat: locked ? 'locked' : s.beat === 'locked' ? 'idle' : s.beat,
      t0: Date.now(),
      now: Date.now(),
    })),
  setRetry: () =>
    set((s) => ({
      beat: 'retry',
      bi: N - 1,
      t0: Date.now(),
      now: Date.now(),
      expected: RETRY_MS,
      retries: s.retries + 1,
      lastActivity: Date.now(),
    })),
  markFault: (ms = 30000) => set({ faultUntil: Date.now() + ms }),

  tick: (now) => {
    const s = get();
    const el = now - s.t0;
    if (s.beat === 'throw' && el >= THROW_MS) {
      const st = STATIONS[s.bi];
      const hop: Run = {
        id: uid('h'),
        kind: 'core',
        hop: s.bi,
        cycle: s.cycle,
        ok: true,
        ms: THROW_MS + FLARE_MS + SIGNAL_MS,
        ts: now,
        summary: `Caught the ${st.payload} · woke the ${STATIONS[(s.bi + 1) % N].name}`,
        detail: [
          ['Caught', `${st.payload} · ${Math.max(1, st.depth)} item${st.depth > 1 ? 's' : ''}`],
          ['Held', `${(FLARE_MS / 1000).toFixed(2)}s`],
          ['Woke', STATIONS[(s.bi + 1) % N].name],
        ],
      };
      set({
        beat: 'flare',
        t0: now,
        now,
        expected: FLARE_MS,
        storeKind: s.bi,
        storeDepth: Math.max(s.storeDepth, Math.min(STORE_CAP, st.depth)),
        runs: [...s.runs, hop].slice(-120),
      });
      return;
    }
    if (s.beat === 'flare' && el >= FLARE_MS) {
      set({ beat: 'signal', t0: now, now, expected: SIGNAL_MS });
      return;
    }
    if (s.beat === 'signal' && el >= SIGNAL_MS) {
      const ni = (s.bi + 1) % N;
      if (ni === 0) {
        // The Hand's receipt closes the loop; wait for the engine to open
        // the next cycle rather than inventing one.
        set({ beat: 'idle', t0: now, now, workStart: null });
        return;
      }
      set({ beat: 'work', bi: ni, t0: now, now, expected: STATIONS[ni].dur, workStart: now });
      return;
    }
    if (s.beat === 'retry' && el >= RETRY_MS) {
      set({ t0: now, now, retries: s.retries + 1 });
      return;
    }
    set({ now });
  },

  startCycle: (n) =>
    set({
      cycle: n,
      soul: emptySoul(),
      senses: emptySenses(),
      brain: emptyBrain(),
      hand: emptyHand(),
      retries: 0,
      processing: true,
      lastActivity: Date.now(),
    }),
  finishCycle: (n) =>
    set((s) => ({
      cycle: Math.max(s.cycle, n),
      processing: false,
      spark: s.balance ? [...s.spark, s.balance].slice(-52) : s.spark,
    })),

  patchSoul: (patch) => set((s) => ({ soul: { ...s.soul, ...patch } })),
  patchSenses: (patch) => set((s) => ({ senses: { ...s.senses, ...patch } })),
  patchBrain: (patch) => set((s) => ({ brain: { ...s.brain, ...patch } })),
  patchHand: (patch) => set((s) => ({ hand: { ...s.hand, ...patch } })),
  setBrainDone: (brainDone) =>
    set((s) => {
      // The batch drained with the Brain still on station: nothing was
      // thrown, so the star goes dark. A verdict in flight is left to land.
      const parked = brainDone && s.beat === 'work' && s.bi === 2;
      return parked ? { brainDone, beat: 'idle', t0: Date.now(), now: Date.now(), workStart: null } : { brainDone };
    }),

  openCard: (card) => set({ card, cardTab: 'now', openRun: null, collapsed: false }),
  closeCard: () => set({ card: null }),
  setCardTab: (cardTab) => set({ cardTab }),
  toggleRun: (id) => set((s) => ({ openRun: s.openRun === id ? null : id })),
  setCardPos: (cardX, cardY) => set({ cardX, cardY }),
  setDragging: (dragging) => set({ dragging }),
  toggleCollapse: () => set((s) => ({ collapsed: !s.collapsed })),
  setRange: (range) => set({ range }),
  setOutcome: (outcome) => set({ outcome }),
  toggleFilters: () => set((s) => ({ filtersOpen: !s.filtersOpen })),
  togglePause: () => set((s) => ({ paused: !s.paused })),
  reset: () => set({ ...initial(), palette: get().palette }),
}));

/** What the top bar and the star report. Derived, never stored. */
export function deriveMode(s: Pick<CockpitState, 'kill' | 'faultUntil' | 'execAtLimit' | 'beat' | 'now'>): Mode {
  if (s.kill) return 'locked';
  if (s.faultUntil > s.now) return 'fault';
  if (s.execAtLimit) return 'choke';
  if (s.beat === 'idle' || s.beat === 'locked') return 'idle';
  return 'live';
}
