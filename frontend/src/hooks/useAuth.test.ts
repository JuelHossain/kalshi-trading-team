import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAuth } from './useAuth';

// Mock the store
const mockSetAuthenticated = vi.fn();
const mockSetAuthMode = vi.fn();
const mockLogout = vi.fn();
let mockIsAuthenticated = false;
let mockAuthMode: 'demo' | 'production' | null = null;

vi.mock('../store/useStore', () => ({
  useStore: () => ({
    isAuthenticated: mockIsAuthenticated,
    authMode: mockAuthMode,
    setAuthenticated: mockSetAuthenticated,
    setAuthMode: mockSetAuthMode,
    logout: mockLogout,
  }),
  getStoredAuthMode: () => mockAuthMode,
}));

describe('useAuth Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated = false;
    mockAuthMode = null;
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Initialization', () => {
    it('initializes with default values', () => {
      const { result } = renderHook(() => useAuth());

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.authMode).toBeNull();
      expect(result.current.isAuthenticating).toBe(false);
      expect(result.current.authError).toBeNull();
    });

    it('returns correct interface', () => {
      const { result } = renderHook(() => useAuth());

      expect(result.current).toHaveProperty('isAuthenticated');
      expect(result.current).toHaveProperty('authMode');
      expect(result.current).toHaveProperty('isAuthenticating');
      expect(result.current).toHaveProperty('authError');
      expect(result.current).toHaveProperty('login');
      expect(result.current).toHaveProperty('verifyAuth');
      expect(result.current).toHaveProperty('logout');
    });
  });

  describe('login - Demo Mode', () => {
    it('calls correct API endpoint for demo mode', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ isAuthenticated: true }),
      });
      global.fetch = mockFetch;

      const { result } = renderHook(() => useAuth());

      await act(async () => {
        await result.current.login('demo');
      });

      expect(mockFetch).toHaveBeenCalledWith('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          mode: 'demo',
          password: '',
        }),
      });
    });

    it('calls store.setAuthenticated and store.setAuthMode on success', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ isAuthenticated: true }),
      });
      global.fetch = mockFetch;

      const { result } = renderHook(() => useAuth());

      await act(async () => {
        await result.current.login('demo');
      });

      expect(mockSetAuthMode).toHaveBeenCalledWith('demo');
      expect(mockSetAuthenticated).toHaveBeenCalledWith(true);
    });

    it('does not set authError on successful login', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ isAuthenticated: true }),
      });
      global.fetch = mockFetch;

      const { result } = renderHook(() => useAuth());

      await act(async () => {
        await result.current.login('demo');
      });

      expect(result.current.authError).toBeNull();
    });
  });

  describe('login - Production Mode', () => {
    it('calls correct API endpoint with password for production', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ isAuthenticated: true }),
      });
      global.fetch = mockFetch;

      const { result } = renderHook(() => useAuth());

      await act(async () => {
        await result.current.login('production', '993728');
      });

      expect(mockFetch).toHaveBeenCalledWith('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          mode: 'production',
          password: '993728',
        }),
      });
    });

    it('calls store.setAuthenticated and store.setAuthMode on success', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ isAuthenticated: true }),
      });
      global.fetch = mockFetch;

      const { result } = renderHook(() => useAuth());

      await act(async () => {
        await result.current.login('production', '993728');
      });

      expect(mockSetAuthMode).toHaveBeenCalledWith('production');
      expect(mockSetAuthenticated).toHaveBeenCalledWith(true);
    });
  });

  describe('login - Error Handling', () => {
    it('sets authError on failed login', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ error: 'Invalid credentials' }),
      });
      global.fetch = mockFetch;

      const { result } = renderHook(() => useAuth());

      await act(async () => {
        try {
          await result.current.login('production', 'wrong-password');
        } catch (e) {
          // Expected to throw
        }
      });

      expect(result.current.authError).toBe('Invalid credentials');
    });

    it('calls store.setAuthenticated(false) on failed login', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ error: 'Auth Failed' }),
      });
      global.fetch = mockFetch;

      const { result } = renderHook(() => useAuth());

      await act(async () => {
        try {
          await result.current.login('production', 'wrong-password');
        } catch (e) {
          // Expected to throw
        }
      });

      expect(mockSetAuthenticated).toHaveBeenCalledWith(false);
    });

    it('handles network errors gracefully', async () => {
      const mockFetch = vi.fn().mockRejectedValue(new Error('Network request failed'));
      global.fetch = mockFetch;

      const { result } = renderHook(() => useAuth());

      await act(async () => {
        try {
          await result.current.login('demo');
        } catch (e) {
          // Expected to throw
        }
      });

      expect(result.current.authError).toBe('Network request failed');
      expect(mockSetAuthenticated).toHaveBeenCalledWith(false);
    });

    it('throws error on failed login', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ error: 'Authentication failed' }),
      });
      global.fetch = mockFetch;

      const { result } = renderHook(() => useAuth());

      await expect(result.current.login('demo')).rejects.toThrow('Authentication failed');
    });
  });

  describe('login - Loading States', () => {
    it('sets isAuthenticating to true during login', async () => {
      let resolveJson: (value: any) => void;
      const jsonPromise = new Promise((resolve) => {
        resolveJson = resolve;
      });

      const mockFetch = vi.fn().mockReturnValue({
        ok: true,
        json: () => jsonPromise,
      });
      global.fetch = mockFetch;

      const { result } = renderHook(() => useAuth());

      act(() => {
        result.current.login('demo');
      });

      expect(result.current.isAuthenticating).toBe(true);

      await act(async () => {
        resolveJson!({ isAuthenticated: true });
      });

      expect(result.current.isAuthenticating).toBe(false);
    });

    it('clears authError at start of new login attempt', async () => {
      const mockFetch = vi
        .fn()
        .mockRejectedValueOnce(new Error('First error'))
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ isAuthenticated: true }),
        });
      global.fetch = mockFetch;

      const { result } = renderHook(() => useAuth());

      await act(async () => {
        try {
          await result.current.login('demo');
        } catch (e) {
          // Expected
        }
      });

      expect(result.current.authError).toBe('First error');

      await act(async () => {
        await result.current.login('demo');
      });

      expect(result.current.authError).toBeNull();
    });
  });

  describe('verifyAuth', () => {
    it('returns true when user is authenticated', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ isAuthenticated: true, mode: 'demo' }),
      });
      global.fetch = mockFetch;

      const { result } = renderHook(() => useAuth());

      let verifyResult: boolean = false;
      await act(async () => {
        verifyResult = await result.current.verifyAuth();
      });

      expect(verifyResult).toBe(true);
      expect(mockSetAuthenticated).toHaveBeenCalledWith(true);
      expect(mockSetAuthMode).toHaveBeenCalledWith('demo');
    });

    it('returns false when user is not authenticated', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ isAuthenticated: false }),
      });
      global.fetch = mockFetch;

      const { result } = renderHook(() => useAuth());

      let verifyResult: boolean = true;
      await act(async () => {
        verifyResult = await result.current.verifyAuth();
      });

      expect(verifyResult).toBe(false);
      expect(mockSetAuthenticated).toHaveBeenCalledWith(false);
      expect(mockSetAuthMode).toHaveBeenCalledWith(null);
    });

    it('handles server error', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
      });
      global.fetch = mockFetch;

      const { result } = renderHook(() => useAuth());

      let verifyResult: boolean = true;
      await act(async () => {
        verifyResult = await result.current.verifyAuth();
      });

      expect(verifyResult).toBe(false);
      expect(mockSetAuthenticated).toHaveBeenCalledWith(false);
    });

    it('handles network error', async () => {
      const mockFetch = vi.fn().mockRejectedValue(new Error('Network error'));
      global.fetch = mockFetch;

      const { result } = renderHook(() => useAuth());

      let verifyResult: boolean = true;
      await act(async () => {
        verifyResult = await result.current.verifyAuth();
      });

      expect(verifyResult).toBe(false);
      expect(mockSetAuthenticated).toHaveBeenCalledWith(false);
    });
  });

  describe('logout', () => {
    it('calls logout endpoint', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
      });
      global.fetch = mockFetch;

      const { result } = renderHook(() => useAuth());

      await act(async () => {
        await result.current.logout();
      });

      expect(mockFetch).toHaveBeenCalledWith('/api/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
    });

    it('calls store.logout even on server error', async () => {
      const mockFetch = vi.fn().mockRejectedValue(new Error('Server error'));
      global.fetch = mockFetch;

      const { result } = renderHook(() => useAuth());

      await act(async () => {
        await result.current.logout();
      });

      expect(mockLogout).toHaveBeenCalled();
    });

    it('always clears local state', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
      });
      global.fetch = mockFetch;

      const { result } = renderHook(() => useAuth());

      await act(async () => {
        await result.current.logout();
      });

      expect(mockLogout).toHaveBeenCalled();
    });
  });

  describe('Auto-verify on mount', () => {
    it('verifies auth when stored mode exists', async () => {
      mockAuthMode = 'demo';

      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ isAuthenticated: true, mode: 'demo' }),
      });
      global.fetch = mockFetch;

      renderHook(() => useAuth());

      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 10));
      });

      expect(mockFetch).toHaveBeenCalledWith('/api/auth/verify', {
        method: 'GET',
        credentials: 'include',
      });
    });

    it('does not verify auth when no stored mode', async () => {
      mockAuthMode = null;

      const mockFetch = vi.fn();
      global.fetch = mockFetch;

      renderHook(() => useAuth());

      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 10));
      });

      expect(mockFetch).not.toHaveBeenCalled();
    });
  });
});
