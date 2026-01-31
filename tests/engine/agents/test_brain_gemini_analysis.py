import pytest
import os
from engine.agents.brain import BrainAgent
from engine.core.synapse import Opportunity, MarketData

@pytest.mark.asyncio
async def test_brain_real_gemini_analysis(bus, synapse):
    """Verify BrainAgent performs a real AI analysis and produces a signal."""
    brain = BrainAgent(3, bus, synapse=synapse)
    brain.CONFIDENCE_THRESHOLD = 0.5  # Lower for test

    # CRITICAL FIX: Check if API key is configured, skip if not
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("Gemini API key not configured - set GEMINI_API_KEY env var")

    # 1. Manually push an opportunity to Synapse
    md = MarketData(
        ticker="TEST-BRAIN-AI",
        title="Will Gemini pass this test?",
        subtitle="AI validation",
        yes_price=50,
        no_price=50,
        volume=100,
        expiration="2026-12-31"
    )
    opp = Opportunity(ticker="TEST-BRAIN-AI", market_data=md)
    await synapse.opportunities.push(opp)

    # 2. Run Brain's consumption logic once
    await brain.process_opportunities(None)

    # 3. Verify execution queue
    size = await synapse.executions.size()
    if size == 0:
        # Add diagnostic output for debugging
        print(f"\n[BRAIN] No execution queued. AI likely vetoed the trade.")
        print(f"[BRAIN] Check if GEMINI_API_KEY is set and valid")
        pytest.fail("Execution queue empty - AI likely returned low confidence")

    assert size == 1
    sig = await synapse.executions.pop()
    assert sig.target_opportunity.ticker == "TEST-BRAIN-AI"
    assert sig.confidence > 0
    print(f"\n[BRAIN] Analysis successful. Side: {sig.side}")
