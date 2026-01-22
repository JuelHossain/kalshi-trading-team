import { CONFIG } from '../config';

/**
 * Demo Authentication Service
 * Professional implementation of demo credentials for development and testing
 * 
 * Security Principles:
 * 1. Demo credentials are clearly marked and separated from production
 * 2. Demo mode uses mock data and never touches real APIs
 * 3. Environment-based configuration prevents accidental production usage
 */

export interface DemoCredentials {
    keyId: string;
    privateKey: string;
    environment: 'demo' | 'production';
}

// Demo RSA Private Key (Generated for demo purposes only - NOT REAL)
const DEMO_PRIVATE_KEY = `-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAyDemoKeyForTestingPurposesOnly123456789ABCDEFGH
IJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/==
MIIEowIBAAKCAQEAyDemoKeyForTestingPurposesOnly123456789ABCDEFGH
IJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/==
MIIEowIBAAKCAQEAyDemoKeyForTestingPurposesOnly123456789ABCDEFGH
IJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/==
MIIEowIBAAKCAQEAyDemoKeyForTestingPurposesOnly123456789ABCDEFGH
IJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/==
MIIEowIBAAKCAQEAyDemoKeyForTestingPurposesOnly123456789ABCDEFGH
IJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/==
MIIEowIBAAKCAQEAyDemoKeyForTestingPurposesOnly123456789ABCDEFGH
IJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/==
MIIEowIBAAKCAQEAyDemoKeyForTestingPurposesOnly123456789ABCDEFGH
IJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/==
MIIEowIBAAKCAQEAyDemoKeyForTestingPurposesOnly123456789ABCDEFGH
-----END RSA PRIVATE KEY-----`;

/**
 * Get demo credentials from environment or use defaults
 */
export const getDemoCredentials = (): DemoCredentials => {
    return {
        keyId: CONFIG.KALSHI.DEMO_KEY_ID || 'demo-key-id',
        privateKey: DEMO_PRIVATE_KEY,
        environment: 'demo'
    };
};

/**
 * Validate if provided credentials are demo credentials
 * This allows the frontend to auto-login with demo credentials
 */
export const isDemoCredentials = (keyId: string, privateKey: string): boolean => {
    const demoKeyId = CONFIG.KALSHI.DEMO_KEY_ID || 'demo-key-id';
    
    // Check if it matches our demo key ID or common demo patterns
    const isDemoKeyId = keyId === demoKeyId || 
                        keyId === 'demo-key-id' || 
                        keyId.toLowerCase().includes('demo');
    
    // Check if private key is demo key or placeholder
    const isDemoKey = privateKey === DEMO_PRIVATE_KEY || 
                      privateKey === 'demo-private-key' ||
                      privateKey.includes('DemoKeyForTesting');
    
    return isDemoKeyId && isDemoKey;
};

/**
 * Authenticate with demo credentials
 * Returns mock session without calling real API
 */
export const authenticateDemo = async (): Promise<{
    success: boolean;
    session: {
        keyId: string;
        environment: 'demo';
        balance: number;
        isPaperTrading: true;
    };
}> => {
    console.log('[Demo Auth] Authenticating with demo credentials...');
    
    // Simulate API delay for realistic UX
    await new Promise(resolve => setTimeout(resolve, 500));
    
    const demoCredentials = getDemoCredentials();
    
    return {
        success: true,
        session: {
            keyId: demoCredentials.keyId,
            environment: 'demo',
            balance: 30000, // $300.00 in cents
            isPaperTrading: true
        }
    };
};

/**
 * Get demo market data
 * Returns realistic mock data for demo mode
 */
export const getDemoMarketData = () => {
    return [
        {
            ticker: 'NBA-LAL-BOS-2024',
            title: 'NBA: Lakers vs Celtics - Lakers Win',
            kalshi_prob: 0.52,
            vegas_prob: 0.58,
            delta: 0.06,
            volume: 42000,
            last_price: 52,
            type: 'SPORTS',
            status: 'active'
        },
        {
            ticker: 'NFL-KC-BAL-2024',
            title: 'NFL: Chiefs vs Ravens - Chiefs Win',
            kalshi_prob: 0.48,
            vegas_prob: 0.53,
            delta: 0.05,
            volume: 85000,
            last_price: 48,
            type: 'SPORTS',
            status: 'active'
        },
        {
            ticker: 'ECON-CPI-JAN-2024',
            title: 'US CPI > 3.2% in January',
            kalshi_prob: 0.22,
            vegas_prob: 0.25,
            delta: 0.03,
            volume: 12000,
            last_price: 22,
            type: 'ECON',
            status: 'active'
        },
        {
            ticker: 'WEATHER-NYC-SNOW',
            title: 'NYC Snowfall > 6 inches this week',
            kalshi_prob: 0.35,
            vegas_prob: 0.40,
            delta: 0.05,
            volume: 8500,
            last_price: 35,
            type: 'WEATHER',
            status: 'active'
        }
    ];
};

/**
 * Get demo balance
 */
export const getDemoBalance = () => {
    return {
        balance: 30000, // $300.00 in cents
        pnl: 0,
        available: 30000
    };
};

/**
 * Get demo orderbook
 */
export const getDemoOrderbook = (ticker: string) => {
    return {
        orderbook: {
            yes: {
                bids: [[48, 100], [47, 200], [46, 150]],
                asks: [[52, 100], [53, 150], [54, 200]]
            },
            no: {
                bids: [[48, 100], [47, 200]],
                asks: [[52, 100], [53, 150]]
            }
        }
    };
};

export default {
    getDemoCredentials,
    isDemoCredentials,
    authenticateDemo,
    getDemoMarketData,
    getDemoBalance,
    getDemoOrderbook
};
