import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from engine.main import GhostEngine
from engine.core.error_dispatcher import ErrorDispatcher, ErrorSeverity

@pytest.mark.asyncio
async def test_engine_halt_protocol(synapse):
    """Verify GHOST ENGINE immediately halts authorization when Synapse Error Box is not empty."""
    engine = GhostEngine()
    engine.synapse = synapse

    # Initialize vault to avoid floor breach lockdown
    await engine.vault.initialize(50000) # $500

    # CRITICAL FIX: Mock the Kalshi API call to prevent race condition in test environment
    async def mock_get_balance():
        return 50000  # $500 - matches vault initialization

    with patch('engine.main.kalshi_client.get_balance', new=mock_get_balance):
        # 1. Start Healthy
        assert await engine.authorize_cycle() is True
    
    # 2. Inject Critical Error via Dispatcher
    dispatcher = ErrorDispatcher("BRAIN", synapse=synapse)
    await dispatcher.dispatch(
        code="INTELLIGENCE_AI_UNAVAILABLE",
        message="Gemini is down",
        severity=ErrorSeverity.CRITICAL
    )
    
    # Wait for non-blocking task to complete
    await asyncio.sleep(0.1)

    # 3. Verify Halt
    assert await synapse.errors.size() == 1
    assert await engine.authorize_cycle() is False
