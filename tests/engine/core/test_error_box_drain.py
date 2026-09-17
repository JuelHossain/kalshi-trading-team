"""The error box must be clearable, or one error halts the engine forever.

authorize_cycle refuses to run while synapse.errors holds anything. That is
the intended safety latch, but nothing could empty it: Synapse.clear_all was
a stub with no body, and no endpoint drained the box. A single recoverable
error -- a model 404, a paused analytics project -- therefore bricked the
engine until someone deleted rows from SQLite by hand.
"""

import pytest
from core.synapse import Synapse, SynapseError


@pytest.fixture
def synapse(tmp_path):
    return Synapse(db_path=str(tmp_path / "test_synapse.db"))


def _error(code: str = "BOOM") -> SynapseError:
    return SynapseError(
        agent_name="TEST",
        code=code,
        message=f"{code} happened",
        severity="CRITICAL",
        domain="SYSTEM",
    )


class TestDrainErrors:
    @pytest.mark.asyncio
    async def test_drain_empties_the_box(self, synapse):
        await synapse.errors.push(_error("ONE"))
        await synapse.errors.push(_error("TWO"))
        assert await synapse.errors.size() == 2

        removed = await synapse.drain_errors()

        assert removed == 2
        assert await synapse.errors.size() == 0

    @pytest.mark.asyncio
    async def test_draining_an_empty_box_is_not_an_error(self, synapse):
        assert await synapse.drain_errors() == 0

    @pytest.mark.asyncio
    async def test_drain_leaves_the_work_queues_alone(self, synapse):
        """Clearing errors must not silently discard pending trades."""
        await synapse.errors.push(_error())
        before = await synapse.opportunities.size(), await synapse.executions.size()

        await synapse.drain_errors()

        after = await synapse.opportunities.size(), await synapse.executions.size()
        assert before == after

    @pytest.mark.asyncio
    async def test_the_box_is_usable_again_after_draining(self, synapse):
        await synapse.errors.push(_error("FIRST"))
        await synapse.drain_errors()

        await synapse.errors.push(_error("SECOND"))

        assert await synapse.errors.size() == 1


class TestClearAll:
    @pytest.mark.asyncio
    async def test_clear_all_empties_every_queue(self, synapse):
        """clear_all was a stub, so an emergency wipe silently did nothing."""
        await synapse.errors.push(_error())
        assert await synapse.errors.size() == 1

        await synapse.clear_all()

        assert await synapse.errors.size() == 0
        assert await synapse.opportunities.size() == 0
        assert await synapse.executions.size() == 0

    @pytest.mark.asyncio
    async def test_clear_all_is_idempotent(self, synapse):
        await synapse.clear_all()
        await synapse.clear_all()
        assert await synapse.errors.size() == 0


class TestQueueClear:
    @pytest.mark.asyncio
    async def test_clear_reports_how_many_it_removed(self, synapse):
        for i in range(3):
            await synapse.errors.push(_error(f"E{i}"))

        assert await synapse.errors.clear() == 3
