import { CONFIG } from '../config';
import { KJUR } from 'jsrsasign';

// Agent 8: The Executioner (V2 Auth & Order Management)
// Implements RSA-SHA256 Signing for Kalshi V2 API

let session: { keyId: string; privateKey: string } | null = null;

export const isAuthenticated = () => !!session;

export const authenticateWithKeys = async (keyId: string, privateKey: string, isPaper: boolean) => {
    const baseUrl = isPaper ? CONFIG.KALSHI.SANDBOX_API : CONFIG.KALSHI.PROD_API;
    console.log(`[Agent 8] Initializing V2 Crypto-Engine for ${baseUrl}...`);

    if (!keyId || !privateKey) {
        throw new Error("Invalid Credentials: Key ID or Private Key missing.");
    }

    // Basic Validation of PEM format
    if (!privateKey.includes('BEGIN RSA PRIVATE KEY')) {
        throw new Error("Invalid Key Format: Must be PEM (RSA PRIVATE KEY).");
    }

    session = {
        keyId: keyId,
        privateKey: privateKey
    };

    console.log(`[Agent 8] Keys Loaded. Crypto-Engine Online.`);
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

// Generic V2 Request Handler
// Generic V2 Request Handler
export const kalshiFetch = async (endpoint: string, method: 'GET' | 'POST' | 'DELETE', body?: any, isPaper: boolean = true) => {
    const baseUrl = isPaper ? CONFIG.KALSHI.SANDBOX_API : CONFIG.KALSHI.PROD_API;
    // Remove /trade-api/v2 from base if present to ensure path correctness, 
    // assuming CONFIG.KALSHI.*_API includes the version path. 
    // V2 Docs typically say: Base URL + Path.
    // e.g. Path is /markets

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
        console.warn("[Agent 2] No Auth Session. Returning Mock Protocol.");
        return getMockMarkets();
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
        console.error("[Agent 2] Scan Failed. Fallback to Mock.", e);
        return getMockMarkets();
    }
};

export const fetchOrderBook = async (ticker: string, isPaperTrading: boolean) => {
    if (!session) {
        return { yes_bid: 10, yes_ask: 50 }; // Mock
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
        console.log("[Agent 8] Mock Execution (No Session).");
        await new Promise(r => setTimeout(r, 1000));
        return { status: 'executed', filled_count: count, order_id: 'mock_ord_123' };
    }

    console.log(`[Agent 8] EXECUTION: ${action.toUpperCase()} ${count}x ${ticker} ${side.toUpperCase()}`);

    const orderBody = {
        action: action,
        count: count,
        side: side,
        ticker: ticker,
        type: 'market', // Aggressive execution
        client_order_id: `sentient_${Date.now()}`
    };

    const response = await kalshiFetch('/portfolio/orders', 'POST', orderBody, isPaperTrading);
    return response.order;
}

export const fetchActiveMarkets = async (isPaperTrading: boolean) => {
    return fetchScoutedMarkets(isPaperTrading);
};

// Fallback Mock Data
const getMockMarkets = () => [
    { ticker: 'NBA-LAL-BOS', title: 'NBA: Lakers vs Celtics', kalshi_prob: 0.52, vegas_prob: 0.58, delta: 0.06, volume: 42000, type: 'SPORTS' },
    { ticker: 'NFL-KC-BAL', title: 'NFL: Chiefs vs Ravens', kalshi_prob: 0.48, vegas_prob: 0.53, delta: 0.05, volume: 85000, type: 'SPORTS' },
    { ticker: 'ECON-CPI-SEP', title: 'US CPI > 3.2%', kalshi_prob: 0.22, vegas_prob: 0.25, delta: 0.03, volume: 12000, type: 'ECON' }
];