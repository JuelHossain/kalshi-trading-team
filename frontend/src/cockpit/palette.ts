/**
 * The two palettes from the prototype. Each resolves to a set of CSS custom
 * properties placed on the cockpit root, so every component reads var(--x)
 * and the Light/Dark toggle is one style object swap.
 */
import type { CSSProperties } from 'react';

export type PaletteKey = 'cream' | 'night';

export interface Palette {
  key: PaletteKey;
  name: string;
  dark: boolean;
  g: string;
  p: string;
  e: string;
  t1: string;
  t2: string;
  t3: string;
  t4: string;
  f: string;
  ac: string;
  acs: string;
  aci: string;
  sg: string;
  sgs: string;
  plate: string;
  ink: string;
  n8: string;
  n7: string;
  n6: string;
  n4: string;
  n3: string;
  n2: string;
  ter: string;
  ter3: string;
  ter4: string;
  ter6: string;
  ter7: string;
  sge: string;
  sge3: string;
  sge6: string;
  sge7: string;
  sheen: number;
  rim: number;
}

export const PALETTES: Record<PaletteKey, Palette> = {
  cream: {
    key: 'cream',
    name: 'Light',
    dark: false,
    g: 'var(--color-bg)',
    p: 'var(--color-neutral-100)',
    e: 'var(--color-neutral-300)',
    t1: 'var(--color-text)',
    t2: 'var(--color-neutral-800)',
    t3: 'var(--color-neutral-700)',
    t4: 'var(--color-neutral-600)',
    f: 'var(--color-neutral-500)',
    ac: 'var(--color-accent-700)',
    acs: 'var(--color-accent)',
    aci: 'var(--color-bg)',
    sg: 'var(--color-accent-2-700)',
    sgs: 'var(--color-accent-2)',
    plate: 'var(--color-bg)',
    ink: 'var(--color-text)',
    n8: 'var(--color-neutral-800)',
    n7: 'var(--color-neutral-700)',
    n6: 'var(--color-neutral-600)',
    n4: 'var(--color-neutral-400)',
    n3: 'var(--color-neutral-400)',
    n2: 'var(--color-neutral-300)',
    ter: 'var(--color-accent)',
    ter3: 'var(--color-accent-400)',
    ter4: 'var(--color-accent-400)',
    ter6: 'var(--color-accent-600)',
    ter7: 'var(--color-accent-700)',
    sge: 'var(--color-accent-2)',
    sge3: 'var(--color-accent-2-300)',
    sge6: 'var(--color-accent-2-600)',
    sge7: 'var(--color-accent-2-700)',
    sheen: 0.5,
    rim: 0.5,
  },
  night: {
    key: 'night',
    name: 'Dark',
    dark: true,
    g: '#1c1916',
    p: '#292420',
    e: '#41392f',
    t1: 'var(--color-bg)',
    t2: 'var(--color-neutral-300)',
    t3: 'var(--color-neutral-400)',
    t4: 'var(--color-neutral-500)',
    f: 'var(--color-neutral-600)',
    ac: 'var(--color-accent-400)',
    acs: 'var(--color-accent)',
    aci: '#1c1916',
    sg: 'var(--color-accent-2-400)',
    sgs: 'var(--color-accent-2)',
    plate: '#3a322a',
    ink: 'var(--color-bg)',
    n8: 'var(--color-neutral-200)',
    n7: 'var(--color-neutral-300)',
    n6: 'var(--color-neutral-400)',
    n4: 'var(--color-neutral-600)',
    n3: 'var(--color-neutral-600)',
    n2: 'var(--color-neutral-700)',
    ter: 'var(--color-accent)',
    ter3: 'var(--color-accent-400)',
    ter4: 'var(--color-accent-300)',
    ter6: 'var(--color-accent-600)',
    ter7: 'var(--color-accent-300)',
    sge: 'var(--color-accent-2)',
    sge3: 'var(--color-accent-2-300)',
    sge6: 'var(--color-accent-2)',
    sge7: 'var(--color-accent-2-300)',
    sheen: 0.16,
    rim: 0.14,
  },
};

/** Short aliases used throughout the cockpit, read from the root vars. */
export const G = 'var(--g)';
export const P = 'var(--p)';
export const E = 'var(--e)';
export const GL = 'var(--glass)';
export const T1 = 'var(--t1)';
export const T2 = 'var(--t2)';
export const T3 = 'var(--t3)';
export const T4 = 'var(--t4)';
export const F = 'var(--f)';
export const AC = 'var(--ac)';
export const ACS = 'var(--acs)';
export const ACI = 'var(--aci)';
export const SG = 'var(--sg)';
export const SGS = 'var(--sgs)';
export const R = 'var(--radius-sm)';
export const RL = 'var(--radius-md)';
export const RXL = 'var(--radius-lg)';
export const PB = 'var(--color-bg)';

export const mix = (c: string, pct: number, base = 'transparent') =>
  `color-mix(in srgb, ${c} ${pct}%, ${base})`;

/** The custom properties the root element carries for a palette. */
export function paletteVars(pal: Palette): CSSProperties {
  const vars: Record<string, string> = {
    '--g': pal.g,
    '--p': pal.p,
    '--e': pal.e,
    '--t1': pal.t1,
    '--t2': pal.t2,
    '--t3': pal.t3,
    '--t4': pal.t4,
    '--f': pal.f,
    '--ac': pal.ac,
    '--acs': pal.acs,
    '--aci': pal.aci,
    '--sg': pal.sg,
    '--sgs': pal.sgs,
    '--blur': '20px',
    '--glass': mix(pal.p, 66),
  };
  return vars as CSSProperties;
}

/** The frosted panel treatment every chrome surface shares. */
export function glassStyle(pal: Palette): CSSProperties {
  return {
    background: GL,
    backdropFilter: 'blur(var(--blur)) saturate(1.15)',
    WebkitBackdropFilter: 'blur(var(--blur)) saturate(1.15)',
    border: `1px solid ${mix(T1, pal.dark ? 14 : 0, E)}`,
    boxShadow: `inset 0 1px 0 ${mix(T1, pal.dark ? 10 : 40)}`,
  };
}

export const LEVEL_INK: Record<string, string> = { ok: SG, info: T3, warn: AC, err: AC };
