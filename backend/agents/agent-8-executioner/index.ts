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

export const createOrder = async (
    ticker: string,
    action: 'buy' | 'sell',
    count: number,
    side: 'yes' | 'no',
    isPaperTrading: boolean
) => {
    // Agent 8: The Executioner
    console.log(`[Agent 8] EXECUTION: ${action.toUpperCase()} ${count}x ${ticker} ${side.toUpperCase()}`);

    const orderBody = {
        action: action,
        count: count,
        side: side,
        ticker: ticker,
        type: 'market',
        client_order_id: `sentient_${Date.now()}`
    };

    try {
        const response = await kalshiFetch('/portfolio/orders', 'POST', orderBody, isPaperTrading);
        return response.order;
    } catch (e) {
        console.error(`[Agent 8] Execution Failed for ${ticker}`, e);
        throw e;
    }
}
