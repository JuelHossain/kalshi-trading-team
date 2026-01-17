import { useState, useEffect } from 'react';
import { CONFIG } from '../config';
import { authenticateWithKeys } from '../services/kalshiService';

export const useAuth = (addLog: (msg: string, id: number, level: string) => void, isPaperTrading: boolean) => {
    const [apiKeyId, setApiKeyId] = useState(CONFIG.KALSHI.KEY_ID || '');
    const [apiSecret, setApiSecret] = useState(CONFIG.KALSHI.PRIVATE_KEY || '');
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [authError, setAuthError] = useState<string | null>(null);

    const handleLogin = async () => {
        setAuthError(null);
        addLog(`SYSTEM: Initiating V2 Handshake...`, 0, 'WARN');
        try {
            await authenticateWithKeys(apiKeyId, apiSecret, isPaperTrading);
            setIsLoggedIn(true);
            addLog(`SYSTEM: V2 Secure Session Established.`, 0, 'SUCCESS');
        } catch (e: any) {
            setAuthError(e.message);
            setIsLoggedIn(false);
            addLog(`SYSTEM: Auth Failed - ${e.message}`, 0, 'ERROR');
        }
    };

    useEffect(() => {
        if (CONFIG.KALSHI.KEY_ID && CONFIG.KALSHI.PRIVATE_KEY && !isLoggedIn) {
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
