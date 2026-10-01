/**
 * Orrery geometry — the exact algorithm from the design prototype, ported to TypeScript.
 * Framework-agnostic and pure: give it a box size, get back every radius and diameter.
 *
 * WHY THIS FILE EXISTS
 * Four earlier attempts at this layout failed in ways that are not obvious, and each failure
 * is encoded as a rule below. Port this function as-is rather than re-deriving it.
 */

export const TILT = 0.5; // the orbital plane is squashed on Y via scaleY(0.5)

export interface Station {
  name: string;
  lane: number; // preferred lane index, 0 = innermost
}

export interface OrreryGeometry {
  planetD: number; // planet disc diameter, px
  coreD: number; // star disc diameter, px
  labelOff: number; // distance from planet centre to label centre, along the rail
  labelW: number; // fixed label box width — makes clearance deterministic
  capH: number; // label block height (name + status)
  cap: number; // type scale multiplier
  minR: number; // smallest legal orbit radius
  maxR: number; // largest orbit radius the box can hold
  laneR: number[]; // final lane radii, innermost first
  laneN: number;
}

/**
 * RULE 1 — minR must be tilt-aware.
 * The plane is scaled to 0.5 on Y, so a radius r only buys r * TILT of *vertical* gap.
 * A planet at the top of its lane must clear the star in that squashed axis, so the
 * required radius is (starRadius + planetRadius + gap) / TILT — roughly double the
 * naive figure. Getting this wrong makes top/bottom planets paint over the star.
 *
 * RULE 2 — never shrink the bodies first.
 * Reserving room for the label eats radius fast. Spend the label's generosity before
 * the planets': three passes of decreasing leader-gap and edge-padding, and only then
 * step the planet diameter down. Otherwise a tight box bottoms out at ~26px planets in
 * a 492x300 plate, which is what made earlier versions look cheap.
 *
 * RULE 3 — lanes must be genuinely separated or must not exist.
 * Distributing lanes across a span that can be zero collapses two rings onto one radius.
 * Place them outward from maxR at a guaranteed planetD * 1.25 separation and emit only
 * as many as actually fit; clamp a station's lane index to what exists.
 */
export function computeOrrery(
  boxW: number,
  boxH: number,
  stations: Station[]
): OrreryGeometry {
  const BW = Math.max(240, boxW);
  const BH = Math.max(170, boxH);

  // SS drives type and body scale. BH is weighted because the plane is wide and short.
  const SS = Math.min(BW, BH * 1.7);
  const cap = SS > 620 ? 1 : SS > 440 ? 0.9 : 0.8;
  const capH = Math.round(15 * cap * 1.1 + 9 * cap * 1.5 + 18);
  const labelW = Math.round(78 * cap);
  const wantLanes = stations.reduce((m, st) => Math.max(m, st.lane + 1), 1);

  const fit = (pD: number, gap: number, pad: number) => {
    const cD = Math.max(44, Math.round(pD * 1.7)); // the star must dominate its system
    const lOff = pD / 2 + gap + labelW / 2;
    return {
      planetD: pD,
      coreD: cD,
      labelOff: lOff,
      minR: (cD / 2 + pD / 2 + 10) / TILT, // RULE 1
      maxR: Math.min(
        BW / 2 - lOff - labelW / 2 - pad,
        (BH / 2 - capH / 2 - pad) / TILT - lOff
      ),
    };
  };

  const ideal = Math.max(36, Math.min(84, Math.round(SS * 0.115)));

  // RULE 2 — [leaderGap, edgePadding, planetFloor]
  let geo: ReturnType<typeof fit> | null = null;
  for (const [gap, pad, floor] of [
    [24, 16, 44],
    [14, 10, 38],
    [9, 6, 34],
  ]) {
    let g = fit(ideal, gap, pad);
    while (g.maxR < g.minR && g.planetD > floor) g = fit(g.planetD - 2, gap, pad);
    if (g.maxR >= g.minR) {
      geo = g;
      break;
    }
    if (!geo || g.planetD > geo.planetD) geo = g;
  }
  const g = geo!;

  const minR = g.minR;
  const maxR = Math.max(g.minR, g.maxR);

  // RULE 3
  const sep = g.planetD * 1.25;
  const laneN = Math.max(1, Math.min(wantLanes, 1 + Math.floor((maxR - minR) / sep)));
  const laneR = Array.from({ length: laneN }, (_, i) => maxR - (laneN - 1 - i) * sep);

  return {
    planetD: g.planetD,
    coreD: g.coreD,
    labelOff: g.labelOff,
    labelW,
    capH,
    cap,
    minR,
    maxR,
    laneR,
    laneN,
  };
}

