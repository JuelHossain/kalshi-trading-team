/**
 * The derived, per-render view of the beat machine that several components
 * share: which planet is in which state, how far the current beat is, and
 * what the star is doing. Computed once per render from the store.
 */
import { PALETTES, type Palette } from './palette';
import { deriveMode, useCockpit, type Beat, type Mode } from './store';
import { FLARE_MS, N, RETRY_MS, SIGNAL_MS, STORE_CAP, THROW_MS } from './stations';

export type PlanetState =
  | 'active'
  | 'throwing'
  | 'waking'
  | 'done'
  | 'queued'
  | 'held'
  | 'fault'
  | 'idle'
  | 'locked';

export interface CockpitView {
  pal: Palette;
  mode: Mode;
  beat: Beat;
  bi: number;
  dur: number;
  el: number;
  bp: number;
  working: boolean;
  transiting: boolean;
  states: PlanetState[];
  storeN: number;
  storeKind: number;
  coreHot: boolean;
  coreAlarm: boolean;
  retries: number;
  cycle: number;
}

export const doneish = (c: PlanetState) => c === 'done' || c === 'held' || c === 'fault' || c === 'throwing';

export function useCockpitView(): CockpitView {
  const s = useCockpit();
  const pal = PALETTES[s.palette];
  const mode = deriveMode(s);
  const beat: Beat = mode === 'locked' ? 'locked' : mode === 'idle' ? 'idle' : s.beat;
  const bi = s.bi;
  const dur =
    beat === 'work'
      ? s.expected
      : beat === 'throw'
        ? THROW_MS
        : beat === 'flare'
          ? FLARE_MS
          : beat === 'signal'
            ? SIGNAL_MS
            : beat === 'retry'
              ? RETRY_MS
              : s.expected;
  const elRaw = Math.max(0, s.now - s.t0);
  const el = Math.min(dur, elRaw);
  // A real work beat may outlast its budget; hold the arc just short of full
  // rather than pretending the agent finished.
  const bp = beat === 'work' ? Math.min(0.96, dur ? elRaw / dur : 0) : dur ? el / dur : 0;
  const working = beat === 'work';
  const transiting = beat === 'throw' || beat === 'flare' || beat === 'signal' || beat === 'retry';

  const stateOf = (i: number): PlanetState => {
    if (mode === 'locked') return 'locked';
    if (mode === 'idle') return 'idle';
    if (mode === 'fault') return i === N - 1 ? 'fault' : 'held';
    if (mode === 'choke') return i === N - 1 ? 'active' : i === N - 2 ? 'done' : 'held';
    if (working && i === bi) return 'active';
    if (beat === 'throw' && i === bi) return 'throwing';
    if (beat === 'signal' && i === (bi + 1) % N) return 'waking';
    return i <= bi ? 'done' : 'queued';
  };
  const states = Array.from({ length: N }, (_, i) => stateOf(i));

  const storeN = mode === 'idle' || mode === 'locked' ? Math.min(STORE_CAP, s.storeDepth) : s.storeDepth;
  const coreHot = beat === 'throw' || beat === 'flare' || beat === 'signal';
  const coreAlarm = mode === 'fault' || mode === 'choke' || storeN >= STORE_CAP;

  return {
    pal,
    mode,
    beat,
    bi,
    dur,
    el,
    bp,
    working,
    transiting,
    states,
    storeN,
    storeKind: s.storeKind,
    coreHot,
    coreAlarm,
    retries: s.retries,
    cycle: s.cycle,
  };
}
