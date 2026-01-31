import pytest
import asyncio
from engine.core.error_dispatcher import ErrorDispatcher, ErrorSeverity

@pytest.mark.asyncio
async def test_error_dispatcher_persistence(synapse):
    """Verify that dispatched errors are correctly saved to Synapse."""
    dispatcher = ErrorDispatcher("CORE_TEST", synapse=synapse)
    
    await dispatcher.dispatch(
        code="SYSTEM_INIT_FAILED",
        message="Initial testing error",
        severity=ErrorSeverity.HIGH
    )
    
    # Wait for non-blocking Synapse push
    await asyncio.sleep(0.1)
    
    assert await synapse.errors.size() == 1
    err = await synapse.errors.pop()
    assert err.agent_name == "CORE_TEST"
    assert err.code == "SYSTEM_INIT_FAILED"

@pytest.mark.asyncio
async def test_error_dispatcher_deduplication():
    """Verify that rapid duplicate errors are suppressed."""
    dispatcher = ErrorDispatcher("DEDUPE_TEST")
    
    # First dispatch
    event1 = await dispatcher.dispatch(code="NETWORK_TIMEOUT", message="Timeout")
    # Second dispatch immediately after
    event2 = await dispatcher.dispatch(code="NETWORK_TIMEOUT", message="Timeout")
    
    # The dispatcher's internal _is_duplicate should be true for the second one
    # Note: dispatcher.dispatch returns the ErrorEvent even if suppressed, 
    # but it won't broadcast or log to synapse if it's a duplicate.
    
    assert dispatcher._is_duplicate(dispatcher._generate_hash("NETWORK_TIMEOUT", "Timeout")) is True
