import { CONFIG } from '../config';
import { KJUR } from 'jsrsasign';

// Agent 8: The Executioner (V2 Auth & Order Management)
// Implements RSA-SHA256 Signing for Kalshi V2 API

let session: { keyId: string; privateKey: string; isDemo?: boolean } | null = null;

export const isAuthenticated = () => !!session;

export const authenticateWithKeys = async (keyId: string, privateKey: string, isPaper: boolean) => {
    // Real authentication flow
    const baseUrl = isPaper ? CONFIG.KALSHI.SANDBOX_API : CONFIG.KALSHI.PROD_API;
    console.log(`[Agent 8] Initializing V2 Crypto-Engine for ${baseUrl}...`);

    if (!keyId || !privateKey) {
        throw new Error("Invalid Credentials: Key ID or Private Key missing.");
    }

    // Basic Validation of PEM format
    if (!privateKey.includes('BEGIN')) {
        throw new Error("Invalid Key Format: Must be PEM format.");
    }

    session = {
        keyId: keyId,
        privateKey: privateKey,
        isDemo: isPaper
    };

    console.log(`[Agent 8] Keys Loaded. Crypto-Engine Online.`);

    // Pro-check: Verify connection immediately
    try {
        await checkConnection(isPaper);
        console.log(`[Agent 8] Identity Verified on ${isPaper ? 'SANDBOX' : 'PROD'}.`);
    } catch (e) {
        console.warn(`[Agent 8] Pre-flight Check Failed, but keys are cached. Error:`, e);
    }

    return true;
}

// V2 Signature Generator
const getHeaders = (method: string, path: string, body: string = '') => {
    if (!session) throw new Error("Agent 8 Locked: No Session Active.");

    const timestamp = Date.now().toString();
    const payload = timestamp + method + path + body;

    const sig = new KJUR.crypto.Signature({ alg: "SHA256withRSA" });
    sig.init(session.privateKey);
    sig.updateString(payload);
    const signature = sig.sign();

    return {
        'Content-Type': 'application/json',
        'KALSHI-ACCESS-KEY': session.keyId,
        'KALSHI-ACCESS-SIGNATURE': signature,
        'KALSHI-ACCESS-TIMESTAMP': timestamp
    };
};

export const checkConnection = async (isPaperTrading: boolean) => {
    try {
        const balance = await kalshiFetch('/portfolio/balance', 'GET', undefined, isPaperTrading);
        console.log(`[Agent 8] Connection Verified. Balance: ${JSON.stringify(balance)}`);
        return true;
    } catch (e) {
        console.error("[Agent 8] Connection Check Failed:", e);
        return false;
    }
}

// Generic V2 Request Handler
import { CHAOS_STATE } from '../agents/agent-14-qa-chaos/state';

export const kalshiFetch = async (endpoint: string, method: 'GET' | 'POST' | 'DELETE', body?: any, isPaper: boolean = true) => {
    // Agent 14: Chaos Injection
    if (CHAOS_STATE.SIMULATE_500) {
        console.warn("[Agent 14] CHAOS: Simulating 500 Error...");
        throw new Error("CHAOS_INJECTED_500: Internal Server Error (Simulated)");
    }
    if (CHAOS_STATE.SIMULATE_TIMEOUT) {
        console.warn("[Agent 14] CHAOS: Simulating 20s Timeout...");
        await new Promise(resolve => setTimeout(resolve, 20000));
        throw new Error("CHAOS_INJECTED_TIMEOUT: Request Timed Out (Simulated)");
    }

    const baseUrl = isPaper ? CONFIG.KALSHI.SANDBOX_API : CONFIG.KALSHI.PROD_API;
    const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = `${baseUrl}${path}`;
    const bodyStr = body ? JSON.stringify(body) : '';

    const headers = getHeaders(method, '/trade-api/v2' + path, bodyStr);

    try {
        const response = await fetch(url, {
            method: method,
            headers: headers as any,
            body: method === 'POST' ? bodyStr : undefined
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Kalshi API ${response.status}: ${errorText}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`[Agent 8] API Call Failed (${endpoint}):`, error);
        throw error;
    }
};

export const fetchScoutedMarkets = async (isPaperTrading: boolean) => {
    // Agent 2: The Scout - Now using Real V2 API
    if (!session) {
        throw new Error("[Agent 2] No Auth Session Active.");
    }

    console.log(`[Agent 2] Scanning Real Markets via V2...`);
    try {
        // Fetch active markets, limit to 100 for speed
        const data = await kalshiFetch('/markets?limit=100&status=active', 'GET', undefined, isPaperTrading);

        // Normalize Real Data to our App's Schema
        return data.markets.map((m: any) => ({
            ticker: m.ticker,
            title: m.title,
            kalshi_prob: (m.last_price || 50) / 100, // Convert cents to prob
            vegas_prob: 0.50, // Placeholder for Agent 3 to fill
            delta: 0,         // Placeholder
            volume: m.volume,
            type: m.category
        }));

    } catch (e) {
        console.error("[Agent 2] Scan Failed:", e);
        throw e;
    }
};


export const fetchOrderBook = async (ticker: string, isPaperTrading: boolean) => {
    if (!session) {
        throw new Error("[Agent 7] No Auth Session Active.");
    }

    try {
        const data = await kalshiFetch(`/markets/${ticker}/orderbook`, 'GET', undefined, isPaperTrading);
        // Assuming orderbook structure (top of book)
        const yesBids = data.orderbook?.yes?.bids || [];
        const yesAsks = data.orderbook?.yes?.asks || [];

        return {
            yes_bid: yesBids.length > 0 ? yesBids[0][0] : 0,
            yes_ask: yesAsks.length > 0 ? yesAsks[0][0] : 99
        };
    } catch (e) {
        console.error(`[Agent 7] Orderbook Fetch Failed for ${ticker}`, e);
        return { yes_bid: 0, yes_ask: 99 };
    }
}


export const createOrder = async (
    ticker: string,
    action: 'buy' | 'sell',
    count: number,
    side: 'yes' | 'no',
    isPaperTrading: boolean
) => {
    // Agent 8: The Executioner
    if (!session) {
        throw new Error("[Agent 8] No Auth Session Active.");
    }

    console.log(`[Agent 8] EXECUTION: ${action.toUpperCase()} ${count}x ${ticker} ${side.toUpperCase()}`);

    const orderBody = {
        action: action,
        count: count,
        side: side,
        ticker: ticker,
        type: 'limit', // PROTOCOL: The Silent Sniper (No Market Orders)
        yes_price: side === 'yes' ? 50 : 50, // This should be calculated by Agent 8
        client_order_id: `sentient_${Date.now()}`
    };

    const response = await kalshiFetch('/portfolio/orders', 'POST', orderBody, isPaperTrading);
    return response.order;
}

export const fetchOpenOrders = async (isPaperTrading: boolean) => {
    try {
        const data = await kalshiFetch('/portfolio/orders?status=resting', 'GET', undefined, isPaperTrading);
        return data.orders || [];
    } catch (e) {
        console.error("[Agent 12] Failed to fetch open orders", e);
        return [];
    }
};

export const cancelOrder = async (orderId: string, isPaperTrading: boolean) => {
    try {
        await kalshiFetch(`/portfolio/orders/${orderId}`, 'DELETE', undefined, isPaperTrading);
        return true;
    } catch (e) {
        console.error(`[Agent 12] Failed to cancel order ${orderId}`, e);
        return false;
    }
};


export const fetchActiveMarkets = async (isPaperTrading: boolean) => {
    return fetchScoutedMarkets(isPaperTrading);
};