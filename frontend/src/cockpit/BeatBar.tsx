/**
 * Plain-language narration of the current beat plus the cycle time axis.
 */
import { ACS, E, glassStyle, mix, RL, SGS, T1, T4 } from './palette';
import { FLARE_MS, N, SIGNAL_MS, STATIONS, STORE_CAP, THROW_MS, WORK_VERBS } from './stations';
import { doneish, useCockpitView } from './useCockpitView';

export function BeatBar({ narrow, short }: { narrow: boolean; short: boolean }) {
  const v = useCockpitView();
  const { pal, mode, beat, bi, bp, working, transiting, states, storeN, coreHot, coreAlarm, retries } = v;

  const transitMs = THROW_MS + FLARE_MS + SIGNAL_MS;
  const segs: { k: 'w' | 't'; i: number; ms: number; name: string }[] = [];
  STATIONS.forEach((st, i) => {
    segs.push({ k: 'w', i, ms: st.dur, name: st.name });
    segs.push({ k: 't', i, ms: transitMs, name: `Throw · ${st.name} → ${STATIONS[(i + 1) % N].name}` });
  });
  const totalMs = segs.reduce((a, x) => a + x.ms, 0);
  const curKey = working ? `w${bi}` : transiting ? `t${bi}` : '';

  const nextName = STATIONS[(bi + 1) % N].name;
  const text =
    mode === 'locked'
      ? 'Everything is stopped'
      : mode === 'idle'
        ? 'The star is dark — nothing worth trading'
        : mode === 'fault'
          ? 'The throw keeps bouncing off the Hand'
          : mode === 'choke'
            ? 'The store is full — the star cannot throw back'
            : beat === 'work'
              ? `${STATIONS[bi].name} is ${WORK_VERBS[bi]}`
              : beat === 'throw'
                ? `${STATIONS[bi].name} throws the ${STATIONS[bi].payload} at the star`
                : beat === 'flare'
                  ? `Caught — the star swallows the ${STATIONS[bi].payload}`
                  : `The star throws the signal out to the ${nextName}`;
  const meta =
    mode === 'fault'
      ? `retry ${retries} of 5`
      : mode === 'choke'
        ? `${storeN}/${STORE_CAP} held`
        : working
          ? `${(v.dur / 1000).toFixed(2)}s budget · ${Math.round(bp * 100)}%`
          : transiting
            ? `in flight · ${(transitMs / 1000).toFixed(2)}s`
            : `${(totalMs / 1000).toFixed(2)}s cycle`;

  return (
    <div
      style={{
        flex: 'none',
        display: 'flex',
        flexDirection: 'column',
        gap: 9,
        padding: short ? '10px 14px' : '12px 16px',
        borderRadius: RL,
        ...glassStyle(pal),
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9, minWidth: 0 }}>
          <span
            style={{
              flex: 'none',
              width: 8,
              height: 8,
              borderRadius: 999,
              background: coreAlarm ? ACS : coreHot ? ACS : working ? SGS : E,
              animation: coreHot || working ? 'saBreathe 1.6s ease-in-out infinite' : undefined,
            }}
          />
          <span style={{ fontFamily: 'var(--font-heading)', fontSize: narrow ? 14 : 16, lineHeight: 1.2, color: T1 }}>{text}</span>
        </div>
        <span className="num" style={{ fontSize: 11, fontWeight: 600, whiteSpace: 'nowrap', color: T4 }}>
          {meta}
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'stretch', gap: 3, height: 8 }}>
        {segs.map((x) => {
          const cur = x.k + x.i === curKey;
          const past = x.k === 'w' ? doneish(states[x.i]) && !cur : x.i < bi;
          const c = cur ? ACS : past ? SGS : E;
          return (
            <span
              key={x.k + x.i}
              title={`${x.name} · ${(x.ms / 1000).toFixed(2)}s`}
              style={{
                flex: `${x.ms} 1 0`,
                height: '100%',
                borderRadius: 999,
                minWidth: 3,
                background: x.k === 't' ? 'transparent' : c,
                backgroundImage:
                  x.k === 't' ? `repeating-linear-gradient(90deg, ${mix(c, cur ? 85 : 50)} 0 3px, transparent 3px 7px)` : undefined,
                opacity: cur ? 1 : past ? 0.85 : 0.32,
                transition: 'background 0.4s, opacity 0.4s',
              }}
            />
          );
        })}
      </div>
    </div>
  );
}
