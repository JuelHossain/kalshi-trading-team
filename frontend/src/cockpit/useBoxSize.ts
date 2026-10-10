/**
 * Measures an element for the orrery. ResizeObserver plus a double
 * requestAnimationFrame re-measure after mount: the first observed box is
 * often a pre-layout value, and geometry computed from it bottoms the
 * bodies out at their floor. 2px change threshold, per the geometry module.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

export interface Box {
  w: number;
  h: number;
}

export function useBoxSize(initial: Box = { w: 680, h: 400 }) {
  const [box, setBox] = useState<Box>(initial);
  const elRef = useRef<HTMLElement | null>(null);
  const roRef = useRef<ResizeObserver | null>(null);

  const measure = useCallback(() => {
    const el = elRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const w = Math.max(240, Math.floor(r.width));
    const h = Math.max(170, Math.floor(r.height));
    setBox((b) => (Math.abs(w - b.w) > 2 || Math.abs(h - b.h) > 2 ? { w, h } : b));
  }, []);

  const ref = useCallback(
    (el: HTMLElement | null) => {
      if (roRef.current) {
        roRef.current.disconnect();
        roRef.current = null;
      }
      elRef.current = el;
      if (!el) return;
      if (typeof ResizeObserver !== 'undefined') {
        roRef.current = new ResizeObserver(() => measure());
        roRef.current.observe(el);
      }
      measure();
    },
    [measure]
  );

  useEffect(() => {
    let raf2 = 0;
    const raf1 = requestAnimationFrame(() => {
      measure();
      raf2 = requestAnimationFrame(measure);
    });
    // A few late polls catch fonts and panels settling after first paint.
    const polls = [180, 360, 720, 1400].map((ms) => setTimeout(measure, ms));
    window.addEventListener('resize', measure);
    return () => {
      cancelAnimationFrame(raf1);
      cancelAnimationFrame(raf2);
      polls.forEach(clearTimeout);
      window.removeEventListener('resize', measure);
      roRef.current?.disconnect();
    };
  }, [measure]);

  return { box, ref };
}

export function useViewport() {
  const read = () => ({
    w: typeof window !== 'undefined' ? window.innerWidth : 1280,
    h: typeof window !== 'undefined' ? window.innerHeight : 820,
  });
  const [vp, setVp] = useState(read);
  useEffect(() => {
    const on = () => setVp(read());
    window.addEventListener('resize', on);
    return () => window.removeEventListener('resize', on);
  }, []);
  return vp;
}
