import { kalshiService } from '../../services/kalshiService';

export const fetchOrderBook = async (ticker: string, isPaperTrading: boolean) => {
  try {
    const data = await kalshiService.fetch(
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
    throw e;
  }
};

export const analyzeOrderBook = (
  book: { yes_bid: number; yes_ask: number },
  targetTicker: string
) => {
  // Protocol: The Silent Sniper
  const spread = book.yes_ask - book.yes_bid;

  console.log(`[Agent 7] Analyzing Orderbook for ${targetTicker}. Spread: ${spread}c`);

  // CRITICAL FIX #5: Hard veto on excessive spreads (changed from warning to rejection)
  if (spread > 10) {
    console.error(`[Agent 7] VETO: Spread too wide (${spread}c). Market is illiquid.`);
    return {
      snipePrice: 0,
      isLiquid: false,
      spread: spread,
      vetoed: true,
      vetoReason: `Spread (${spread}c) exceeds 10c threshold`,
    };
  }

  // Snipe Logic: 1 cent above high bid
  const snipePrice = book.yes_bid + 1;

  // Safety: Never snipe above the ask
  const finalPrice = Math.min(snipePrice, book.yes_ask);

  return {
    snipePrice: finalPrice,
    isLiquid: spread < 5,
    spread: spread,
    vetoed: false,
  };
};