/** Clamp a station's preferred lane to the lanes that actually fit. */
export const laneIndex = (lane: number, laneN: number) => Math.min(lane, laneN - 1);

/**
 * Orbit period per lane, seconds. Inner lanes orbit faster (Kepler-ish).
 * Planets on the same lane are spaced by a NEGATIVE animation-delay of
 * (i / count) * period — this is what makes them evenly distributed and, crucially,
 * keeps the whole orbit on the compositor with zero per-frame JS.
 */
export const LANE_PERIOD = [46, 74];

/**
 * Stable pseudo-random. Used for the plate dial, the seeded run history and the
 * per-throw physics roll. Must be deterministic: re-rolling on every React render
 * makes the debris jitter mid-flight.
 */
export const rnd = (n: number) => {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

/** Per-throw physics roll. Seed on cycle + agent + beat so it is stable for one throw. */
export interface ThrowRoll {
  arc: string;
  arcH: number;
  arcEase: string;
  ease: string;
  durK: number;
  tumble: string;
  shape: string;
  sizeK: number;
  hi: string;
  echoN: number;
  shards: { a: number; reach: number; d: number; ms: number; delay: number }[];
}

export function rollThrow(cycle: number, agent: number, beat: string, massD: number): ThrowRoll {
  const sd =
    cycle * 9.7 + agent * 3.3 + (beat === 'throw' ? 0.11 : beat === 'retry' ? 0.53 : 0.77);
  const r1 = rnd(sd),
    r2 = rnd(sd + 17),
    r3 = rnd(sd + 41),
    r4 = rnd(sd + 73),
    r5 = rnd(sd + 101);

  const ARCS = ['saArcHi', 'saArcLo', 'saArcUnder', 'saArcWob', 'saArcKick', 'saArcSling'];
  const TUMB = ['saTumbleA', 'saTumbleB', 'saTumbleC'];
  const EASES = [
    'cubic-bezier(0.18,0.92,0.12,1)',
    'cubic-bezier(0.4,0.02,0.2,1)',
    'cubic-bezier(0.62,0.01,0.3,1)',
    'cubic-bezier(0.1,0.85,0.3,1)',
  ];
  const SHAPES = ['42% 58% 55% 45%', '60% 40% 38% 62%', '48% 52% 62% 38%', '999px', '35% 65% 50% 50%'];
  const nSh = 2 + Math.floor(r5 * 3);

  return {
    arc: ARCS[Math.floor(r1 * ARCS.length)],
    arcH: 0.55 + r2 * 1.5,
    arcEase: r3 > 0.5 ? 'ease-in-out' : 'cubic-bezier(0.3,0.7,0.4,1)',
    ease: EASES[Math.floor(r4 * EASES.length)],
    durK: 0.78 + r2 * 0.22,
    tumble: TUMB[Math.floor(r3 * TUMB.length)],
    shape: SHAPES[Math.floor(r4 * SHAPES.length)],
    sizeK: 0.78 + r1 * 0.62,
    hi: `${Math.round(24 + r2 * 34)}% ${Math.round(22 + r3 * 32)}%`,
    echoN: 1.6 + r4 * 1.8,
    shards: Array.from({ length: nSh }, (_, k) => ({
      a: Math.round(rnd(sd + k * 13) * 360),
      reach: Math.round(14 + rnd(sd + k * 29) * 34),
      d: Math.max(2, Math.round(massD * (0.18 + rnd(sd + k * 7) * 0.3))),
      ms: Math.round(340 + rnd(sd + k * 5) * 520),
      delay: Math.round(rnd(sd + k * 3) * 420),
    })),
  };
}

/**
 * Measure hook contract (React):
 *
 *   const [box, setBox] = useState({ w: 680, h: 400 });
 *   const ref = useCallback((el: HTMLElement | null) => { ... ResizeObserver ... }, []);
 *
 * IMPORTANT: measure again in a double requestAnimationFrame after mount. The first
 * observed box is often a pre-layout value, and geometry computed from it bottoms the
 * bodies out at their floor — a bug that only self-heals on a resize the user may never
 * trigger. Use a 2px change threshold, not 6px.
 */
