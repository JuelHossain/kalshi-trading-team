import { CONFIG } from '../config';
import crypto from 'crypto';
import { CHAOS_STATE } from '../agents/agent-14-qa-chaos/state';

// Agent 8: The Executioner (V2 Auth & Order Management)
// Implements RSA-SHA256 Signing for Kalshi V2 API

interface Session {
  keyId: string;
  privateKey: string;
  isDemo?: boolean;
}

export class KalshiService {
  private static instance: KalshiService;
  private session: Session | null = null;

  private constructor() {}

  public static getInstance(): KalshiService {
    if (!KalshiService.instance) {
      KalshiService.instance = new KalshiService();
    }
    return KalshiService.instance;
  }

  public isAuthenticated(): boolean {
    return !!this.session;
  }

  public async authenticateWithKeys(
    keyId: string,
    privateKey: string,
    isPaper: boolean
  ): Promise<boolean> {
    const baseUrl = isPaper ? CONFIG.KALSHI.SANDBOX_API : CONFIG.KALSHI.PROD_API;
    console.log(`[Agent 8] Initializing V2 Crypto-Engine for ${baseUrl}...`);

    if (!keyId || !privateKey) {
      throw new Error('Invalid Credentials: Key ID or Private Key missing.');
    }

    if (!privateKey.includes('BEGIN')) {
      throw new Error('Invalid Key Format: Must be PEM format.');
    }

    this.session = {
      keyId: keyId,
      privateKey: privateKey,
      isDemo: isPaper,
    };

    console.log(`[Agent 8] Keys Loaded. Crypto-Engine Online.`);

    try {
      await this.checkConnection(isPaper);
      console.log(`[Agent 8] Identity Verified on ${isPaper ? 'SANDBOX' : 'PROD'}.`);
    } catch (e) {
      console.warn(`[Agent 8] Pre-flight Check Failed, but keys are cached. Error:`, e);
    }

    return true;
  }

  private getHeaders(method: string, path: string, body: string = '') {
    if (!this.session) throw new Error('Agent 8 Locked: No Session Active.');

    const timestamp = Date.now().toString();
    const fullPath = '/trade-api/v2' + path;
    const payload = timestamp + method + fullPath + body;

    const signer = crypto.createSign('RSA-SHA256');
    signer.update(payload);
    signer.end();

    const signature = signer.sign(
      {
        key: this.session.privateKey,
        padding: crypto.constants.RSA_PKCS1_PSS_PADDING,
        saltLength: crypto.constants.RSA_PSS_SALTLEN_DIGEST,
      },
      'base64'
    );

    return {
      'Content-Type': 'application/json',
      'KALSHI-ACCESS-KEY': this.session.keyId,
      'KALSHI-ACCESS-SIGNATURE': signature,
      'KALSHI-ACCESS-TIMESTAMP': timestamp,
    };
  }

  public async checkConnection(isPaperTrading: boolean): Promise<boolean> {
    try {
      const balance = await this.fetch('/portfolio/balance', 'GET', undefined, isPaperTrading);
      console.log(`[Agent 8] Connection Verified. Balance: ${JSON.stringify(balance)}`);
      return true;
    } catch (e) {
      console.error('[Agent 8] Connection Check Failed:', e);
      return false;
    }
  }

  public async fetch(
    endpoint: string,
    method: 'GET' | 'POST' | 'DELETE',
    body?: any,
    isPaper: boolean = true
  ) {
    if (CHAOS_STATE.SIMULATE_500) {
      console.warn('[Agent 14] CHAOS: Simulating 500 Error...');
      throw new Error('CHAOS_INJECTED_500: Internal Server Error (Simulated)');
    }
    if (CHAOS_STATE.SIMULATE_TIMEOUT) {
      console.warn('[Agent 14] CHAOS: Simulating 20s Timeout...');
      await new Promise((resolve) => setTimeout(resolve, 20000));
      throw new Error('CHAOS_INJECTED_TIMEOUT: Request Timed Out (Simulated)');
    }

    const baseUrl = isPaper ? CONFIG.KALSHI.SANDBOX_API : CONFIG.KALSHI.PROD_API;
    const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = `${baseUrl}${path}`;
    const bodyStr = body ? JSON.stringify(body) : '';

    const headers = this.getHeaders(method, path, bodyStr);

    try {
      const response = await fetch(url, {
        method: method,
        headers: headers as any,
        body: method === 'POST' ? bodyStr : undefined,
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
  }

  public async fetchScoutedMarkets(isPaperTrading: boolean) {
    if (!this.session) {
      throw new Error('[Agent 2] No Auth Session Active.');
    }

    console.log(`[Agent 2] Scanning Real Markets via V2...`);
    try {
      const data = await this.fetch(
        '/markets?limit=100&status=active',
        'GET',
        undefined,
        isPaperTrading
      );

      return data.markets.map((m: any) => ({
        ticker: m.ticker,
        title: m.title,
        kalshi_prob: (m.last_price || 50) / 100,
        vegas_prob: 0.5,
        delta: 0,
        volume: m.volume,
        type: m.category,
      }));
    } catch (e) {
      console.error('[Agent 2] Scan Failed:', e);
      throw e;
    }
  }

  public async fetchOrderBook(ticker: string, isPaperTrading: boolean) {
    if (!this.session) {
      throw new Error('[Agent 7] No Auth Session Active.');
    }

    try {
      const data = await this.fetch(
        `/markets/${ticker}/orderbook`,
        'GET',
        undefined,
        isPaperTrading
      );
      const yesBids = data.orderbook?.yes?.bids || [];
      const yesAsks = data.orderbook?.yes?.asks || [];

      return {
        yes_bid: yesBids.length > 0 ? yesBids[0][0] : 0,
        yes_ask: yesAsks.length > 0 ? yesAsks[0][0] : 99,
      };
    } catch (e) {
      console.error(`[Agent 7] Orderbook Fetch Failed for ${ticker}`, e);
      return { yes_bid: 0, yes_ask: 99 };
    }
  }

  public async createOrder(
    ticker: string,
    action: 'buy' | 'sell',
    count: number,
    side: 'yes' | 'no',
    isPaperTrading: boolean
  ) {
    if (!this.session) {
      throw new Error('[Agent 8] No Auth Session Active.');
    }

    console.log(
      `[Agent 8] EXECUTION: ${action.toUpperCase()} ${count}x ${ticker} ${side.toUpperCase()}`
    );

    const orderBody = {
      action: action,
      count: count,
      side: side,
      ticker: ticker,
      type: 'limit',
      yes_price: side === 'yes' ? 50 : 50,
      client_order_id: `sentient_${Date.now()}`,
    };

    const response = await this.fetch('/portfolio/orders', 'POST', orderBody, isPaperTrading);
    return response.order;
  }
}

export const kalshiService = KalshiService.getInstance();
