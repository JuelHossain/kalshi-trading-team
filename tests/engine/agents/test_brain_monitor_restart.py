"""STOP_AUTOPILOT then START_AUTOPILOT must not leave the Brain's queue stuck.

Regression for a live defect: monitor_queue's `while not stop_requested()`
exits for good once STOP_AUTOPILOT sets the flag, and nothing reset it or
replaced the task on a later START_AUTOPILOT. After one stop/start cycle the
opportunity queue had a consumer subscribed to nothing: every market Senses
found from then on sat in Synapse forever while the engine reported healthy.
"""

import asyncio
import os
from unittest.mock import patch

import pytest
from agents.brain import BrainAgent
from core.bus import EventBus
from core.synapse import MarketData, Opportunity, Synapse


async def _settled(read, quiet_for: float = 0.2, timeout: float = 5.0):
    """Poll until `read()` holds steady for `quiet_for` seconds. See
    test_agent_flow_control.py for why a fixed sleep is the wrong tool here.
    """
    deadline = asyncio.get_event_loop().time() + timeout
    previous = await read()
    stable_since = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(0.02)
        current = await read()
        now = asyncio.get_event_loop().time()
        if current != previous:
            previous, stable_since = current, now
        elif now - stable_since >= quiet_for:
            return current
    return previous


def _opportunity(ticker: str) -> Opportunity:
    return Opportunity(
        ticker=ticker,
        market_data=MarketData(
            ticker=ticker,
            title="t",
            subtitle="s",
            yes_price=50,
            no_price=50,
            volume=1000,
            expiration="2099-01-01",
        ),
    )


@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def synapse(tmp_path):
    return Synapse(db_path=str(tmp_path / "brain_restart.db"))


@pytest.mark.asyncio
async def test_queue_drains_again_after_stop_then_start(bus, synapse):
    with patch.dict(os.environ, {}, clear=True):
        brain = BrainAgent(3, bus, synapse=synapse)
    await brain.setup()

    # Stop, the way /autopilot/stop and /cancel do. publish awaits every
    # subscriber, so on_system_control has already run by the time this
    # returns -- stop_requested is set, though the loop may still be mid-sleep
    # before it notices.
    await bus.publish("SYSTEM_CONTROL", {"action": "STOP_AUTOPILOT"}, "TEST")
    assert brain.stop_requested is True

    # A market found while autopilot is off must not be silently lost.
    await synapse.opportunities.push(_opportunity("KXTEST-STOPPED"))

    # Restart, the way /autopilot/start does (Soul's on_system_control).
    await bus.publish("SYSTEM_CONTROL", {"action": "START_AUTOPILOT"}, "TEST")

    remaining = await _settled(synapse.opportunities.size)
    assert remaining == 0, "the queue must drain once the monitor loop is running again"
    assert brain.stop_requested is False
    assert brain._monitoring_task is not None and not brain._monitoring_task.done()


@pytest.mark.asyncio
async def test_start_autopilot_is_a_noop_when_already_running(bus, synapse):
    """START_AUTOPILOT while the loop is healthy must not replace or duplicate it."""
    with patch.dict(os.environ, {}, clear=True):
        brain = BrainAgent(3, bus, synapse=synapse)
    await brain.setup()
    original_task = brain._monitoring_task

    await bus.publish("SYSTEM_CONTROL", {"action": "START_AUTOPILOT"}, "TEST")
    await asyncio.sleep(0.05)

    assert brain._monitoring_task is original_task
    assert not original_task.done()
