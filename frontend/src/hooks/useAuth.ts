import { useState, useEffect } from 'react';
import { CONFIG } from '../config';

const BACKEND_URL = 'http://localhost:3001';

export const useAuth = (addLog: (msg: string, id: number, level: string) => void, isPaperTrading: boolean) => {
    const [apiKeyId, setApiKeyId] = useState(CONFIG.KALSHI.DEMO_KEY_ID || CONFIG.KALSHI.PROD_KEY_ID || '');
    const [apiSecret, setApiSecret] = useState(CONFIG.KALSHI.DEMO_PRIVATE_KEY || CONFIG.KALSHI.PROD_PRIVATE_KEY || '');
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [authError, setAuthError] = useState<string | null>(null);

    const handleLogin = async () => {
        setAuthError(null);
        addLog(`SYSTEM: Initiating V2 Handshake via Backend...`, 0, 'WARN');
        try {
            const response = await fetch(`${BACKEND_URL}/api/auth`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    keyId: apiKeyId,
                    privateKey: apiSecret,
                    isPaperTrading
                })
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || 'Auth Failed');
            }

            setIsLoggedIn(true);
            addLog(`SYSTEM: V2 Secure Session Established.`, 0, 'SUCCESS');
        } catch (e: any) {
            setAuthError(e.message);
            setIsLoggedIn(false);
            addLog(`SYSTEM: Auth Failed - ${e.message}`, 0, 'ERROR');
        }
    };

    useEffect(() => {
        const keyId = CONFIG.KALSHI.DEMO_KEY_ID || CONFIG.KALSHI.PROD_KEY_ID;
        const privateKey = CONFIG.KALSHI.DEMO_PRIVATE_KEY || CONFIG.KALSHI.PROD_PRIVATE_KEY;
        if (keyId && privateKey && !isLoggedIn) {
            handleLogin();
        }
    }, [isPaperTrading]);

    return {
        apiKeyId,
        setApiKeyId,
        apiSecret,
        setApiSecret,
        isLoggedIn,
        authError,
        handleLogin
    };
};
