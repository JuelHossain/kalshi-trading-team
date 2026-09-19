"""The Brain-to-Senses restock path, driven end to end.

Regression for a coverage gap: nothing exercised REQUEST_RESTOCK, the only
route from "the Brain vetoed enough opportunities in a row" back to "Senses
fetches fresh markets from Kalshi" (see monitor.handle_restock_trigger and
SensesAgent.on_restock_request). A break anywhere on that path -- the
publish never firing, Senses never subscribing to it, or the low-stock fetch
branch never running -- previously left the full backend suite green.

This gap cannot deadlock the engine any more: test_senses_rescan.py covers
the empty-first-scan case that used to (Senses now rescans on its own after
a cooldown). But a silent break here would still slow restocking: fresh
markets would arrive only after the stock buffer and the queue had both
drained and start_scan's rescan cooldown had passed, not when the Brain
asked for them, and nothing would say why.

Drives the real wiring end to end: BrainAgent.process_single_item_from_queue
-> handle_restock_trigger -> EventBus.publish("REQUEST_RESTOCK") ->
SensesAgent.on_restock_request -> the Kalshi client. run_debate is stubbed
to force a VETO on every opportunity, so no AI call and no network happen;
everything downstream of that stub is the production code path.
"""

import asyncio

import pytest
from agents.brain import BrainAgent
from agents.senses import SensesAgent
from core import constants
from core.synapse import MarketData, Opportunity

from tests.engine.support import _debate, _FakeKalshiClient, _market


async def _push_opportunity(synapse, ticker: str):
    await synapse.opportunities.push(
        Opportunity(
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
    )


async def _drain_vetoes(brain, synapse, n: int):
    """Push and process `n` opportunities that the stubbed debate vetoes."""
    for i in range(n):
        await _push_opportunity(synapse, f"KXVETO-{i}")
        await brain.process_single_item_from_queue()


def _recorder():
    """A bus subscriber callback that records every message it is sent.

    The returned `event` is set from inside the bus's own dispatch --
    `EventBus.publish` awaits every subscriber before it returns (see
    core/bus.py) -- so awaiting `event.wait()` cannot observe a publish
    that is still in flight, the way polling application state can.
    """
    messages = []
    event = asyncio.Event()

    async def on_message(message):
        messages.append(message)
        event.set()

    return on_message, messages, event


@pytest.mark.asyncio
async def test_brain_restocks_senses_after_threshold_vetoes(bus, synapse):
    """RESTOCK_THRESHOLD_VETO_COUNT vetoes in a row must reach Kalshi via Senses."""
    client = _FakeKalshiClient(pages=[[_market(f"KXR-{i}") for i in range(3)]])
    senses = SensesAgent(2, bus, kalshi_client=client, synapse=synapse)
    senses._initial_scan_done = True  # past the first scan; stock stays empty
    senses.QUEUE_BATCH_SIZE = 3
    await senses.setup()  # real REQUEST_RESTOCK subscription, not a mock

    on_restock, restock_messages, _unused_event = _recorder()
    on_ready, ready_messages, ready_seen = _recorder()
    await bus.subscribe("REQUEST_RESTOCK", on_restock)
    await bus.subscribe("OPPORTUNITIES_READY", on_ready)

    brain = BrainAgent(3, bus, synapse=synapse)
    brain.run_debate = _debate(confidence=0)  # every opportunity is VETOED

    await _drain_vetoes(brain, synapse, constants.RESTOCK_THRESHOLD_VETO_COUNT)

    # REQUEST_RESTOCK's handler runs on a fire_and_forget task, not inline
    # (see handle_restock_trigger's comment on why). Senses publishes
    # OPPORTUNITIES_READY only after queue_from_stock has finished queueing
    # every market (see on_restock_request), so waiting for that message --
    # rather than polling the queue size -- cannot observe a partially
    # filled queue. Polling `size() >= 1` did exactly that under a slow
    # (disk-backed) Synapse.push: it could return once 1 or 2 of the 3
    # markets were queued, and a later `== 3` assertion then flaked.
    await asyncio.wait_for(ready_seen.wait(), timeout=5.0)

    assert len(restock_messages) == 1, "expected exactly one REQUEST_RESTOCK"
    assert restock_messages[0].sender == "BRAIN"
    assert client.calls == 1, "the veto threshold did not pull a fresh scan through Kalshi"
    assert await synapse.opportunities.size() == 3, "the fresh markets were never queued"
    assert brain._dumped_count == 0, "the veto counter must reset once a restock is requested"
    assert ready_messages[0].payload["count"] == 3


@pytest.mark.asyncio
async def test_brain_does_not_restock_below_threshold(bus, synapse):
    """One veto short of the threshold must not touch Kalshi."""
    client = _FakeKalshiClient(pages=[[_market("KXR-0")]])
    senses = SensesAgent(2, bus, kalshi_client=client, synapse=synapse)
    senses._initial_scan_done = True
    await senses.setup()

    brain = BrainAgent(3, bus, synapse=synapse)
    brain.run_debate = _debate(confidence=0)

    await _drain_vetoes(brain, synapse, constants.RESTOCK_THRESHOLD_VETO_COUNT - 1)
    await asyncio.sleep(0.1)  # give any stray fire_and_forget task a chance to run

    assert client.calls == 0, "Kalshi was hit before the veto threshold was reached"
    assert await synapse.opportunities.size() == 0
