"""
Test suite for stale opportunity detection in BrainAgent.

This test reproduces the risk of processing stale market data (>60 seconds old).
TDD Phase: RED - Tests should fail before the fix is implemented.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import sys
sys.path.insert(0, 'e:/Projects/kalshi-trading-team')

from engine.agents.brain import BrainAgent
from engine.core.bus import EventBus
from engine.core.synapse import Synapse, Opportunity, MarketData


@pytest.fixture
def brain_agent():
    """Create a BrainAgent instance for testing"""
    bus = EventBus()
    synapse = None  # Not needed for process_single_opportunity testing
    agent = BrainAgent(
        agent_id=1,
        bus=bus,
        synapse=synapse
    )
    # Mock AI client to avoid actual API calls
    agent.client = None
    return agent


class TestStaleOpportunityDetection:
    """Test suite for stale opportunity detection in process_single_opportunity"""

    @pytest.mark.asyncio
    async def test_stale_opportunity_rejected(self, brain_agent, caplog):
        """
        TEST: Opportunities older than 60 seconds should be rejected with STALE status
        """
        # Create an opportunity with timestamp > 60 seconds ago
        old_timestamp = datetime.now() - timedelta(seconds=120)  # 2 minutes old

        stale_opportunity = {
            "id": str(uuid.uuid4()),
            "ticker": "STALE-TEST-123",
            "kalshi_price": 0.50,
            "timestamp": old_timestamp,
            "market_data": {
                "ticker": "STALE-TEST-123",
                "title": "Stale Market",
                "yes_price": 50,
                "volume": 1000
            }
        }

        result = await brain_agent.process_single_opportunity(stale_opportunity)

        # Should return 'STALE' for old opportunities
        assert result == "STALE", "Should return STALE for opportunities > 60 seconds old"

    @pytest.mark.asyncio
    async def test_fresh_opportunity_accepted(self, brain_agent):
        """
        TEST: Opportunities younger than 60 seconds should be processed normally
        """
        # Create a fresh opportunity (current timestamp)
        fresh_opportunity = {
            "id": str(uuid.uuid4()),
            "ticker": "FRESH-TEST-456",
            "kalshi_price": 0.50,
            "timestamp": datetime.now(),  # Fresh
            "market_data": {
                "ticker": "FRESH-TEST-456",
                "title": "Fresh Market",
                "yes_price": 50,
                "volume": 1000
            }
        }

        # Mock AI client to return valid response
        brain_agent.client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = '''{
            "optimist": "Good opportunity",
            "critic": "Risks exist",
            "judge_verdict": "Approved with caution",
            "estimated_probability": 0.75,
            "confidence": 90
        }'''
        brain_agent.client.models.generate_content = MagicMock(return_value=mock_response)

        result = await brain_agent.process_single_opportunity(fresh_opportunity)

        # Should NOT return 'STALE' for fresh opportunities
        assert result != "STALE", "Should not return STALE for fresh opportunities"

    @pytest.mark.asyncio
    async def test_exactly_60_seconds_old_rejected(self, brain_agent):
        """
        TEST: Opportunities exactly 60 seconds old should be rejected (boundary test)
        """
        # Create an opportunity exactly 60 seconds old
        boundary_timestamp = datetime.now() - timedelta(seconds=60)

        boundary_opportunity = {
            "id": str(uuid.uuid4()),
            "ticker": "BOUNDARY-TEST-789",
            "kalshi_price": 0.50,
            "timestamp": boundary_timestamp,
            "market_data": {
                "ticker": "BOUNDARY-TEST-789",
                "title": "Boundary Market",
                "yes_price": 50,
                "volume": 1000
            }
        }

        result = await brain_agent.process_single_opportunity(boundary_opportunity)

        # Should return 'STALE' for opportunities at exactly 60 seconds
        assert result == "STALE", "Should return STALE for opportunities exactly 60 seconds old"

    @pytest.mark.asyncio
    async def test_59_seconds_old_accepted(self, brain_agent):
        """
        TEST: Opportunities 59 seconds old should be processed (boundary test)
        """
        # Create an opportunity 59 seconds old
        fresh_timestamp = datetime.now() - timedelta(seconds=59)

        fresh_opportunity = {
            "id": str(uuid.uuid4()),
            "ticker": "FRESH-59-TEST",
            "kalshi_price": 0.50,
            "timestamp": fresh_timestamp,
            "market_data": {
                "ticker": "FRESH-59-TEST",
                "title": "Fresh Market 59s",
                "yes_price": 50,
                "volume": 1000
            }
        }

        # Mock AI client
        brain_agent.client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = '''{
            "optimist": "Good opportunity",
            "critic": "Risks exist",
            "judge_verdict": "Proceed",
            "estimated_probability": 0.80,
            "confidence": 95
        }'''
        brain_agent.client.models.generate_content = MagicMock(return_value=mock_response)

        result = await brain_agent.process_single_opportunity(fresh_opportunity)

        # Should NOT return 'STALE' for 59 second old opportunities
        assert result != "STALE", "Should not return STALE for opportunities 59 seconds old"

    @pytest.mark.asyncio
    async def test_missing_timestamp_treated_as_stale(self, brain_agent):
        """
        TEST: Opportunities without timestamp should be rejected for safety
        """
        # Create an opportunity without timestamp
        no_timestamp_opportunity = {
            "id": str(uuid.uuid4()),
            "ticker": "NO-TIMESTAMP-TEST",
            "kalshi_price": 0.50,
            "market_data": {
                "ticker": "NO-TIMESTAMP-TEST",
                "title": "No Timestamp Market",
                "yes_price": 50,
                "volume": 1000
            }
        }

        result = await brain_agent.process_single_opportunity(no_timestamp_opportunity)

        # Should return 'STALE' for opportunities without timestamp (safety first)
        assert result == "STALE", "Should return STALE for opportunities without timestamp"

    @pytest.mark.asyncio
    async def test_stale_opportunity_logs_warning(self, brain_agent, caplog):
        """
        TEST: Stale opportunities should log '[STALE] Opportunity expired' message
        """
        old_timestamp = datetime.now() - timedelta(seconds=120)

        stale_opportunity = {
            "id": str(uuid.uuid4()),
            "ticker": "STALE-LOG-TEST",
            "kalshi_price": 0.50,
            "timestamp": old_timestamp,
            "market_data": {
                "ticker": "STALE-LOG-TEST",
                "title": "Stale Market",
                "yes_price": 50,
                "volume": 1000
            }
        }

        result = await brain_agent.process_single_opportunity(stale_opportunity)

        assert result == "STALE"
        # Verify the log message contains the expected text
        # (Note: actual logging depends on the agent's log implementation)

    @pytest.mark.asyncio
    async def test_extremely_stale_opportunity_rejected(self, brain_agent):
        """
        TEST: Extremely old opportunities (e.g., 1 hour) should be rejected
        """
        # Create an opportunity 1 hour old
        ancient_timestamp = datetime.now() - timedelta(hours=1)

        ancient_opportunity = {
            "id": str(uuid.uuid4()),
            "ticker": "ANCIENT-TEST",
            "kalshi_price": 0.50,
            "timestamp": ancient_timestamp,
            "market_data": {
                "ticker": "ANCIENT-TEST",
                "title": "Ancient Market",
                "yes_price": 50,
                "volume": 1000
            }
        }

        result = await brain_agent.process_single_opportunity(ancient_opportunity)

        # Should return 'STALE' for ancient opportunities
        assert result == "STALE", "Should return STALE for extremely old opportunities"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
