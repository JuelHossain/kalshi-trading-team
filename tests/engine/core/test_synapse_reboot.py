import pytest
import os
from engine.core.synapse import Synapse, Opportunity, MarketData

@pytest.mark.asyncio
async def test_synapse_data_persistence_on_reboot(test_db):
    """Verify that items pushed to Synapse survive closing and reopening the database."""
    # 1. First session
    synapse1 = Synapse(db_path=test_db)
    md = MarketData(ticker="REBOOT-OK", title="T", subtitle="S", yes_price=1, no_price=1, volume=1, expiration="")
    opp = Opportunity(ticker="REBOOT-OK", market_data=md)
    await synapse1.opportunities.push(opp)
    assert await synapse1.opportunities.size() == 1
    
    # "Shutdown"
    del synapse1
    
    # 2. Second session
    synapse2 = Synapse(db_path=test_db)
    assert await synapse2.opportunities.size() == 1
    
    popped = await synapse2.opportunities.pop()
    assert popped.ticker == "REBOOT-OK"
