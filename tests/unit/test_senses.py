import pytest
import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# Add engine to path
sys.path.append(os.path.join(os.getcwd(), 'engine'))

from agents.senses import SensesAgent

@pytest.fixture
def senses_agent():
    bus = MagicMock()
    from unittest.mock import AsyncMock
    bus.publish = AsyncMock()
    bus.subscribe = AsyncMock()
    with patch.dict(os.environ, {}, clear=True):
        agent = SensesAgent(agent_id=2, bus=bus)
    # Mock DDGS availability
    with patch('agents.senses.DDGS_AVAILABLE', True):
        yield agent

@pytest.mark.asyncio
async def test_fetch_market_context_success(senses_agent):
    """Test context fetching with mocked DDGS"""
    with patch('agents.senses.DDGS') as MockDDGS:
        mock_ddgs_instance = MockDDGS.return_value
        mock_ddgs_instance.text.return_value = [
            {"body": "News Item 1"},
            {"body": "News Item 2"}
        ]
        
        results = await senses_agent.fetch_market_context("TICKER", "Market Title")
        
        assert len(results) == 2
        assert "News Item 1" in results
        assert "News Item 2" in results

@pytest.mark.asyncio
async def test_fetch_market_context_failure(senses_agent):
    """Test context fetching handling exception"""
    with patch('agents.senses.DDGS') as MockDDGS:
        mock_ddgs_instance = MockDDGS.return_value
        mock_ddgs_instance.text.side_effect = Exception("Search failed")
        
        results = await senses_agent.fetch_market_context("TICKER", "Market Title")
        
        # Should return empty list on error (as per my implementation)
        assert results == []
