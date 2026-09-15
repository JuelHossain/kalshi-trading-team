"""IS_PAPER_TRADING must pin cycles to paper on the server.

Whether a cycle trades for real arrives in the request body from the browser:
routes.trigger_cycle and GhostEngine._handle_cycle_request both read
`isPaperTrading` from the payload. ecosystem.config.cjs set IS_PAPER_TRADING
with the comment "Default to paper trading", but nothing read it, so the
process-level safety setting had no effect at all.
"""

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
    try:
        await eng.execute_single_cycle(is_paper_trading=requested)
    except _Stop:
        pass
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
