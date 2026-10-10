"""The 8-page/4000-market scan ceiling, and why it kept finding nothing.

Kalshi's listing inside a close window is dominated by KXMVE combo shards,
filtered out client-side in is_tradeable. Every one of them still had to be
downloaded and paged past, and four consecutive live scans on 2026-09-18 hit
the 8-page ceiling and returned 3, 2, 1 and then 0 tradeable markets -- each
logged as "from 4000 scanned" -- while real, liquid markets past page 8 were
never reached. That fed straight into the restock deadlock covered by
test_senses_rescan.py.

Kalshi's GET /markets accepts mve_filter=exclude, which drops combo shards
server-side instead of the scanner paging past thousands of them. These
tests cover that it is actually requested, and the two related defects found
alongside it: a mid-walk page failure discarding markets already collected,
and no signal in the logs distinguishing "the market genuinely thinned out"
from "the scan gave up with more still unseen".
"""

import pytest
from agents.senses.scanner import MAX_MARKET_PAGES, fetch_kalshi_markets


def _market(ticker: str, volume: int = 5000) -> dict:
    return {
        "ticker": ticker,
        "yes_bid_dollars": "0.40",
        "yes_ask_dollars": "0.44",
        "volume_fp": str(volume),
    }


class _RecordingClient:
    """Serves queued pages and records every mve_filter it was called with."""

    def __init__(self, pages, fail_on_call: int | None = None):
        self._pages = list(pages)
        self.mve_filters_seen = []
        self.fail_on_call = fail_on_call
        self.calls = 0

    async def get_markets_page(self, mve_filter=None, cursor=None, **_kwargs):
        self.calls += 1
        self.mve_filters_seen.append(mve_filter)
        if self.fail_on_call == self.calls:
            raise RuntimeError("simulated transient Kalshi error")
        idx = int(cursor) if cursor else 0
        page = self._pages[idx] if idx < len(self._pages) else []
        nxt = str(idx + 1) if idx + 1 < len(self._pages) else None
        return page, nxt


class _Log:
    def __init__(self):
        self.lines: list[tuple[str, str]] = []

    async def __call__(self, message, level="INFO"):
        self.lines.append((level, message))


@pytest.mark.asyncio
async def test_mve_filter_exclude_is_requested():
    """The scan must ask Kalshi to exclude combo shards, not filter 4000 of them client-side."""
    client = _RecordingClient(pages=[[_market("A")]])
    log = _Log()

    await fetch_kalshi_markets(client, log, needed=1)

    assert client.mve_filters_seen == ["exclude"]


@pytest.mark.asyncio
async def test_partial_results_survive_a_mid_walk_failure():
    """A page failing partway through must not discard markets already found."""
    pages = [[_market("A")], [_market("B")]]
    client = _RecordingClient(pages=pages, fail_on_call=2)
    log = _Log()

    got = await fetch_kalshi_markets(client, log, needed=5)

    assert [m["ticker"] for m in got] == [
        "A"
    ], "the first page's market must survive the second page's failure"
    assert any("Kalshi fetch error" in msg for _lvl, msg in log.lines)


@pytest.mark.asyncio
async def test_ceiling_hit_is_logged_when_more_remains():
    """Exhausting all pages with the cursor still live must say so."""
    # Each page must be non-empty (an empty page means the cursor genuinely
    # ran out) but never enough to satisfy `needed`, and there must be more
    # pages than the ceiling so the cursor is never exhausted either.
    pages = [[_market(f"Z{i}")] for i in range(MAX_MARKET_PAGES + 2)]
    client = _RecordingClient(pages=pages)
    log = _Log()

    await fetch_kalshi_markets(client, log, needed=100)

    assert client.calls == MAX_MARKET_PAGES
    assert any("ceiling" in msg.lower() for _lvl, msg in log.lines)


@pytest.mark.asyncio
async def test_no_ceiling_warning_when_the_cursor_simply_runs_out():
    """A market that genuinely has nothing left must not be reported as a ceiling hit."""
    client = _RecordingClient(pages=[[_market("A")]])  # one page, then cursor is None
    log = _Log()

    await fetch_kalshi_markets(client, log, needed=100)

    assert not any("ceiling" in msg.lower() for _lvl, msg in log.lines)


@pytest.mark.asyncio
async def test_the_whole_window_is_walked_and_ranked_by_volume():
    """The most liquid markets can sit on any page; the scan must reach them."""
    pages = [[_market(f"LOW{p}", volume=250)] for p in range(5)]
    pages.append([_market("DEEP", volume=1_000_000)])
    client = _RecordingClient(pages=pages)
    log = _Log()

    got = await fetch_kalshi_markets(client, log, needed=2)

    assert client.calls == len(pages)
    assert got[0]["ticker"] == "DEEP"
    assert not any("ceiling" in msg.lower() for _lvl, msg in log.lines)


def test_pages_are_kalshis_maximum_size():
    from agents.senses import scanner

    assert scanner.MARKET_PAGE_SIZE == 1000
