import { CONFIG } from '../config';

// In-memory session storage for the runtime
let session: { token: string; memberId: string } | null = null;

export const isAuthenticated = () => !!session;

export const loginToKalshi = async (email: string, pass: string, isPaper: boolean) => {
    const baseUrl = isPaper ? CONFIG.KALSHI.SANDBOX_API : CONFIG.KALSHI.PROD_API;
    console.log(`[Kalshi Service] Authenticating with ${baseUrl}...`);

    try {
        const response = await fetch(`${baseUrl}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password: pass })
        });
        
        if (!response.ok) {
            if (response.status === 404) {
                 throw new Error(`Endpoint Not Found (404) at ${baseUrl}/login. Check Sandbox Availability.`);
            }
            const err = await response.json().catch(() => ({}));
            throw new Error(err.message || `Login Failed: ${response.status}`);
        }
        
        const data = await response.json();
        session = {
            token: data.token,
            memberId: data.member_id
        };
        console.log(`[Kalshi Service] Authenticated as Member: ${session.memberId}`);
        return true;
    } catch (e: any) {
        console.error("Kalshi Login Error:", e);
        session = null;
        throw e;
    }
}

export const fetchActiveMarkets = async (isPaperTrading: boolean) => {
  const baseUrl = isPaperTrading ? CONFIG.KALSHI.SANDBOX_API : CONFIG.KALSHI.PROD_API;
  
  const headers: Record<string, string> = {
    'Accept': 'application/json',
    'Content-Type': 'application/json'
  };

  if (session?.token) {
      headers['Authorization'] = `${session.token}`;
  } else {
      console.warn("[Kalshi Service] Fetching public markets without auth.");
  }

  try {
    const response = await fetch(`${baseUrl}/markets?limit=10&status=active`, {
      method: 'GET',
      headers: headers
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Kalshi API Error [${response.status}]: ${errorText}`);
    }

    const data = await response.json();
    return data.markets || [];
  } catch (error: any) {
    console.error("Kalshi Connection Failure:", error);
    throw error;
  }
};

export const fetchOrderBook = async (ticker: string, isPaperTrading: boolean) => {
    const baseUrl = isPaperTrading ? CONFIG.KALSHI.SANDBOX_API : CONFIG.KALSHI.PROD_API;
    
    if (!session?.token) {
        throw new Error("Authentication required for Order Book access.");
    }

    try {
        const response = await fetch(`${baseUrl}/markets/${ticker}/orderbook`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Authorization': `${session.token}`
            }
        });

        if (!response.ok) {
            throw new Error(`OrderBook Error [${response.status}]`);
        }

        const data = await response.json();
        return data.orderbook || {};
    } catch (error) {
        console.error("Fetch OrderBook Failed:", error);
        throw error;
    }
}

export const createOrder = async (
    ticker: string, 
    action: 'buy' | 'sell', 
    count: number, 
    side: 'yes' | 'no', 
    isPaperTrading: boolean
) => {
    const baseUrl = isPaperTrading ? CONFIG.KALSHI.SANDBOX_API : CONFIG.KALSHI.PROD_API;
    
    if (!session?.token) {
        throw new Error("Authentication required to place order.");
    }

    try {
        const response = await fetch(`${baseUrl}/portfolio/orders`, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'Authorization': `${session.token}`
            },
            body: JSON.stringify({
                ticker: ticker,
                action: action,
                type: 'market', // Using Market orders for speed in this Alpha
                count: count,
                side: side
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.message || `Order Failed: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error("Create Order Failed:", error);
        throw error;
    }
}
