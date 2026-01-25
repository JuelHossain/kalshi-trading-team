import { useState, useEffect } from 'react';
import { CONFIG } from '../config';
import { useStore } from '../store/useStore';

const ENGINE_URL = 'http://localhost:3002';

export const useAuth = (
  addLog: (msg: string, id: number, level: string) => void,
  isPaperTrading: boolean
) => {
  const store = useStore();

  // Fallback demo credentials if none provided in CONFIG
  const FALLBACK_DEMO_KEY = 'demo-key-id';
  const FALLBACK_DEMO_SECRET =
    '-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEAyDemoKeyForTestingPurposesOnly123456789ABCDEFGH\n-----END RSA PRIVATE KEY-----';

  const [apiKeyId, setApiKeyId] = useState(CONFIG.KALSHI.DEMO_KEY_ID || FALLBACK_DEMO_KEY);
  const [apiSecret, setApiSecret] = useState(FALLBACK_DEMO_SECRET);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  const handleLogin = async (silent: boolean = false) => {
    if (!silent) setAuthError(null);
    setIsAuthenticating(true);

    if (!silent) addLog(`SYSTEM: Initiating V2 Handshake via Engine...`, 0, 'WARN');

    try {
      const authBody = isPaperTrading
        ? { useSystemAuth: true, isPaperTrading: true }
        : {
          keyId: apiKeyId || FALLBACK_DEMO_KEY,
          privateKey: apiSecret || FALLBACK_DEMO_SECRET,
          isPaperTrading,
        };

      const response = await fetch(`${ENGINE_URL}/auth`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(authBody),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Auth Failed');
      }

      const data = await response.json();
      if (data.isAuthenticated) {
        store.login(); // Update global store
        // We can also set user data if returned
        if (!silent) addLog(`SYSTEM: V2 Secure Session Established.`, 0, 'SUCCESS');
      } else {
        throw new Error('Authentication rejected by engine');
      }
    } catch (e: any) {
      if (!silent) setAuthError(e.message);
      store.logout();
      if (!silent) addLog(`SYSTEM: Auth Failed - ${e.message}`, 0, 'ERROR');
    } finally {
      setIsAuthenticating(false);
    }
  };

  useEffect(() => {
    // Auto-login for Demo Mode (Paper Trading)
    if (isPaperTrading && !store.isAuthenticated && !isAuthenticating) {
      handleLogin(true);
    }
  }, [isPaperTrading, store.isAuthenticated]);

  return {
    apiKeyId,
    setApiKeyId,
    apiSecret,
    setApiSecret,
    isLoggedIn: store.isAuthenticated,
    isAuthenticating,
    authError,
    handleLogin,
  };
};
