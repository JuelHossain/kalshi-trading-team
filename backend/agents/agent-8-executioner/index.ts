import { kalshiFetch } from '../../services/kalshiService';

export const calculateRiskParams = (
    balance: number,
    winProbability: number,
    odds: number // Decimal odds (e.g. 2.0 for 50/50 payout)
): { wager: number; maxLoss: number } => {
    // Agent 8 Module: Kelly Risk Engine

    // 1. Simple Kelly Criterion
    // f* = (bp - q) / b
    const b = odds - 1;
    const p = winProbability;
    const q = 1 - p;

    let kellyFraction = (b * p - q) / b;

    // 2. Fractional Kelly (Safety)
    // We use "Quarter Kelly" to reduce volatility
    const safetyFactor = 0.25;
    let safeFraction = kellyFraction * safetyFactor;

    // 3. Hard Limits
    if (safeFraction < 0) safeFraction = 0;
    if (safeFraction > 0.05) safeFraction = 0.05; // Cap at 5% of bankroll per trade

    const wager = Math.floor(balance * safeFraction);

    console.log(`[Agent 8] Risk Engine: Bal=$${balance}, P=${p.toFixed(2)}, Wager=$${wager}`);

    return {
        wager: wager,
        maxLoss: wager
    };
};

import { validateExecutionerSafety } from '../agent-14-qa-chaos/index';

export const createOrder = async (
    ticker: string,
    action: 'buy' | 'sell',
    count: number,
    side: 'yes' | 'no',
    price: number, // Silently snipe at this price
    isPaperTrading: boolean
) => {
    // Agent 14 Check: Verify Safety Protocols
    validateExecutionerSafety(isPaperTrading, isPaperTrading ? 'DEMO' : 'PROD');

    // Agent 8: The Executioner
    console.log(`[Agent 8] SNIPE: ${action.toUpperCase()} ${count}x ${ticker} ${side.toUpperCase()} @ ${price}c`);

    const orderBody = {
        action: action,
        count: count,
        side: side,
        ticker: ticker,
        type: 'limit', // PROTOCOL: The Silent Sniper
        yes_price: side === 'yes' ? price : 100 - price,
        client_order_id: `sentient_${Date.now()}`
    };

    try {
        const response = await kalshiFetch('/portfolio/orders', 'POST', orderBody, isPaperTrading);
        return response.order;
    } catch (e) {
        console.error(`[Agent 8] Snipe Failed for ${ticker}`, e);
        throw e;
    }
}

