import { describe, it, expect } from 'vitest';
import { computeOrrery, rollThrow, TILT } from './orrery-geometry';
import { STATIONS } from './stations';

// The layout rules from the design handoff. Every past layout bug lived here.
const stations = STATIONS.map((s) => ({ name: s.name, lane: s.lane }));

describe('computeOrrery', () => {
  it('keeps bodies large in the reference 492x300 plate, never the floor value', () => {
    const g = computeOrrery(492, 300, stations);
    expect(g.planetD).toBeGreaterThanOrEqual(34);
    expect(g.planetD).not.toBe(34);
  });

  it('separates every pair of lanes by at least planetD * 1.25', () => {
    for (const [w, h] of [
      [492, 300],
      [680, 400],
      [1100, 520],
      [320, 320],
    ]) {
      const g = computeOrrery(w, h, stations);
      for (let i = 0; i < g.laneR.length; i++) {
        for (let j = i + 1; j < g.laneR.length; j++) {
          expect(Math.abs(g.laneR[i] - g.laneR[j])).toBeGreaterThanOrEqual(g.planetD * 1.25 - 1e-6);
        }
      }
    }
  });

  it('clears the star in the squashed axis: minR * TILT >= coreD/2 + planetD/2', () => {
    for (const [w, h] of [
      [240, 170],
      [492, 300],
      [1400, 700],
    ]) {
      const g = computeOrrery(w, h, stations);
      expect(g.minR * TILT).toBeGreaterThanOrEqual(g.coreD / 2 + g.planetD / 2);
    }
  });

  it('keeps the outer lane label inside the box', () => {
    for (const [w, h] of [
      [492, 300],
      [680, 400],
      [900, 380],
    ]) {
      const g = computeOrrery(w, h, stations);
      const outer = g.laneR[g.laneR.length - 1];
      expect(outer + g.labelOff + g.labelW / 2).toBeLessThanOrEqual(w / 2 + 1e-6);
    }
  });

  it('never emits more lanes than stations want, and at least one', () => {
    const g = computeOrrery(240, 170, stations);
    expect(g.laneN).toBeGreaterThanOrEqual(1);
    expect(g.laneN).toBeLessThanOrEqual(2);
    expect(g.laneR).toHaveLength(g.laneN);
  });
});

describe('rollThrow', () => {
  it('is deterministic for the same seed', () => {
    const a = rollThrow(47, 0, 'throw', 12);
    const b = rollThrow(47, 0, 'throw', 12);
    expect(a).toEqual(b);
  });

  it('rolls differently for the inbound throw and the outbound signal', () => {
    const inbound = rollThrow(47, 2, 'throw', 12);
    const outbound = rollThrow(47, 2, 'signal', 12);
    expect(inbound).not.toEqual(outbound);
  });

  it('produces between two and four shards with sane reach', () => {
    for (let c = 1; c < 40; c++) {
      const r = rollThrow(c, c % 4, 'throw', 12);
      expect(r.shards.length).toBeGreaterThanOrEqual(2);
      expect(r.shards.length).toBeLessThanOrEqual(4);
      for (const sh of r.shards) {
        expect(sh.reach).toBeGreaterThanOrEqual(14);
        expect(sh.reach).toBeLessThanOrEqual(48);
      }
    }
  });
});
