"""/reset must return the engine to a runnable state, not shut it down.

Two defects made recovery impossible without restarting the process and
hand-editing SQLite:

  * reset_system set engine.running = False. That is the condition of the
    main loop, so the one endpoint named "reset" terminated the engine.
  * Nothing drained synapse.errors, and authorize_cycle halts while that box
    holds anything. A recoverable error latched the engine off for good.
"""

import pytest
from core.synapse import Synapse, SynapseError
from http_api.routes import reset_system


class _Soul:
    def __init__(self):
        self.is_locked_down = True


class _Engine:
    """The surface reset_system touches."""

    def __init__(self, synapse):
        self.manual_kill_switch = True
        self.is_processing = True
        self.running = True
        self.synapse = synapse
        self.soul = _Soul()


class _Request:
    pass


@pytest.fixture
def engine(tmp_path):
    return _Engine(Synapse(db_path=str(tmp_path / "reset.db")))


def _error() -> SynapseError:
    return SynapseError(
        agent_name="TEST",
        code="BOOM",
        message="something recoverable",
        severity="CRITICAL",
        domain="SYSTEM",
    )


class TestResetRecovers:
    @pytest.mark.asyncio
    async def test_reset_does_not_stop_the_engine(self, engine):
        """The regression: reset used to exit the main loop."""
        await reset_system(engine)(_Request())

        assert engine.running is True

    @pytest.mark.asyncio
    async def test_reset_clears_the_kill_switch_and_processing_flag(self, engine):
        await reset_system(engine)(_Request())

        assert engine.manual_kill_switch is False
        assert engine.is_processing is False

    @pytest.mark.asyncio
    async def test_reset_drains_the_error_box(self, engine):
        await engine.synapse.errors.push(_error())
        await engine.synapse.errors.push(_error())

        await reset_system(engine)(_Request())

        assert await engine.synapse.errors.size() == 0

    @pytest.mark.asyncio
    async def test_reset_lifts_a_soul_lockdown(self, engine):
        """A failed pre-flight latches this, and it also halts every cycle."""
        await reset_system(engine)(_Request())

        assert engine.soul.is_locked_down is False

    @pytest.mark.asyncio
    async def test_reset_reports_what_it_cleared(self, engine):
        await engine.synapse.errors.push(_error())

        response = await reset_system(engine)(_Request())

        assert response.status == 200
        assert b'"errors_cleared": 1' in response.body

    @pytest.mark.asyncio
    async def test_reset_leaves_pending_work_alone(self, engine):
        """Recovering from an error must not discard queued trades."""
        before = (
            await engine.synapse.opportunities.size(),
            await engine.synapse.executions.size(),
        )

        await reset_system(engine)(_Request())

        after = (
            await engine.synapse.opportunities.size(),
            await engine.synapse.executions.size(),
        )
        assert before == after

    @pytest.mark.asyncio
    async def test_reset_works_on_an_engine_without_a_soul_yet(self, tmp_path):
        """Startup ordering means soul may not be attached."""
        engine = _Engine(Synapse(db_path=str(tmp_path / "nosoul.db")))
        del engine.soul

        response = await reset_system(engine)(_Request())

        assert response.status == 200
        assert engine.running is True
