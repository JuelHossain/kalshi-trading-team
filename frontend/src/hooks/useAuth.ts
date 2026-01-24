import { useState, useEffect } from 'react';
import { CONFIG } from '../config';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || `http://${window.location.hostname}:3001`;

export const useAuth = (addLog: (msg: string, id: number, level: string) => void, isPaperTrading: boolean) => {
    // Fallback demo credentials if none provided in CONFIG
    const FALLBACK_DEMO_KEY = 'demo-key-id';
    const FALLBACK_DEMO_SECRET = '-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEAyDemoKeyForTestingPurposesOnly123456789ABCDEFGH\n-----END RSA PRIVATE KEY-----';

    const [apiKeyId, setApiKeyId] = useState(CONFIG.KALSHI.DEMO_KEY_ID || FALLBACK_DEMO_KEY);
    const [apiSecret, setApiSecret] = useState(CONFIG.KALSHI.DEMO_PRIVATE_KEY || FALLBACK_DEMO_SECRET);
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [isAuthenticating, setIsAuthenticating] = useState(false);
    const [authError, setAuthError] = useState<string | null>(null);

    const handleLogin = async (silent: boolean = false) => {
        if (!silent) setAuthError(null);
        setIsAuthenticating(true);

        if (!silent) addLog(`SYSTEM: Initiating V2 Handshake via Backend...`, 0, 'WARN');

        try {
            const authBody = isPaperTrading 
                ? { useSystemAuth: true, isPaperTrading: true }
                : { keyId: apiKeyId || FALLBACK_DEMO_KEY, privateKey: apiSecret || FALLBACK_DEMO_SECRET, isPaperTrading };

            const response = await fetch(`${BACKEND_URL}/api/auth`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(authBody)
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || 'Auth Failed');
            }

            setIsLoggedIn(true);
            if (!silent) addLog(`SYSTEM: V2 Secure Session Established.`, 0, 'SUCCESS');
        } catch (e: any) {
            if (!silent) setAuthError(e.message);
            setIsLoggedIn(false);
            if (!silent) addLog(`SYSTEM: Auth Failed - ${e.message}`, 0, 'ERROR');
        } finally {
            setIsAuthenticating(false);
        }
    };

    useEffect(() => {
        // Auto-login for Demo Mode (Paper Trading)
        if (isPaperTrading && !isLoggedIn && !isAuthenticating) {
            handleLogin(true);
        }
    }, [isPaperTrading]);

    return {
        apiKeyId,
        setApiKeyId,
        apiSecret,
        setApiSecret,
        isLoggedIn,
        isAuthenticating,
        authError,
        handleLogin
    };
};
