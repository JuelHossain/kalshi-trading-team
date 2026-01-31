import pytest
from engine.core.synapse import Opportunity, MarketData

@pytest.mark.asyncio
async def test_synapse_push_pop_atomic(synapse):
    """Verify basic push/pop functionality."""
    md = MarketData(ticker="ATOMIC", title="T", subtitle="S", yes_price=1, no_price=1, volume=1, expiration="")
    opp = Opportunity(ticker="ATOMIC", market_data=md)
    
    await synapse.opportunities.push(opp)
    assert await synapse.opportunities.size() == 1
    
    popped = await synapse.opportunities.pop()
    assert popped.ticker == "ATOMIC"
    assert await synapse.opportunities.size() == 0

@pytest.mark.asyncio
async def test_synapse_multiple_items_fifo(synapse):
    """Verify FIFO ordering for same priority."""
    md = MarketData(ticker="F1", title="T", subtitle="S", yes_price=1, no_price=1, volume=1, expiration="")
    opp1 = Opportunity(ticker="FIRST", market_data=md)
    opp2 = Opportunity(ticker="SECOND", market_data=md)
    
    await synapse.opportunities.push(opp1)
    await asyncio.sleep(0.01) # Ensure timestamp diff
    await synapse.opportunities.push(opp2)
    
    popped1 = await synapse.opportunities.pop()
    assert popped1.ticker == "FIRST"
    
    popped2 = await synapse.opportunities.pop()
    assert popped2.ticker == "SECOND"

import asyncio
