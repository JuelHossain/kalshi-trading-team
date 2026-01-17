import { kalshiFetch } from '../../services/kalshiService';

export const fetchOrderBook = async (ticker: string, isPaperTrading: boolean) => {
    try {
        const data = await kalshiFetch(`/markets/${ticker}/orderbook`, 'GET', undefined, isPaperTrading);
        const yesBids = data.orderbook?.yes?.bids || [];
        const yesAsks = data.orderbook?.yes?.asks || [];

        return {
            yes_bid: yesBids.length > 0 ? yesBids[0][0] : 0,
            yes_ask: yesAsks.length > 0 ? yesAsks[0][0] : 99
        };
    } catch (e) {
        console.error(`[Agent 7] Orderbook Fetch Failed for ${ticker}`, e);
        throw e;
    }
}
