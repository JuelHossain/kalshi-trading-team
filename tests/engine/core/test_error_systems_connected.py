"""The dispatcher reports; the manager decides. They now talk.

These are not duplicate systems. ErrorDispatcher is transport -- terminal,
dashboard, Synapse, with deduplication. ErrorManager is policy -- escalate,
count, halt. The separation is sound.

What was broken is that nothing connected them. An error painted on the
dashboard never reached the thing that decides whether to stop trading, and the
manager's statistics described only the errors routed to it directly.
BaseAgent held both objects and passed neither to the other.
"""

from unittest.mock import AsyncMock

import pytest

from core.bus import EventBus
from core.error_codes import ErrorDomain, ErrorSeverity
from core.error_dispatcher import ErrorDispatcher
from core.error_manager import ErrorManager


@pytest.fixture
def manager():
    return ErrorManager()


class TestDispatchedErrorsReachThePolicyLayer:
    @pytest.mark.asyncio
    async def test_a_dispatched_error_is_registered(self, manager):
        dispatcher = ErrorDispatcher("BRAIN", error_manager=manager)

        await dispatcher.dispatch(
            code="INTELLIGENCE_AI_UNAVAILABLE",
            message="AI down",
            severity=ErrorSeverity.HIGH,
            domain=ErrorDomain.INTELLIGENCE,
        )

        stats = manager.get_error_stats()
        assert stats["total_errors"] == 1

    @pytest.mark.asyncio
    async def test_the_agent_name_travels_with_it(self, manager):
        """Statistics are useless if every error looks like it came from nowhere."""
        await ErrorDispatcher("SENSES", error_manager=manager).dispatch(
            code="NETWORK_CONNECTION_FAILED", severity=ErrorSeverity.MEDIUM
        )

        recent = manager.get_recent_errors()
        assert recent[0].agent_name == "SENSES"

    @pytest.mark.asyncio
    async def test_severity_is_preserved_not_flattened(self, manager):
        """Escalation depends on severity arriving intact."""
        await ErrorDispatcher("HAND", error_manager=manager).dispatch(
            code="TRADE_FAILED", severity=ErrorSeverity.HIGH
        )

        assert manager.get_recent_errors()[0].severity == ErrorSeverity.HIGH

    @pytest.mark.asyncio
    async def test_a_critical_error_escalates_to_shutdown(self, manager):
        """The point of connecting them: severity now means something.

        Previously a CRITICAL dispatch only printed. Call sites had to remember
        to publish SYSTEM_FATAL as well, and one that forgot would surface a
        fatal error to the operator while the engine kept trading.
        """
        shutdown = AsyncMock()
        manager.shutdown_callback = shutdown

        await ErrorDispatcher("SOUL", error_manager=manager).dispatch(
            code="SYSTEM_INIT_FAILED", severity=ErrorSeverity.CRITICAL
        )

        shutdown.assert_awaited_once()


class TestTheConnectionIsOptionalAndSafe:
    @pytest.mark.asyncio
    async def test_a_dispatcher_without_a_manager_still_works(self):
        """Most call sites construct one directly with no manager."""
        error = await ErrorDispatcher("BRAIN").dispatch(
            code="NETWORK_CONNECTION_FAILED", severity=ErrorSeverity.LOW
        )
        assert error is not None

    @pytest.mark.asyncio
    async def test_a_failing_manager_does_not_swallow_the_original_error(self, manager):
        """Losing the real error behind a reporting failure is the worst outcome."""
        manager.register_error = AsyncMock(side_effect=RuntimeError("manager broken"))

        error = await ErrorDispatcher("BRAIN", error_manager=manager).dispatch(
            code="NETWORK_CONNECTION_FAILED", severity=ErrorSeverity.HIGH
        )

        assert error is not None
        assert error.code == "NETWORK_CONNECTION_FAILED"


class TestBaseAgentWiresThemTogether:
    def test_an_agent_connects_its_own_two_systems(self):
        """BaseAgent held both and passed neither. It now passes one to the other."""
        from agents.base import BaseAgent

        manager = ErrorManager()
        agent = BaseAgent("TEST", 1, EventBus(), error_manager=manager)

        assert agent.error_dispatcher.error_manager is manager


class TestShutdownIsIdempotent:
    @pytest.mark.asyncio
    async def test_the_teardown_runs_only_once(self, test_db):
        """Two paths can now request shutdown; tearing down twice is not safe.

        Asserts the work is not repeated, not merely that the second call
        returns quietly -- without the guard it also returns quietly, having
        torn every agent down a second time and closed the API session twice.
        """
        import main
        from core.synapse import Synapse

        engine = main.GhostEngine()
        engine.synapse = Synapse(db_path=test_db)

        agent = AsyncMock()
        agent.teardown = AsyncMock()
        engine.agents = [agent]

        await engine.shutdown("first")
        await engine.shutdown("second")

        assert agent.teardown.await_count == 1, (
            "the second shutdown repeated the teardown"
        )
