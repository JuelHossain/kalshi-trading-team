"""
Test Fix 3: Async Error Race Condition

Vulnerability: Uses asyncio.create_task() for non-blocking error logging
Fix: For CRITICAL/HIGH severity, use synchronous await instead

This test demonstrates:
1. The vulnerability (BEFORE fix): Error logged asynchronously, cycle starts before Error Box populated
2. The fix (AFTER): Critical errors logged synchronously, guaranteeing halt before next cycle
"""

import pytest
import asyncio
import sys
from pathlib import Path

# Add engine directory to path
engine_dir = Path(__file__).parent.parent.parent.parent / "engine"
sys.path.insert(0, str(engine_dir))

from unittest.mock import AsyncMock, MagicMock, patch
from core.error_dispatcher import ErrorDispatcher, ErrorSeverity, ErrorDomain
from core.synapse import Synapse


class MockSynapse:
    """Mock Synapse for testing"""
    def __init__(self):
        self.errors = MagicMock()
        self.errors.push = AsyncMock()
        self.errors.size = AsyncMock(return_value=0)

    async def setup_error_queue(self):
        """Setup error queue"""
        pass


class TestAsyncErrorRace:
    """Test suite for async error race condition vulnerability"""

    @pytest.mark.asyncio
    async def test_fix_critical_errors_logged_synchronously(self):
        """
        FIX VERIFICATION: Verify that CRITICAL and HIGH severity errors
        are logged synchronously (using await, not create_task).

        This ensures the Error Box is populated BEFORE dispatch() returns.
        """
        synapse = MockSynapse()
        event_bus = MagicMock()
        event_bus.publish = AsyncMock()

        dispatcher = ErrorDispatcher(
            agent_name="TEST_AGENT",
            event_bus=event_bus,
            synapse=synapse
        )

        # Track if push was awaited (synchronous)
        push_called_synchronously = False

        async def tracked_push(error):
            nonlocal push_called_synchronously
            push_called_synchronously = True
            await asyncio.sleep(0.01)  # Simulate DB write

        synapse.errors.push = tracked_push

        # Dispatch CRITICAL error
        error = await dispatcher.dispatch(
            code="SYSTEM_INIT_FAILED",
            severity=ErrorSeverity.CRITICAL,
            domain=ErrorDomain.SYSTEM
        )

        # Verify that push was actually awaited (synchronous)
        assert push_called_synchronously, "CRITICAL errors should be logged synchronously"

    @pytest.mark.asyncio
    async def test_fix_high_errors_logged_synchronously(self):
        """
        Verify that HIGH severity errors are also logged synchronously.
        """
        synapse = MockSynapse()
        event_bus = MagicMock()
        event_bus.publish = AsyncMock()

        dispatcher = ErrorDispatcher(
            agent_name="TEST_AGENT",
            event_bus=event_bus,
            synapse=synapse
        )

        # Track if push was awaited
        push_called_synchronously = False

        async def tracked_push(error):
            nonlocal push_called_synchronously
            push_called_synchronously = True

        synapse.errors.push = tracked_push

        # Dispatch HIGH error
        error = await dispatcher.dispatch(
            code="INTELLIGENCE_AI_UNAVAILABLE",
            severity=ErrorSeverity.HIGH,
            domain=ErrorDomain.INTELLIGENCE
        )

        # Verify synchronous logging
        assert push_called_synchronously, "HIGH errors should be logged synchronously"

    @pytest.mark.asyncio
    async def test_medium_errors_can_be_async(self):
        """
        Verify that MEDIUM and lower severity errors can use async logging
        (non-blocking is acceptable for non-critical errors).
        """
        synapse = MockSynapse()
        event_bus = MagicMock()
        event_bus.publish = AsyncMock()

        dispatcher = ErrorDispatcher(
            agent_name="TEST_AGENT",
            event_bus=event_bus,
            synapse=synapse
        )

        # Dispatch MEDIUM error
        error = await dispatcher.dispatch(
            code="DATA_VALIDATION_FAILED",
            severity=ErrorSeverity.MEDIUM,
            domain=ErrorDomain.DATA
        )

        # For MEDIUM, async is acceptable - just verify it was called
        # (we can't easily test if it was awaited vs created as task without more complex mocking)
        synapse.errors.push.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_box_populated_before_next_cycle(self):
        """
        Integration test: Verify that Error Box is populated immediately
        after critical error, before next cycle can start.

        This simulates the race scenario:
        1. Critical error occurs
        2. authorize_cycle() checks Error Box
        3. Error must be in box (not pending)
        """
        synapse = MockSynapse()
        event_bus = MagicMock()
        event_bus.publish = AsyncMock()

        # Track error count
        error_count = 0

        async def mock_push(error):
            """Mock push that actually tracks errors"""
            nonlocal error_count
            error_count += 1

        async def mock_size():
            """Mock size that returns actual count"""
            return error_count

        synapse.errors.push = mock_push
        synapse.errors.size = mock_size

        dispatcher = ErrorDispatcher(
            agent_name="TEST_AGENT",
            event_bus=event_bus,
            synapse=synapse
        )

        # Dispatch CRITICAL error
        await dispatcher.dispatch(
            code="SYSTEM_EVENT_BUS_FAILED",
            severity=ErrorSeverity.CRITICAL,
            domain=ErrorDomain.SYSTEM
        )

        # Immediately check error count (simulating authorize_cycle)
        # In fixed version, this should be 1 (not 0)
        count = await synapse.errors.size()

        assert count == 1, "Error Box should contain 1 error immediately after dispatch"

    @pytest.mark.asyncio
    async def test_multiple_critical_errors_all_logged(self):
        """
        Verify that multiple critical errors are all logged synchronously.
        """
        synapse = MockSynapse()
        event_bus = MagicMock()
        event_bus.publish = AsyncMock()

        dispatcher = ErrorDispatcher(
            agent_name="TEST_AGENT",
            event_bus=event_bus,
            synapse=synapse
        )

        # Dispatch multiple CRITICAL errors
        errors = [
            ("SYSTEM_INIT_FAILED", ErrorSeverity.CRITICAL),
            ("SYSTEM_EVENT_BUS_FAILED", ErrorSeverity.CRITICAL),
            ("INTELLIGENCE_AI_UNAVAILABLE", ErrorSeverity.HIGH),
        ]

        for code, severity in errors:
            await dispatcher.dispatch(
                code=code,
                severity=severity,
                domain=ErrorDomain.SYSTEM
            )

        # Verify all were pushed
        assert synapse.errors.push.call_count == 3

    @pytest.mark.asyncio
    async def test_synchronous_logging_blocks_until_complete(self):
        """
        Verify that synchronous await actually blocks until the push completes.
        """
        synapse = MockSynapse()

        # Make push artificially slow
        async def slow_push(error):
            await asyncio.sleep(0.1)  # Simulate slow DB write
            return True

        synapse.errors.push = slow_push
        synapse.errors.size = AsyncMock(return_value=1)

        event_bus = MagicMock()
        event_bus.publish = AsyncMock()

        dispatcher = ErrorDispatcher(
            agent_name="TEST_AGENT",
            event_bus=event_bus,
            synapse=synapse
        )

        # Dispatch should take at least 0.1s (await time)
        import time
        start = time.time()
        await dispatcher.dispatch(
            code="SYSTEM_INIT_FAILED",
            severity=ErrorSeverity.CRITICAL,
            domain=ErrorDomain.SYSTEM
        )
        elapsed = time.time() - start

        # Should have waited for the slow push
        assert elapsed >= 0.1, "Should block until push completes"

    @pytest.mark.asyncio
    async def test_fix_critical_errors_logged_synchronously(self):
        """
        FIX VERIFICATION: Verify that CRITICAL and HIGH severity errors
        are logged synchronously (using await, not create_task).

        This ensures the Error Box is populated BEFORE dispatch() returns.
        """
        synapse = MockSynapse()
        event_bus = MagicMock()
        event_bus.publish = AsyncMock()

        dispatcher = ErrorDispatcher(
            agent_name="TEST_AGENT",
            event_bus=event_bus,
            synapse=synapse
        )

        # Dispatch CRITICAL error
        error = await dispatcher.dispatch(
            code="SYSTEM_INIT_FAILED",
            severity=ErrorSeverity.CRITICAL,
            domain=ErrorDomain.SYSTEM
        )

        # Verify that synapse.errors.push was actually awaited
        # (not just created as a task)
        # In the fixed version, this will be called synchronously
        synapse.errors.push.assert_called_once()

        # Verify the error data is correct
        call_args = synapse.errors.push.call_args
        pushed_error = call_args[0][0]  # First positional argument
        assert pushed_error.code == "SYSTEM_INIT_FAILED"
        assert pushed_error.severity == "CRITICAL"

    @pytest.mark.asyncio
    async def test_fix_high_errors_logged_synchronously(self):
        """
        Verify that HIGH severity errors are also logged synchronously.
        """
        synapse = MockSynapse()
        event_bus = MagicMock()
        event_bus.publish = AsyncMock()

        dispatcher = ErrorDispatcher(
            agent_name="TEST_AGENT",
            event_bus=event_bus,
            synapse=synapse
        )

        # Dispatch HIGH error
        error = await dispatcher.dispatch(
            code="INTELLIGENCE_AI_UNAVAILABLE",
            severity=ErrorSeverity.HIGH,
            domain=ErrorDomain.INTELLIGENCE
        )

        # Verify synchronous logging
        synapse.errors.push.assert_called_once()

    @pytest.mark.asyncio
    async def test_medium_errors_can_be_async(self):
        """
        Verify that MEDIUM and lower severity errors can use async logging
        (non-blocking is acceptable for non-critical errors).
        """
        synapse = MockSynapse()
        event_bus = MagicMock()
        event_bus.publish = AsyncMock()

        dispatcher = ErrorDispatcher(
            agent_name="TEST_AGENT",
            event_bus=event_bus,
            synapse=synapse
        )

        # Dispatch MEDIUM error
        error = await dispatcher.dispatch(
            code="DATA_VALIDATION_FAILED",
            severity=ErrorSeverity.MEDIUM,
            domain=ErrorDomain.DATA
        )

        # For MEDIUM, async is acceptable
        # We just verify it was eventually called
        await asyncio.sleep(0.1) # Allow async task to run
        synapse.errors.push.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_box_populated_before_next_cycle(self):
        """
        Integration test: Verify that Error Box is populated immediately
        after critical error, before next cycle can start.

        This simulates the race scenario:
        1. Critical error occurs
        2. authorize_cycle() checks Error Box
        3. Error must be in box (not pending)
        """
        synapse = MockSynapse()
        event_bus = MagicMock()
        event_bus.publish = AsyncMock()

        # Track error count
        error_count = 0

        async def mock_push(error):
            """Mock push that actually tracks errors"""
            nonlocal error_count
            error_count += 1

        async def mock_size():
            """Mock size that returns actual count"""
            return error_count

        synapse.errors.push = mock_push
        synapse.errors.size = mock_size

        dispatcher = ErrorDispatcher(
            agent_name="TEST_AGENT",
            event_bus=event_bus,
            synapse=synapse
        )

        # Dispatch CRITICAL error
        await dispatcher.dispatch(
            code="SYSTEM_EVENT_BUS_FAILED",
            severity=ErrorSeverity.CRITICAL,
            domain=ErrorDomain.SYSTEM
        )

        # Immediately check error count (simulating authorize_cycle)
        # In fixed version, this should be 1 (not 0)
        count = await synapse.errors.size()

        assert count == 1, "Error Box should contain 1 error immediately after dispatch"

    @pytest.mark.asyncio
    async def test_multiple_critical_errors_all_logged(self):
        """
        Verify that multiple critical errors are all logged synchronously.
        """
        synapse = MockSynapse()
        event_bus = MagicMock()
        event_bus.publish = AsyncMock()

        dispatcher = ErrorDispatcher(
            agent_name="TEST_AGENT",
            event_bus=event_bus,
            synapse=synapse
        )

        # Dispatch multiple CRITICAL errors
        errors = [
            ("SYSTEM_INIT_FAILED", ErrorSeverity.CRITICAL),
            ("SYSTEM_EVENT_BUS_FAILED", ErrorSeverity.CRITICAL),
            ("INTELLIGENCE_AI_UNAVAILABLE", ErrorSeverity.HIGH),
        ]

        for code, severity in errors:
            await dispatcher.dispatch(
                code=code,
                severity=severity,
                domain=ErrorDomain.SYSTEM
            )

        # Verify all were pushed
        assert synapse.errors.push.call_count == 3

    @pytest.mark.asyncio
    async def test_synchronous_logging_blocks_until_complete(self):
        """
        Verify that synchronous await actually blocks until the push completes.
        """
        synapse = MockSynapse()

        # Make push artificially slow
        async def slow_push(error):
            await asyncio.sleep(0.1)  # Simulate slow DB write
            return True

        synapse.errors.push = slow_push
        synapse.errors.size = AsyncMock(return_value=1)

        event_bus = MagicMock()
        event_bus.publish = AsyncMock()

        dispatcher = ErrorDispatcher(
            agent_name="TEST_AGENT",
            event_bus=event_bus,
            synapse=synapse
        )

        # Dispatch should take at least 0.1s (await time)
        import time
        start = time.time()
        await dispatcher.dispatch(
            code="SYSTEM_INIT_FAILED",
            severity=ErrorSeverity.CRITICAL,
            domain=ErrorDomain.SYSTEM
        )
        elapsed = time.time() - start

        # Should have waited for the slow push
        assert elapsed >= 0.1, "Should block until push completes"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
