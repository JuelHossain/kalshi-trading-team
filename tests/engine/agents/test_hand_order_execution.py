import pytest
from engine.agents.hand import HandAgent
from engine.core.synapse import Opportunity, MarketData, ExecutionSignal
from unittest.mock import patch

@pytest.mark.asyncio
async def test_hand_real_demo_execution(bus, synapse, k_client, vault):
    """Verify HandAgent executes a real order on Kalshi Demo."""
    # WARNING: This test PLACES AN ACTUAL ORDER on Kalshi Demo.
    hand = HandAgent(4, bus, vault=vault, kalshi_client=k_client, synapse=synapse)
    
    # Mock snipe_check to always pass
    with patch.object(HandAgent, 'snipe_check', return_value={"valid": True, "entry_price": 50, "slippage": 0}):
        # Ensure vault has funds
        await vault.initialize(100000) # $1000
        
        # 1. Create a dummy execution signal for a real but cheap market
        # We'll try to find a real ticker first or use a known one.
        # For now, let's use a VERY safe small order.
        
        # To be extremely safe, we should fetch a real ticker first
        from engine.agents.senses import SensesAgent
        senses = SensesAgent(2, bus, kalshi_client=k_client, synapse=synapse)
        await senses.surveillance_loop()
        
        opp = await synapse.opportunities.pop()
        if not opp:
            pytest.skip("No real markets available to test Hand execution.")
            
        sig = ExecutionSignal(
            target_opportunity=opp,
            action="BUY",
            side="YES",
            confidence=0.9,
            monte_carlo_ev=2.0,
            reasoning="Testing Hand agent",
            suggested_count=1 # JUST ONE CONTRACT
        )
        
        # 2. Push to executions queue
        await synapse.executions.push(sig)
        
        # 3. Run Hand's consumption logic once
        # hand.on_execution_ready() handles the signal from Synapse
        await hand.on_execution_ready(None)
            
        # 4. Verify order was processed (Vault should have deducted or order ID should be logged)
        # Vault balance will decrease if order filled
        assert vault.current_balance < 100000
        print(f"\n[HAND] Execution success. New Balance: ${vault.current_balance/100:.2f}")

import asyncio
