"""A scan that finds nothing must not leave Senses stuck forever.

Regression for a live deadlock: start_scan ran exactly once per process
(guarded by _initial_scan_done), and the only other route back into a scan,
REQUEST_RESTOCK, is sent by the Brain only after enough vetoes -- which needs
an opportunity queue that a stuck Senses will never fill. If the one-and-only
scan found nothing, both paths back to a scan were closed for the life of the
process. Confirmed live 2026-09-18: the first scan found 0 markets and the
engine ran ~500 cycles with nothing to analyse, reporting healthy the whole
time.

The fix adds a narrow rescan: on PREFLIGHT_COMPLETE, if the stock buffer and
the opportunity queue are both empty and a cooldown has elapsed, scan again.
The cooldown keeps a persistently empty result (a real Kalshi outage, a quiet
market) from re-walking the listing every 30s cycle -- see
test_agent_flow_control.py::test_senses_guard for the companion invariant
this must not break: a healthy stock buffer must not be re-scanned every
cycle.
"""

import pytest
from agents.senses import SensesAgent
from core.bus import EventBus
from core.synapse import Synapse


def _market(ticker: str, volume: int = 5000) -> dict:
    return {
        "ticker": ticker,
        "yes_bid_dollars": "0.40",
        "yes_ask_dollars": "0.44",
        "volume_fp": str(volume),
    }


class _FakeKalshiClient:
    """Returns each queued page in order; an empty list means "nothing found"."""

    def __init__(self, pages: list[list[dict]]):
        self._pages = list(pages)
        self.calls = 0

    async def get_markets_page(self, **kwargs):
        self.calls += 1
        page = self._pages.pop(0) if self._pages else []
        return page, None


@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def synapse(tmp_path):
    return Synapse(db_path=str(tmp_path / "rescan.db"))


@pytest.mark.asyncio
async def test_empty_first_scan_does_not_deadlock_after_cooldown(bus, synapse):
    """A first scan that finds nothing must be retried once the cooldown passes."""
    client = _FakeKalshiClient(pages=[[], [_market("KXTEST-A")]])
    senses = SensesAgent(2, bus, kalshi_client=client, synapse=synapse)
    senses.RESCAN_COOLDOWN_SECONDS = 0  # elapses immediately for the test
    await senses.setup()

    await bus.publish("PREFLIGHT_COMPLETE", {}, "TEST")
    assert await synapse.opportunities.size() == 0, "the first (empty) scan queues nothing"
    assert senses._initial_scan_done is True

    await bus.publish("PREFLIGHT_COMPLETE", {}, "TEST")
    assert await synapse.opportunities.size() == 1, "the rescan must pick up the fresh market"
    assert client.calls == 2, "a rescan was actually attempted, not skipped"


@pytest.mark.asyncio
async def test_rescan_respects_its_cooldown(bus, synapse):
    """Back-to-back empty PREFLIGHT_COMPLETEs must not each hit Kalshi."""
    client = _FakeKalshiClient(pages=[[], [_market("KXTEST-B")]])
    senses = SensesAgent(2, bus, kalshi_client=client, synapse=synapse)
    senses.RESCAN_COOLDOWN_SECONDS = 3600  # effectively never, for this test
    await senses.setup()

    await bus.publish("PREFLIGHT_COMPLETE", {}, "TEST")
    await bus.publish("PREFLIGHT_COMPLETE", {}, "TEST")
    await bus.publish("PREFLIGHT_COMPLETE", {}, "TEST")

    assert client.calls == 1, "the cooldown must suppress a rescan on every cycle"
    assert await synapse.opportunities.size() == 0


@pytest.mark.asyncio
async def test_healthy_stock_is_not_rescanned(bus, synapse):
    """test_senses_guard's invariant, restated: unqueued stock must not be re-fetched."""
    client = _FakeKalshiClient(pages=[[_market(f"KXTEST-{i}") for i in range(3)]])
    senses = SensesAgent(2, bus, kalshi_client=client, synapse=synapse)
    senses.RESCAN_COOLDOWN_SECONDS = 0
    senses.QUEUE_BATCH_SIZE = 1  # leaves stock behind after the first queue
    await senses.setup()

    await bus.publish("PREFLIGHT_COMPLETE", {}, "TEST")
    assert senses.market_stock, "stock should remain after queuing one batch"

    await bus.publish("PREFLIGHT_COMPLETE", {}, "TEST")
    assert client.calls == 1, "stock on hand must not trigger another Kalshi fetch"


@pytest.mark.asyncio
async def test_no_rescan_while_brain_still_has_work(bus, synapse):
    """An empty stock buffer with a non-empty opportunity queue must not rescan."""
    from core.synapse import MarketData, Opportunity

    await synapse.opportunities.push(
        Opportunity(
            ticker="KXTEST-PENDING",
            market_data=MarketData(
                ticker="KXTEST-PENDING",
                title="t",
                subtitle="s",
                yes_price=50,
                no_price=50,
                volume=1000,
                expiration="2099-01-01",
            ),
        )
    )
    client = _FakeKalshiClient(pages=[[_market("KXTEST-C")]])
    senses = SensesAgent(2, bus, kalshi_client=client, synapse=synapse)
    senses._initial_scan_done = True  # already past the first scan
    senses.RESCAN_COOLDOWN_SECONDS = 0

    assert await senses._should_rescan() is False
