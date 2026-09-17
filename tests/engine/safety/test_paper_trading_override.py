"""IS_PAPER_TRADING must pin cycles to paper on the server.

Whether a cycle trades for real arrives in the request body from the browser:
routes.trigger_cycle and GhostEngine._handle_cycle_request both read
`isPaperTrading` from the payload. ecosystem.config.cjs set IS_PAPER_TRADING
with the comment "Default to paper trading", but nothing read it, so the
process-level safety setting had no effect at all.
"""

import contextlib

import pytest


@pytest.fixture
def engine(monkeypatch, test_db):
    import main
    from core.synapse import Synapse

    eng = main.GhostEngine()
    monkeypatch.setattr(eng, "synapse", Synapse(db_path=test_db))

    seen = {}

    class _Progress:
        def update_phase(self, *_a, **_k):
            pass

    class _Ctx:
        def __enter__(self):
            return _Progress()

        def __exit__(self, *_a):
            return False

    def capture(_cycle, is_paper):
        seen["is_paper"] = is_paper
        raise _Stop

    monkeypatch.setattr(eng.display, "cycle_progress", capture)
    return eng, seen


class _Stop(Exception):
    """Ends the cycle once the paper/live decision has been observed."""


async def _run(eng, seen, requested):
    # The stub raises from cycle_progress itself, before the engine's own
    # try/finally, so the in-progress flag is not cleared for us here. The
    # engine does reset it on a real exception (main.py finally block).
    eng.is_processing = False
    with contextlib.suppress(_Stop):
        await eng.execute_single_cycle(is_paper_trading=requested)
    return seen.get("is_paper")


@pytest.mark.asyncio
async def test_live_request_is_forced_to_paper_when_set(engine, monkeypatch):
    """The whole point: a live request must not trade live."""
    eng, seen = engine
    monkeypatch.setenv("IS_PAPER_TRADING", "true")

    assert await _run(eng, seen, requested=False) is True


@pytest.mark.asyncio
async def test_live_request_is_honoured_when_unset(engine, monkeypatch):
    """Unset means the request decides, which is the previous behaviour."""
    eng, seen = engine
    monkeypatch.delenv("IS_PAPER_TRADING", raising=False)

    assert await _run(eng, seen, requested=False) is False


@pytest.mark.asyncio
async def test_paper_request_stays_paper_either_way(engine, monkeypatch):
    eng, seen = engine
    monkeypatch.setenv("IS_PAPER_TRADING", "true")
    assert await _run(eng, seen, requested=True) is True

    seen.clear()
    monkeypatch.delenv("IS_PAPER_TRADING", raising=False)
    assert await _run(eng, seen, requested=True) is True


@pytest.mark.asyncio
async def test_cycle_arms_the_order_path_for_live(engine, monkeypatch):
    """The decision must reach the order path, not just the display.

    This is the defect these tests originally missed: every assertion above
    passes while `is_paper_trading` goes only to the progress bar and the event
    payloads. The switch consulted by KalshiClient.place_order is what actually
    decides whether money moves, so that is what has to agree.
    """
    from core import trading_mode

    eng, seen = engine
    monkeypatch.delenv("IS_PAPER_TRADING", raising=False)
    trading_mode.set_live(False)

    assert await _run(eng, seen, requested=False) is False
    assert (
        trading_mode.is_live() is True
    ), "cycle reported LIVE but the order path was left in paper mode"


@pytest.mark.asyncio
async def test_cycle_disarms_the_order_path_for_paper(engine, monkeypatch):
    """A paper cycle must leave the order path unable to place a real order."""
    from core import trading_mode

    eng, seen = engine
    monkeypatch.delenv("IS_PAPER_TRADING", raising=False)
    trading_mode.set_live(True)

    assert await _run(eng, seen, requested=True) is True
    assert (
        trading_mode.is_live() is False
    ), "cycle reported PAPER while the order path was still armed for live"


@pytest.mark.asyncio
async def test_override_disarms_the_order_path(engine, monkeypatch):
    """IS_PAPER_TRADING must disarm the order path, not merely relabel the cycle."""
    from core import trading_mode

    eng, seen = engine
    monkeypatch.setenv("IS_PAPER_TRADING", "true")
    trading_mode.set_live(True)

    assert await _run(eng, seen, requested=False) is True
    assert (
        trading_mode.is_live() is False
    ), "IS_PAPER_TRADING relabelled the cycle but left live orders armed"
