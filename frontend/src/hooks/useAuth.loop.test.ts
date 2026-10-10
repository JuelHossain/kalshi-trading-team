import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAuth } from './useAuth';

// Uses the REAL store. useAuth.test.ts mocks it with plain functions that
// never trigger a re-render, which is why a verify loop went unnoticed:
// subscribing to the whole store meant every /auth/verify reply recreated
// verifyAuth and re-ran the mount effect -- 97 to 1,381 requests in two
// seconds from one open cockpit (2026-09-18 audit).
describe('useAuth against the real store', () => {
  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('verifies once on mount, not in a loop', async () => {
    localStorage.setItem('sentient_alpha_auth_mode', 'demo');
    const fetchMock = vi.fn(
      (_url: string) =>
        new Promise((resolve) =>
          setTimeout(
            () => resolve({ ok: true, json: () => Promise.resolve({ isAuthenticated: true, mode: 'demo' }) }),
            5
          )
        )
    );
    global.fetch = fetchMock as unknown as typeof fetch;

    renderHook(() => useAuth());
    await act(async () => {
      await new Promise((r) => setTimeout(r, 300));
    });

    const verifies = fetchMock.mock.calls.filter((c) => String(c[0]).includes('/auth/verify'));
    expect(verifies.length).toBe(1);
  });
});
