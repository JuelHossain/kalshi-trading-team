import { kalshiFetch } from '../../services/kalshiService';
import { fastClassify } from '../../services/aiService';

interface HarvesterMarket {
    ticker: string;
    title: string;
    last_price: number;
    volume: number;
    category: string;
}

export const fetchScoutedMarkets = async (isPaperTrading: boolean) => {
    console.log(`[Agent 2] Scout: Scanning via V2 API...`);

    try {
        // 1. Fetch from Kalshi
        // Using strict hard-coded filters here for efficiency
        const data = await kalshiFetch('/markets?limit=100&status=active', 'GET', undefined, isPaperTrading);
        const rawMarkets = data.markets || [];

        // 2. Filter Logic (Liquidity & Open Interest)
        // Hard-coded: Volume > 100 contracts, Open Interest > $2000 (approx)
        const candidates = rawMarkets.filter((m: any) => m.volume > 100 && (m.open_interest || 0) > 2000);

        console.log(`[Agent 2] Found ${candidates.length} candidates after liquidity filter.`);

        // 3. AI Categorization (Parallel)
        const processed = await Promise.all(candidates.map(async (m: any) => {
            // Speed Optimization: Only classify if category is generic/unknown, otherwise use default
            // But we want to separate Sports vs Econ vs Weather vs Politics
            // Kalshi 'category' field is often good enough, but let's refine it.

            let category = m.category;
            // Reflex to AI if "Politics" or "Economics" to distinguish subtypes if needed
            // For now, let's trust Kalshi category to save latency, UNLESS it's "Other"
            if (!category || category === 'Other') {
                category = await fastClassify(m.title, ['Sports', 'Economics', 'Politics', 'Weather', 'Culture']);
            }

            return {
                ticker: m.ticker,
                title: m.title,
                kalshi_prob: (m.last_price || 50) / 100,
                vegas_prob: 0.50, // Agent 3 will fill this
                delta: 0,
                volume: m.volume,
                type: category
            };
        }));

        return processed;

    } catch (e) {
        console.error("[Agent 2] Scout Scan Failed.", e);
        // Fallback Mock
        return [];
    }
};
