import { useState, useEffect, useCallback } from 'react';
import { useStore, getStoredAuthMode } from '../store/useStore';
import { AuthMode } from '../components/Login';

const ENGINE_URL = '/api';

interface AuthResponse {
  isAuthenticated: boolean;
  mode?: AuthMode;
  error?: string;
}

export interface UseAuthReturn {
  // State
  isAuthenticated: boolean;
  authMode: AuthMode | null;
  isAuthenticating: boolean;
  authError: string | null;

  // Actions
  login: (mode: AuthMode, password?: string) => Promise<void>;
  verifyAuth: () => Promise<boolean>;
  logout: () => Promise<void>;
}

export const useAuth = (): UseAuthReturn => {
  const store = useStore();

  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  /**
   * Login with the specified mode and optional password
   */
  const login = useCallback(
    async (mode: AuthMode, password?: string): Promise<void> => {
      setAuthError(null);
      setIsAuthenticating(true);

      try {
        console.log('[Auth] Attempting login for mode:', mode);
        const response = await fetch(`${ENGINE_URL}/auth/login`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify({
            mode,
            password: password || '',
          }),
        });

        console.log('[Auth] Response status:', response.status);
        console.log('[Auth] Response headers:', response.headers);

        // Clone response for debugging since we can only read body once
        const clonedResponse = response.clone();

        // Check if response body is empty
        const text = await clonedResponse.text();
        console.log('[Auth] Response body:', text);

        if (!text) {
          throw new Error('Empty response from server');
        }

        const data: AuthResponse = JSON.parse(text);

        if (!response.ok || !data.isAuthenticated) {
          throw new Error(data.error || 'Authentication failed');
        }

        // Update store with auth state
        store.setAuthMode(mode);
        store.setAuthenticated(true);

        console.log(`[Auth] Successfully logged in as ${mode} mode`);
      } catch (error: any) {
        console.error('[Auth] Login error:', error);
        const message = error.message || 'Failed to authenticate';
        setAuthError(message);
        store.setAuthenticated(false);
        throw error;
      } finally {
        setIsAuthenticating(false);
      }
    },
    [store]
  );

  /**
   * Verify the current authentication status with the server
   */
  const verifyAuth = useCallback(async (): Promise<boolean> => {
    try {
      const response = await fetch(`${ENGINE_URL}/auth/verify`, {
        method: 'GET',
        credentials: 'include',
      });

      if (!response.ok) {
        store.setAuthenticated(false);
        store.setAuthMode(null);
        return false;
      }

      const data: AuthResponse = await response.json();

      if (data.isAuthenticated) {
        store.setAuthenticated(true);
        // Use server-returned mode or fall back to stored mode
        const mode = data.mode || getStoredAuthMode();
        if (mode) {
          store.setAuthMode(mode);
        }
        return true;
      } else {
        store.setAuthenticated(false);
        store.setAuthMode(null);
        return false;
      }
    } catch (error) {
      console.error('[Auth] Verification failed:', error);
      store.setAuthenticated(false);
      return false;
    }
  }, [store]);

  /**
   * Logout the current user
   */
  const logout = useCallback(async (): Promise<void> => {
    try {
      await fetch(`${ENGINE_URL}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });
    } catch (error) {
      console.error('[Auth] Logout error:', error);
    } finally {
      // Always clear local state even if server request fails
      store.logout();
    }
  }, [store]);

  // Verify auth on mount
  useEffect(() => {
    // Check if we have a stored mode, verify with server
    const storedMode = getStoredAuthMode();
    if (storedMode) {
      verifyAuth();
    }
  }, [verifyAuth]);

  return {
    isAuthenticated: store.isAuthenticated,
    authMode: store.authMode,
    isAuthenticating,
    authError,
    login,
    verifyAuth,
    logout,
  };
};

export default useAuth;
