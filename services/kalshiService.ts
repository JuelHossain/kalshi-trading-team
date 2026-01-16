import { CONFIG } from '../config';

// In-memory session storage for the runtime (Mocking V2 signed client state)
let session: { keyId: string; secret: string } | null = null;

export const isAuthenticated = () => !!session;

export const authenticateWithKeys = async (keyId: string, secret: string, isPaper: boolean) => {
    const baseUrl = isPaper ? CONFIG.KALSHI.SANDBOX_API : CONFIG.KALSHI.PROD_API;
    console.log(`[Kalshi Service V2] Initializing Signed Client for ${baseUrl}...`);

    await new Promise(resolve => setTimeout(resolve, 800));

    if (!keyId || !secret) {
        throw new Error("Invalid Credentials provided.");
    }

    session = {
        keyId: keyId,
        secret: secret
    };
    
    console.log(`[Kalshi Service V2] Keys Loaded. Ready to Sign.`);
    return true;
}

// "Wide Net" Simulation Data
const getScoutedMarkets = () => [
    { 
        ticker: 'NBA-LAL-BOS', 
        title: 'NBA: Lakers vs Celtics', 
        kalshi_prob: 0.52,
        vegas_prob: 0.58,
        delta: 0.06, // +6% Edge
        volume: 42000,
        type: 'SPORTS'
    },
    { 
        ticker: 'NFL-KC-BAL', 
        title: 'NFL: Chiefs vs Ravens', 
        kalshi_prob: 0.48, 
        vegas_prob: 0.53,
        delta: 0.05, // +5% Edge
        volume: 85000, 
        type: 'SPORTS'
    },
    { 
        ticker: 'ECON-CPI-SEP', 
        title: 'US CPI > 3.2%', 
        kalshi_prob: 0.22, 
        vegas_prob: 0.25,
        delta: 0.03, // +3% Edge
        volume: 12000, 
        type: 'ECON'
    },
    { 
        ticker: 'POL-SEN-OH', 
        title: 'Senate Control: Ohio', 
        kalshi_prob: 0.45, 
        vegas_prob: 0.46,
        delta: 0.01, // +1% Edge (Low)
        volume: 150000, 
        type: 'POLITICS'
    },
    { 
        ticker: 'WX-NYC-RAIN', 
        title: 'Rain in NYC > 1in', 
        kalshi_prob: 0.10, 
        vegas_prob: 0.11,
        delta: 0.01, // Low Edge
        volume: 5000, 
        type: 'WEATHER'
    }
];

export const fetchActiveMarkets = async (isPaperTrading: boolean) => {
   // Legacy support for single-market fetch if needed
   return getScoutedMarkets();
};

export const fetchScoutedMarkets = async (isPaperTrading: boolean) => {
  // Simulates the "Wide Net" Stage: Fetching 100+ markets and checking odds
  await new Promise(resolve => setTimeout(resolve, 1000)); // Latency sim
  return getScoutedMarkets();
};

export const fetchOrderBook = async (ticker: string, isPaperTrading: boolean) => {
    await new Promise(resolve => setTimeout(resolve, 400));
    return {
        yes_bid: Math.floor(Math.random() * 50) + 10,
        yes_ask: Math.floor(Math.random() * 50) + 50
    };
}

export const createOrder = async (
    ticker: string, 
    action: 'buy' | 'sell', 
    count: number, 
    side: 'yes' | 'no', 
    isPaperTrading: boolean
) => {
    await new Promise(resolve => setTimeout(resolve, 1000));
    return {
        order_id: `ord_${Math.random().toString(36).substring(7)}`,
        status: 'executed',
        filled_count: count
    };
}