"""
Test Fix 4: Variance Veto Logic Optimization

Vulnerability: When AI fails (confidence=0, estimated_prob=None), run_simulation(None)
returns variance=999, which correctly vetos but wastes CPU on simulation.
Fix: Check if confidence==0 or estimated_prob is None BEFORE calling run_simulation()

This test demonstrates:
1. The vulnerability (BEFORE fix): Unnecessary simulation when result is predetermined
2. The fix (AFTER): Early veto/skip when AI fails, avoiding wasted CPU
"""

import pytest
import asyncio
import sys
from pathlib import Path

# Add engine directory to path
engine_dir = Path(__file__).parent.parent.parent.parent / "engine"
sys.path.insert(0, str(engine_dir))

from unittest.mock import AsyncMock, MagicMock, patch
from agents.brain import BrainAgent
from core.bus import EventBus
from core.synapse import Synapse


class TestVarianceVetoLogic:
    """Test suite for variance veto logic optimization"""

    @pytest.fixture
    async def brain_agent(self):
        """Create a BrainAgent for testing"""
        bus = EventBus()
        synapse = Synapse()  # Synapse has no initialize() method

        # Mock Gemini client (unavailable)
        with patch('agents.brain.GEMINI_AVAILABLE', False):
            agent = BrainAgent(
                agent_id=3,
                bus=bus,
                synapse=synapse
            )
            # Override to skip actual AI calls
            agent.client = None

            await agent.setup()
            yield agent

    @pytest.mark.asyncio
    async def test_fix_early_veto_when_confidence_zero(self):
        """
        FIX VERIFICATION: Verify that opportunities with confidence=0
        are rejected immediately WITHOUT running simulation.

        The fix should check confidence before calling run_simulation().
        """
        bus = EventBus()
        synapse = Synapse()  # No initialize() needed

        agent = BrainAgent(agent_id=3, bus=bus, synapse=synapse)

        # Track simulation calls
        simulation_calls = []
        original_run_simulation = agent.run_simulation

        def tracked_run_simulation(*args, **kwargs):
            simulation_calls.append((args, kwargs))
            return original_run_simulation(*args, **kwargs)

        agent.run_simulation = tracked_run_simulation

        # Mock run_debate to return zero confidence
        agent.run_debate = AsyncMock(return_value={
            "confidence": 0.0,
            "reasoning": "AI service unavailable",
            "estimated_probability": None
        })

        # Use current timestamp to pass STALE check (age < 60 seconds)
        # Use naive datetime to match brain.py's datetime.now()
        from datetime import datetime
        current_ts = datetime.now().isoformat()

        opportunity = {
            "ticker": "TEST",
            "kalshi_price": 0.50,
            "market_data": {"title": "Test", "subtitle": "Test"},
            "timestamp": current_ts
        }

        result = await agent.process_single_opportunity(opportunity)

        # Verify result
        assert result in ["SKIPPED", "VETOED"], "Should skip/veto with zero confidence"

        # AFTER FIX: Simulation should NOT be called
        # BEFORE FIX: Simulation IS called (wasteful)
        # This test will pass after fix is applied
        assert len(simulation_calls) == 0, \
            f"Simulation should not be called when confidence=0, but was called {len(simulation_calls)} times"

    @pytest.mark.asyncio
    async def test_fix_early_skip_when_probability_none(self):
        """
        Verify that opportunities with estimated_prob=None
        are rejected immediately WITHOUT running simulation.
        """
        bus = EventBus()
        synapse = Synapse()  # No initialize() needed

        agent = BrainAgent(agent_id=3, bus=bus, synapse=synapse)

        # Track simulation calls
        simulation_calls = []
        original_run_simulation = agent.run_simulation

        def tracked_run_simulation(*args, **kwargs):
            simulation_calls.append((args, kwargs))
            return original_run_simulation(*args, **kwargs)

        agent.run_simulation = tracked_run_simulation

        # Mock run_debate to return None probability
        agent.run_debate = AsyncMock(return_value={
            "confidence": 0.5,  # Non-zero confidence
            "reasoning": "Some reasoning",
            "estimated_probability": None  # But no probability!
        })

        # Use current timestamp to pass STALE check (age < 60 seconds)
        # Use naive datetime to match brain.py's datetime.now()
        from datetime import datetime
        current_ts = datetime.now().isoformat()

        opportunity = {
            "ticker": "TEST",
            "kalshi_price": 0.50,
            "market_data": {"title": "Test", "subtitle": "Test"},
            "timestamp": current_ts
        }

        result = await agent.process_single_opportunity(opportunity)

        # Verify result
        assert result in ["SKIPPED", "VETOED"], "Should skip/veto with None probability"

        # AFTER FIX: Simulation should NOT be called
        assert len(simulation_calls) == 0, \
            f"Simulation should not be called when probability is None"

    @pytest.mark.asyncio
    async def test_simulation_runs_when_ai_succeeds(self):
        """
        Verify that simulation DOES run when AI succeeds.
        This ensures the fix doesn't break normal operation.
        """
        bus = EventBus()
        synapse = Synapse()  # No initialize() needed

        agent = BrainAgent(agent_id=3, bus=bus, synapse=synapse)

        # Track simulation calls
        simulation_calls = []
        original_run_simulation = agent.run_simulation

        def tracked_run_simulation(*args, **kwargs):
            simulation_calls.append((args, kwargs))
            return original_run_simulation(*args, **kwargs)

        agent.run_simulation = tracked_run_simulation

        # Mock successful AI response
        agent.run_debate = AsyncMock(return_value={
            "confidence": 0.90,  # High confidence
            "reasoning": "Strong bullish signal",
            "estimated_probability": 0.75  # Valid probability
        })

        # Use current timestamp to pass STALE check (age < 60 seconds)
        # Use naive datetime to match brain.py's datetime.now()
        from datetime import datetime
        current_ts = datetime.now().isoformat()

        opportunity = {
            "ticker": "TEST",
            "kalshi_price": 0.50,
            "market_data": {"title": "Test", "subtitle": "Test"},
            "timestamp": current_ts
        }

        result = await agent.process_single_opportunity(opportunity)

        # Simulation SHOULD have been called
        assert len(simulation_calls) == 1, \
            "Simulation should run when AI succeeds with valid probability"

        # Result depends on variance/ev thresholds
        assert result in ["APPROVED", "VETOED"]

    @pytest.mark.asyncio
    async def test_simulation_returns_999_variance_for_none_prob(self):
        """
        Verify that run_simulation(None) returns variance=999.
        This is the sentinel value that triggers veto.
        """
        bus = EventBus()
        synapse = Synapse()  # No initialize() needed

        agent = BrainAgent(agent_id=3, bus=bus, synapse=synapse)

        opportunity = {
            "ticker": "TEST",
            "kalshi_price": 0.50
        }

        # Call with None probability
        result = agent.run_simulation(opportunity, override_prob=None)

        assert result["variance"] == 999.0, "Should return 999 variance for None probability"
        assert result["ev"] == -999.0, "Should return -999 EV for None probability"
        assert result["win_rate"] == 0.0, "Should return 0 win_rate for None probability"

    @pytest.mark.asyncio
    async def test_normal_simulation_with_valid_probability(self):
        """
        Verify that simulation works normally with valid probability.
        """
        bus = EventBus()
        synapse = Synapse()  # No initialize() needed

        agent = BrainAgent(agent_id=3, bus=bus, synapse=synapse)

        opportunity = {
            "ticker": "TEST",
            "kalshi_price": 0.50
        }

        # Call with valid probability
        result = agent.run_simulation(opportunity, override_prob=0.60)

        # Should have realistic values
        assert result["variance"] < 1.0, "Variance should be < 1.0 for valid probability"
        assert result["variance"] >= 0.0, "Variance should be non-negative"
        assert result["win_rate"] > 0.0, "Win rate should be > 0"

        # EV calculation: (0.60 * 0.50) - (0.40 * 0.50) = 0.30 - 0.20 = 0.10
        # Approximately (within Monte Carlo variance)
        assert -0.5 < result["ev"] < 0.5, "EV should be reasonable"

    @pytest.mark.asyncio
    async def test_early_exit_performance_improvement(self):
        """
        Performance test: Verify early exit is faster than running simulation.
        """
        bus = EventBus()
        synapse = Synapse()  # No initialize() needed

        agent = BrainAgent(agent_id=3, bus=bus, synapse=synapse)

        # Mock AI failure
        agent.run_debate = AsyncMock(return_value={
            "confidence": 0.0,
            "reasoning": "AI unavailable",
            "estimated_probability": None
        })

        # Use current timestamp to pass STALE check (age < 60 seconds)
        # Use naive datetime to match brain.py's datetime.now()
        from datetime import datetime
        current_ts = datetime.now().isoformat()

        opportunity = {
            "ticker": "TEST",
            "kalshi_price": 0.50,
            "market_data": {"title": "Test", "subtitle": "Test"},
            "timestamp": current_ts
        }

        import time
        start = time.time()
        result = await agent.process_single_opportunity(opportunity)
        elapsed = time.time() - start

        # With early exit, should be very fast (< 0.1s)
        # Without early exit (runs 10k iterations), would be > 0.5s
        # This is a soft check - performance varies
        assert elapsed < 1.0, "Early exit should be fast"

        # Verify correct result
        assert result in ["SKIPPED", "VETOED"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
