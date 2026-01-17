import asyncio
from typing import Dict, Any, Optional
from pydantic import BaseModel
from agents.base import BaseAgent
from core.bus import EventBus
from core.network import kalshi_client
from colorama import Fore, Style

class SnipeAnalysis(BaseModel):
    ticker: str
    snipe_price: int
    spread: int
    is_liquid: bool
    bid: int
    ask: int

class SniperAgent(BaseAgent):
    """
    Agent 7: The Sniper (Orderbook Analyst)
    Role: Precise Price Targeting & Liquidity Guard.
    """
    
    async def setup(self):
        await self.log("Sniper initialized and listening for Intercept Data.")
        await self.bus.subscribe("INTERCEPT_DATA", self.handle_snipe_request)

    async def handle_snipe_request(self, message):
        ticker = message.payload.get('ticker')
        if not ticker:
            return

        await self.log(f"Analyzing Depth for {ticker}...")
        
        book_data = await kalshi_client.get_orderbook(ticker)
        if book_data:
            book = book_data.get('orderbook', {})
            yes_bids = book.get('yes', {}).get('bids', [])
            yes_asks = book.get('yes', {}).get('asks', [])
            
            bid = yes_bids[0][0] if yes_bids else 0
            ask = yes_asks[0][0] if yes_asks else 99
            
            analysis = self.analyze_orderbook(ticker, bid, ask)
            await self.log(f"Snipe Price Calculated: {analysis.snipe_price}c (Spread: {analysis.spread}c)")
            
            await self.bus.publish("SNIPE_ANALYSIS", analysis.model_dump(), self.name)

    def analyze_orderbook(self, ticker: str, bid: int, ask: int) -> SnipeAnalysis:
        spread = ask - bid
        
        # Snipe Logic: 1 cent above bid
        snipe_price = bid + 1
        
        # Guard: Never snipe above ask
        final_price = min(snipe_price, ask)
        
        return SnipeAnalysis(
            ticker=ticker,
            snipe_price=final_price,
            spread=spread,
            is_liquid=spread < 10,
            bid=bid,
            ask=ask
        )
