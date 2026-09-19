/**
 * Session state: who is signed in and in which mode. Everything the engine
 * reports lives in the cockpit store (src/cockpit/store.ts).
 */
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { AuthMode } from '../components/Login';

interface AppState {
  isAuthenticated: boolean;
  authMode: AuthMode | null;
  setAuthMode: (mode: AuthMode | null) => void;
  setAuthenticated: (isAuthenticated: boolean) => void;
  logout: () => void;
}

const AUTH_STORAGE_KEY = 'sentient_alpha_auth';

export const useStore = create<AppState>()(
  devtools(
    persist(
      (set) => ({
        isAuthenticated: false,
        authMode: null,
        setAuthMode: (mode) => {
          set({ authMode: mode });
          if (mode) {
            localStorage.setItem(`${AUTH_STORAGE_KEY}_mode`, mode);
          } else {
            localStorage.removeItem(`${AUTH_STORAGE_KEY}_mode`);
          }
        },
        setAuthenticated: (isAuthenticated) => set({ isAuthenticated }),
        logout: () => {
          set({ isAuthenticated: false, authMode: null });
          localStorage.removeItem(`${AUTH_STORAGE_KEY}_mode`);
        },
      }),
      {
        name: 'sentient-alpha-store',
        partialize: (state) => ({ authMode: state.authMode }),
      }
    )
  )
);

export const getStoredAuthMode = (): AuthMode | null => {
  const stored = localStorage.getItem(`${AUTH_STORAGE_KEY}_mode`);
  if (stored === 'demo' || stored === 'production') {
    return stored;
  }
  return null;
};
