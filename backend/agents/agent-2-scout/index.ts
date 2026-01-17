import { kalshiFetch } from '../../services/kalshiService';

export const fetchScoutedMarkets = async (isPaperTrading: boolean) => {
    // Agent 2: The Scout - Now using Real V2 API
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
        console.error("[Agent 2] Scan Failed.", e);
        throw e; // No Mock Fallback
    }
};
