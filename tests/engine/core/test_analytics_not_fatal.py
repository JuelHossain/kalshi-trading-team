"""Analytics logging must never block trade execution.

BrainAgent.queue_for_execution awaits log_to_db between appending an approved
trade and publishing EXECUTION_READY -- the event HandAgent places orders on.
log_to_db raised when Supabase was unconfigured, so the publish was skipped and
an approved trade was silently never executed. An insert failure was already
tolerated; only the unconfigured case was fatal.
"""

import core.db
import pytest
from core.bus import EventBus


@pytest.mark.asyncio
async def test_log_to_db_does_not_raise_when_supabase_unconfigured(monkeypatch):
    monkeypatch.setattr(core.db, "supabase", None)
    await core.db.log_to_db("execution_queue", {"signal_id": "x"})  # must not raise


@pytest.mark.asyncio
async def test_log_to_db_swallows_insert_errors(monkeypatch):
    """A configured-but-failing Supabase was already tolerated; keep it that way."""

    class Boom:
        def table(self, _name):
            raise RuntimeError("supabase down")

    monkeypatch.setattr(core.db, "supabase", Boom())
    await core.db.log_to_db("execution_queue", {"signal_id": "x"})  # must not raise


@pytest.mark.asyncio
async def test_execution_ready_is_published_without_supabase(monkeypatch):
    """The real defect: the Hand agent's trigger must still fire."""
    monkeypatch.setattr(core.db, "supabase", None)

    from agents.brain.agent import BrainAgent

    bus = EventBus()
    published = []

    async def capture(payload, *_args, **_kwargs):
        published.append(payload)

    await bus.subscribe("EXECUTION_READY", capture)

    brain = BrainAgent(3, bus, synapse=None)
    await brain.queue_for_execution(
        {
            "ticker": "TEST-TICKER",
            "confidence": 90,
            "monte_carlo_ev": 12.5,
            "reasoning": "unit test",
            "suggested_size": 10,
        }
    )

    assert published, "EXECUTION_READY was not published; the Hand agent never fires"
