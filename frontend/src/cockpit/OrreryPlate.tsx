/**
 * The glass plate with the Synapse star at the centre and the four agents
 * orbiting it on a tilted plane. Geometry comes from orrery-geometry.ts;
 * motion is pure CSS animation with negative delays (see index.css).
 */
import type { CSSProperties } from 'react';
import { computeOrrery, laneIndex, LANE_PERIOD, rollThrow } from './orrery-geometry';
import { mix, PB, RXL } from './palette';
import { useCockpit } from './store';
import { N, STATIONS, STORE_CAP } from './stations';
import { useBoxSize } from './useBoxSize';
import { doneish, useCockpitView, type PlanetState } from './useCockpitView';

const STATUS_LABEL: Record<PlanetState, string> = {
  locked: 'halted',
  fault: 'fault',
  held: 'held',
  idle: 'standby',
  active: 'working',
  done: 'done',
  queued: 'queued',
  waking: 'waking',
  throwing: 'throwing',
};

export function OrreryPlate() {
  const { box, ref } = useBoxSize();
  const v = useCockpitView();
  const openCard = useCockpit((s) => s.openCard);
  const { pal, mode, beat, bi, dur, el, bp, states, storeN, coreHot, coreAlarm } = v;

  const BW = box.w;
  const BH = box.h;
  const SS = Math.min(BW, BH * 1.7);
  const geo = computeOrrery(BW, BH, STATIONS);
  const { planetD, coreD, labelOff, labelW, cap, maxR, laneR } = geo;

  const PINK = pal.ink;
  const PN3 = pal.n3;
  const PN2 = pal.n2;
  const PN6 = pal.n6;
  const PN7 = pal.n7;
  const TER = pal.ter;
  const TER3 = pal.ter3;
  const TER4 = pal.ter4;
  const TER6 = pal.ter6;
  const TER7 = pal.ter7;
  const SGE = pal.sge;
  const SGE3 = pal.sge3;
  const SGE6 = pal.sge6;
  const SGE7 = pal.sge7;
  const dim = mode === 'idle' || mode === 'locked';

  // ── dial: 72 graduations on the plate rim
  const dialRx = BW / 2 - 7;
  const dialRy = BH / 2 - 7;
  const dialTicks = Array.from({ length: 72 }, (_, i) => {
    const a = (i / 72) * Math.PI * 2;
    const major = i % 6 === 0;
    const x = BW / 2 + Math.cos(a) * dialRx;
    const y = BH / 2 + Math.sin(a) * dialRy;
    const deg = (Math.atan2(Math.sin(a) * dialRy, Math.cos(a) * dialRx) * 180) / Math.PI;
    return (
      <span
        key={i}
        style={{
          position: 'absolute',
          left: x,
          top: y,
          width: major ? 9 : 5,
          height: 1,
          transform: `translate(-50%,-50%) rotate(${deg.toFixed(1)}deg)`,
          transformOrigin: '50% 50%',
          background: major ? TER3 : PN3,
          pointerEvents: 'none',
        }}
      />
    );
  });

  // ── the throw's physics, stable for one flight
  const throwIdx = beat === 'throw' ? bi : beat === 'signal' ? (bi + 1) % N : beat === 'retry' ? N - 1 : -1;
  const massD = Math.max(11, Math.round(SS * 0.022));
  const tk = rollThrow(v.cycle, bi, beat, massD);
  const flightMs = Math.round(dur * tk.durK);

  const plate: CSSProperties = {
    position: 'absolute',
    inset: 0,
    overflow: 'hidden',
    borderRadius: RXL,
    background: `linear-gradient(158deg, ${mix(pal.plate, 40)} 0%, ${mix(pal.plate, 26)} 48%, ${mix(pal.plate, 36)} 100%)`,
    backdropFilter: `blur(26px) saturate(1.45) brightness(${pal.dark ? 1.1 : 1.04})`,
    WebkitBackdropFilter: `blur(26px) saturate(1.45) brightness(${pal.dark ? 1.1 : 1.04})`,
    border: `1px solid ${mix('#ffffff', pal.dark ? 12 : 42)}`,
    boxShadow: `0 22px 52px ${mix('#000000', pal.dark ? 42 : 14)}, inset 0 1px 0 ${mix('#ffffff', pal.dark ? 16 : 58)}, inset 0 -18px 40px -22px ${mix('#000000', pal.dark ? 34 : 12)}`,
  };

  return (
    <div ref={ref as (el: HTMLDivElement | null) => void} data-orrery style={{ position: 'absolute', inset: 0 }}>
      <div style={plate}>
        <div
          style={{
            position: 'absolute',
            left: '-20%',
            top: '-60%',
            width: '90%',
            height: '220%',
            transform: 'rotate(18deg)',
            pointerEvents: 'none',
            background: `linear-gradient(90deg, transparent, ${mix('#ffffff', pal.sheen * 30)} 48%, transparent)`,
            filter: 'blur(18px)',
          }}
        />
        <div
          style={{
            position: 'absolute',
            inset: 5,
            borderRadius: `calc(${RXL} - 4px)`,
            border: `1px solid ${mix(TER3, pal.dark ? 26 : 46)}`,
            pointerEvents: 'none',
          }}
        />
        {dialTicks}

        <div style={{ position: 'absolute', inset: 0 }}>
          {/* engraved sunburst: fine ruled spokes, not a glow */}
          <div
            style={{
              position: 'absolute',
              left: '50%',
              top: '50%',
              width: Math.round(coreD * 3.6),
              height: Math.round(coreD * 3.6),
              transform: 'translate(-50%,-50%)',
              borderRadius: 999,
              pointerEvents: 'none',
              zIndex: 1,
              background: `repeating-conic-gradient(from 0deg, ${TER3} 0deg 0.7deg, transparent 0.7deg 11.25deg)`,
              mask: 'radial-gradient(circle, transparent 30%, #000 41%, transparent 60%)',
              WebkitMask: 'radial-gradient(circle, transparent 30%, #000 41%, transparent 60%)',
              opacity: dim ? 0.2 : coreHot ? 0.95 : 0.55,
              transition: 'opacity 0.6s',
              animation: 'saSun 150s linear infinite',
            }}
          />
          <div
            style={{
              position: 'absolute',
              left: '50%',
              top: '50%',
              width: Math.round(coreD * 2.5),
              height: Math.round(coreD * 2.5),
              transform: 'translate(-50%,-50%)',
              borderRadius: 999,
              pointerEvents: 'none',
              zIndex: 1,
              background: `repeating-conic-gradient(from 2.8deg, ${mix(TER, 34)} 0deg 0.5deg, transparent 0.5deg 5.62deg)`,
              mask: 'radial-gradient(circle, transparent 41%, #000 54%, transparent 72%)',
              WebkitMask: 'radial-gradient(circle, transparent 41%, #000 54%, transparent 72%)',
              opacity: dim ? 0.16 : 0.5,
              transition: 'opacity 0.6s',
              animation: 'saSunBack 210s linear infinite',
            }}
          />
          <div
            style={{
              position: 'absolute',
              left: '50%',
              top: '50%',
              width: Math.round(coreD * 2.1),
              height: Math.round(coreD * 2.1),
              transform: 'translate(-50%,-50%)',
              borderRadius: 999,
              pointerEvents: 'none',
              zIndex: 1,
              background: `radial-gradient(circle, ${mix(TER, 26)} 0%, transparent 66%)`,
              opacity: dim ? 0.25 : coreHot ? 1 : 0.6,
              transition: 'opacity 0.6s',
              animation: coreHot ? 'saInk 2.2s ease-in-out infinite' : undefined,
            }}
          />

          {/* the orbital plane */}
          {/* The plane sits above the star so labels stay legible. It must not
              catch pointer events itself, or the star underneath is unclickable;
              the planet buttons opt back in. */}
          <div style={{ position: 'absolute', inset: 0, zIndex: 4, transform: 'scaleY(0.5)', transformOrigin: '50% 50%', pointerEvents: 'none' }}>
            {laneR.map((r, k) => (
              <span
                key={`lane${k}`}
                style={{
                  position: 'absolute',
                  left: '50%',
                  top: '50%',
                  width: r * 2,
                  height: r * 2,
                  margin: `-${r}px 0 0 -${r}px`,
                  borderRadius: 999,
                  border: `1px solid ${TER3}`,
                  pointerEvents: 'none',
                }}
              />
            ))}
            {Array.from({ length: 60 }, (_, i) => {
              const major = i % 5 === 0;
              return (
                <span
                  key={`tick${i}`}
                  style={{
                    position: 'absolute',
                    left: '50%',
                    top: '50%',
                    width: maxR,
                    height: 1,
                    transformOrigin: '0 50%',
                    transform: `rotate(${i * 6}deg)`,
                    pointerEvents: 'none',
                    background: `linear-gradient(90deg, transparent calc(100% - ${major ? 8 : 4}px), ${major ? TER3 : PN3} calc(100% - ${major ? 8 : 4}px))`,
                  }}
                />
              );
            })}

            {STATIONS.map((st, i) => {
              const c = states[i];
              const hot = c === 'active';
              const bad = c === 'fault';
              const held = c === 'held';
              const waking = c === 'waking';
              const throwing = c === 'throwing';
              const done = doneish(c) && !bad;
              const li = laneIndex(st.lane, laneR.length);
              const r = laneR[li];
              const per = LANE_PERIOD[li % LANE_PERIOD.length];
              const phase = (i / N) * per;
              const spin: CSSProperties = {
                animationDuration: `${per}s`,
                animationTimingFunction: 'linear',
                animationIterationCount: 'infinite',
                animationDelay: `-${phase.toFixed(2)}s`,
              };
              const lit = hot || waking || bad;
              const idleFill = pal.dark ? mix('#000000', 26) : PB;
              const fill = bad ? TER7 : lit ? TER : done ? SGE6 : idleFill;
              const edge = bad ? TER7 : lit ? TER6 : done ? SGE7 : PN3;
              const glyphC = bad || lit || done ? PB : PN6;
              const arcR = planetD / 2 + Math.max(6, Math.round(planetD * 0.17));
              const arcOn = hot ? bp : done || throwing ? 1 : 0;
              const ink = bad || held ? TER7 : lit ? TER7 : done ? SGE7 : PN6;
              const isMe = throwIdx === i;
              const mAnim = beat === 'throw' ? 'saThrowX' : beat === 'retry' ? 'saBounceX' : 'saSignalX';
              const massAnim = beat === 'throw' ? 'saThrowMass' : 'saSignalMass';
              const inbound = beat === 'throw';
              const Icon = st.icon;
              const massPx = Math.round(massD * tk.sizeK);
              const leaderW = Math.max(4, Math.round(labelOff - planetD / 2 - labelW / 2 - 4));

              return (
                <div
                  key={st.name}
                  style={{
                    position: 'absolute',
                    left: '50%',
                    top: '50%',
                    width: r,
                    height: 0,
                    transformOrigin: '0 50%',
                    animationName: 'saRail',
                    ...spin,
                    willChange: 'transform',
                  }}
                >
                  {isMe && (
                    <span
                      style={{
                        position: 'absolute',
                        top: 0,
                        left: '14%',
                        width: 0,
                        height: 0,
                        animationName: mAnim,
                        animationDuration: `${flightMs}ms`,
                        animationTimingFunction: tk.ease,
                        animationFillMode: 'forwards',
                      }}
                    >
                      <span
                        style={{
                          position: 'absolute',
                          left: 0,
                          top: 0,
                          width: 0,
                          height: Math.round(planetD * tk.arcH),
                          animation: `${tk.arc} ${flightMs}ms ${tk.arcEase} forwards`,
                        }}
                      >
                        <span
                          style={{
                            position: 'absolute',
                            left: 0,
                            top: 0,
                            width: massD * 2,
                            height: massD * 2,
                            margin: `-${massD}px 0 0 -${massD}px`,
                            borderRadius: 999,
                            border: `1px solid ${inbound ? SGE : TER}`,
                            animation: `saEcho ${Math.round(flightMs / tk.echoN)}ms ease-out infinite`,
                          }}
                        />
                        {tk.shards.map((sh, k) => (
                          <span
                            key={k}
                            style={{
                              position: 'absolute',
                              left: 0,
                              top: 0,
                              width: sh.reach,
                              height: 0,
                              transformOrigin: '0 50%',
                              transform: `rotate(${sh.a}deg)`,
                              pointerEvents: 'none',
                            }}
                          >
                            <span
                              style={{
                                position: 'absolute',
                                top: 0,
                                width: sh.d,
                                height: sh.d,
                                borderRadius: 999,
                                background: inbound ? SGE7 : TER7,
                                animation: `saShardOut ${sh.ms}ms ease-out ${sh.delay}ms infinite`,
                              }}
                            />
                          </span>
                        ))}
                        <span
                          style={{
                            position: 'absolute',
                            left: 0,
                            top: 0,
                            width: massPx,
                            height: massPx,
                            margin: `-${Math.round(massPx / 2)}px 0 0 -${Math.round(massPx / 2)}px`,
                            borderRadius: tk.shape,
                            background: `radial-gradient(circle at ${tk.hi}, ${inbound ? SGE3 : TER4}, ${inbound ? SGE7 : TER7} 72%)`,
                            boxShadow: `0 ${Math.round(massD * 0.2)}px ${Math.round(massD * 0.5)}px ${mix(PINK, 26)}`,
                            animation: `${tk.tumble} ${flightMs}ms ${tk.arcEase} forwards`,
                          }}
                        />
                        <span style={{ display: 'none' }}>{massAnim}</span>
                      </span>
                    </span>
                  )}

                  <button
                    onClick={() => openCard({ kind: 'agent', i })}
                    aria-label={`${st.name} · ${STATUS_LABEL[c]}`}
                    style={{
                      position: 'absolute',
                      right: 0,
                      top: '50%',
                      width: planetD,
                      height: planetD,
                      marginTop: -planetD / 2,
                      marginRight: -planetD / 2,
                      padding: 0,
                      border: 'none',
                      background: 'transparent',
                      cursor: 'pointer',
                      pointerEvents: 'auto',
                      transformOrigin: '50% 50%',
                      animationName: 'saUpright',
                      ...spin,
                      willChange: 'transform',
                      color: 'inherit',
                    }}
                  >
                    <span
                      style={{
                        position: 'absolute',
                        left: '50%',
                        top: '50%',
                        width: Math.round(planetD * 1.5),
                        height: Math.round(planetD * 1.5),
                        margin: `-${Math.round(planetD * 0.75)}px 0 0 -${Math.round(planetD * 0.75)}px`,
                        borderRadius: 999,
                        border: `1px solid ${bad ? TER : lit ? TER3 : done ? SGE3 : 'transparent'}`,
                        opacity: lit || bad ? 1 : done ? 0.6 : 0,
                        pointerEvents: 'none',
                        animation: hot || bad ? 'saHold 2.6s ease-in-out infinite' : undefined,
                      }}
                    />
                    <span
                      style={{
                        position: 'absolute',
                        inset: 0,
                        borderRadius: 999,
                        background: fill,
                        backgroundImage: bad
                          ? `repeating-linear-gradient(135deg, transparent 0 5px, ${mix(PB, 26)} 5px 10px)`
                          : undefined,
                        border: `${done || lit || bad ? 2 : 1}px solid ${edge}`,
                        boxShadow: `0 ${Math.round(planetD * 0.09)}px ${Math.round(planetD * 0.2)}px ${mix(PINK, 20)}, inset 0 1px 0 ${mix(PB, lit || done ? 26 : 0)}`,
                        opacity: held ? 0.55 : c === 'queued' || c === 'idle' || c === 'locked' ? 0.85 : 1,
                        transition: 'background 0.45s, border-color 0.45s, opacity 0.45s',
                        animation: waking ? 'saWake 0.7s ease-out' : undefined,
                      }}
                    >
                      <span style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', color: glyphC }}>
                        <Icon size={Math.max(12, Math.round(planetD * 0.3))} strokeWidth={2.75} />
                      </span>
                    </span>
                    <svg
                      viewBox="0 0 100 100"
                      style={{
                        position: 'absolute',
                        left: '50%',
                        top: '50%',
                        width: arcR * 2,
                        height: arcR * 2,
                        margin: `-${arcR}px 0 0 -${arcR}px`,
                        pointerEvents: 'none',
                      }}
                    >
                      <circle cx="50" cy="50" r="46" fill="none" strokeWidth="2.5" style={{ stroke: PN2 }} />
                      <circle
                        cx="50"
                        cy="50"
                        r="46"
                        fill="none"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        transform="rotate(-90 50 50)"
                        style={{
                          stroke: bad ? TER7 : done ? SGE7 : TER,
                          strokeDasharray: 289.03,
                          strokeDashoffset: (289.03 * (1 - arcOn)).toFixed(1),
                          transition: `stroke-dashoffset ${hot ? Math.max(0, Math.round(dur - el)) : 0}ms linear, stroke 0.4s`,
                        }}
                      />
                    </svg>
                  </button>

                  <span style={{ position: 'absolute', left: '100%', top: '50%', width: labelOff, height: 0, pointerEvents: 'none' }}>
                    <span
                      style={{
                        position: 'absolute',
                        left: Math.round(planetD / 2 + 2),
                        top: 0,
                        width: leaderW,
                        height: 1,
                        background: lit ? TER3 : PN3,
                        pointerEvents: 'none',
                      }}
                    />
                    <span
                      style={{
                        position: 'absolute',
                        left: '100%',
                        top: 0,
                        width: 0,
                        height: 0,
                        transformOrigin: '0 50%',
                        animationName: 'saUpright',
                        ...spin,
                      }}
                    >
                      <span
                        style={{
                          position: 'absolute',
                          left: 0,
                          top: 0,
                          width: labelW,
                          transform: 'translate(-50%,-50%)',
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                          gap: 1,
                          textAlign: 'center',
                        }}
                      >
                        <span
                          style={{
                            fontFamily: 'var(--font-heading)',
                            fontSize: Math.round(14 * cap),
                            lineHeight: 1.05,
                            whiteSpace: 'nowrap',
                            color: lit ? TER7 : done ? PINK : PN7,
                          }}
                        >
                          {st.name}
                        </span>
                        <span
                          style={{
                            fontSize: Math.round(8.5 * cap),
                            fontWeight: 600,
                            letterSpacing: '0.13em',
                            textTransform: 'uppercase',
                            whiteSpace: 'nowrap',
                            color: ink,
                          }}
                        >
                          {STATUS_LABEL[c]}
                        </span>
                      </span>
                    </span>
                  </span>
                </div>
              );
            })}
          </div>

          {/* store gauge around the star */}
          <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 3 }}>
            {Array.from({ length: STORE_CAP }, (_, k) => {
              const on = k < storeN;
              const a = -90 + (360 / STORE_CAP) * k;
              const rr = coreD / 2 + Math.max(11, Math.round(coreD * 0.2));
              return (
                <span
                  key={k}
                  style={{
                    position: 'absolute',
                    left: '50%',
                    top: '50%',
                    width: rr,
                    height: on ? 3 : 1,
                    marginTop: on ? -1.5 : -0.5,
                    transformOrigin: '0 50%',
                    transform: `rotate(${a}deg)`,
                    pointerEvents: 'none',
                  }}
                >
                  <span
                    style={{
                      position: 'absolute',
                      right: 0,
                      top: 0,
                      width: on ? 9 : 5,
                      height: '100%',
                      borderRadius: 1,
                      background: on ? (coreAlarm ? TER7 : TER) : PN3,
                      transition: 'background 0.4s, width 0.3s',
                    }}
                  />
                </span>
              );
            })}
          </div>

          {/* the star */}
          <button
            onClick={() => openCard({ kind: 'core' })}
            aria-label={`Synapse · ${storeN} of ${STORE_CAP} held`}
            style={{
              position: 'absolute',
              left: '50%',
              top: '50%',
              width: coreD,
              height: coreD,
              margin: `-${coreD / 2}px 0 0 -${coreD / 2}px`,
              padding: 0,
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              zIndex: 2,
            }}
          >
            {beat === 'flare' && (
              <>
                <span
                  style={{
                    position: 'absolute',
                    inset: -2,
                    borderRadius: 999,
                    border: `2px solid ${TER}`,
                    animation: `saRipple ${Math.round(dur * 1.8)}ms cubic-bezier(0.1,0.7,0.3,1) forwards`,
                  }}
                />
                <span
                  style={{
                    position: 'absolute',
                    inset: 2,
                    borderRadius: 999,
                    border: `1px solid ${TER6}`,
                    animation: `saRipple ${Math.round(dur * 2.4)}ms cubic-bezier(0.1,0.7,0.3,1) 130ms forwards`,
                  }}
                />
              </>
            )}
            <span
              style={{
                position: 'absolute',
                inset: 0,
                borderRadius: 999,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 1,
                overflow: 'hidden',
                background: `radial-gradient(circle at 44% 36%, ${TER4} 0%, ${TER} 44%, ${TER6} 92%)`,
                border: `2px solid ${TER7}`,
                boxShadow: `0 ${Math.round(coreD * 0.06)}px ${Math.round(coreD * 0.18)}px ${mix(PINK, 26)}${coreHot ? `, 0 0 0 ${Math.round(coreD * 0.07)}px ${mix(TER, 24)}` : ''}`,
                opacity: dim ? 0.45 : 1,
                transition: 'box-shadow 0.45s, opacity 0.6s',
                animation: beat === 'flare' ? `saSnap ${Math.round(dur * 1.5)}ms ease-out` : undefined,
              }}
            >
              <span
                style={{
                  position: 'absolute',
                  inset: 0,
                  borderRadius: 999,
                  pointerEvents: 'none',
                  background: `repeating-radial-gradient(circle at 50% 50%, transparent 0 ${Math.round(coreD * 0.075)}px, ${mix(PB, 15)} ${Math.round(coreD * 0.075)}px ${Math.round(coreD * 0.075) + 1}px)`,
                }}
              />
              <span
                className="num"
                style={{
                  position: 'relative',
                  fontFamily: 'var(--font-heading)',
                  fontSize: Math.round(coreD * 0.235),
                  lineHeight: 1,
                  letterSpacing: '-0.02em',
                  color: PB,
                }}
              >
                {storeN}/{STORE_CAP}
              </span>
              {coreD > 78 && (
                <span
                  style={{
                    position: 'relative',
                    fontSize: Math.max(7, Math.round(coreD * 0.085)),
                    fontWeight: 600,
                    letterSpacing: '0.12em',
                    textTransform: 'uppercase',
                    color: mix(PB, 78),
                  }}
                >
                  held
                </span>
              )}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}
