"""Senses must not hand the Brain the same market every restock.

Observed live: NYGLAR-NYG, SEAARI-ARI and MIASF-MIA each analysed twice in
one cycle. Restock re-fetches the top of the same volume ranking, so the
same tickers came back, cost a grounded Gemini call each, and the same
approval reached the Hand a second time -- which, with the position guard
blind to paper fills, became a second position.
"""

import time

import pytest
from agents.senses.agent import SensesAgent
from agents.senses.scanner import fetch_kalshi_markets


def _market(ticker: str, volume: float = 5000) -> dict:
    return {
        "ticker": ticker,
        "yes_bid_dollars": "0.3300",
        "yes_ask_dollars": "0.3500",
        "volume_fp": f"{volume:.2f}",
    }


class _PagedClient:
    """Serves markets in pages so paging-past-exclusions can be observed."""

    def __init__(self, pages):
        self.pages = pages
        self.calls = 0

    async def get_markets_page(
        self,
        limit,
        status="open",
        min_close_ts=None,
        max_close_ts=None,
        cursor=None,
        mve_filter=None,
    ):
        idx = int(cursor) if cursor else 0
        self.calls += 1
        page = self.pages[idx] if idx < len(self.pages) else []
        nxt = str(idx + 1) if idx + 1 < len(self.pages) else None
        return page, nxt


async def _log(message, level="INFO"):
    pass


@pytest.fixture
def senses():
    return SensesAgent.__new__(SensesAgent)


class TestRecentlyQueuedIsRemembered:
    def test_a_queued_ticker_is_excluded(self, senses):
        senses.mark_queued("A")
        assert "A" in senses.recently_queued()

    def test_nothing_queued_means_nothing_excluded(self, senses):
        assert senses.recently_queued() == frozenset()

    def test_exclusion_expires(self, senses, monkeypatch):
        senses.mark_queued("A")
        senses._queued_at()["A"] = time.time() - senses.REQUEUE_AFTER_SECONDS - 1

        assert "A" not in senses.recently_queued()

    def test_expired_entries_are_dropped_not_kept_forever(self, senses):
        senses.mark_queued("A")
        senses._queued_at()["A"] = 0

        senses.recently_queued()

        assert "A" not in senses._queued_at()


class TestFetchPagesPastExcludedTickers:
    @pytest.mark.asyncio
    async def test_excluded_tickers_are_not_returned(self):
        client = _PagedClient([[_market("A"), _market("B"), _market("C")]])

        got = await fetch_kalshi_markets(client, _log, needed=3, exclude={"B"})

        assert [m["ticker"] for m in got] == ["A", "C"]

    @pytest.mark.asyncio
    async def test_the_regression_it_keeps_paging_to_find_new_markets(self):
        """If the whole first page was queued last time, look further."""
        client = _PagedClient(
            [
                [_market("A"), _market("B")],
                [_market("C"), _market("D")],
            ]
        )

        got = await fetch_kalshi_markets(client, _log, needed=2, exclude={"A", "B"})

        assert [m["ticker"] for m in got] == ["C", "D"]
        assert client.calls == 2

    @pytest.mark.asyncio
    async def test_it_keeps_the_best_volume_not_the_first_found(self):
        """The listing is not in volume order, so stopping at the first
        `needed` tradeable markets took an arbitrary slice."""
        client = _PagedClient(
            [
                [_market("A", volume=300), _market("B", volume=400)],
                [_market("C", volume=9000)],
            ]
        )

        got = await fetch_kalshi_markets(client, _log, needed=2)

        assert [m["ticker"] for m in got] == ["C", "B"]
        assert client.calls == 2

    @pytest.mark.asyncio
    async def test_no_exclusions_is_the_default(self):
        client = _PagedClient([[_market("A")]])

        got = await fetch_kalshi_markets(client, _log, needed=1)

        assert [m["ticker"] for m in got] == ["A"]
