import pytest
from http_api.routes import activate_kill_switch, deactivate_kill_switch

from engine.main import GhostEngine


@pytest.mark.asyncio
async def test_ragnarok_emergency_lockdown(synapse):
    """Verify that Ragnarok protocol triggers kill switch and halts engine."""
    # Note: Real Ragnarok calls kalshi_client.close_all_positions()
    # In Demo mode, this should be safe.

    engine = GhostEngine()
    engine.synapse = synapse
    await engine.vault.initialize(50000)

    assert await engine.authorize_cycle() is True

    # Drive the /kill-switch handler itself (trigger_ragnarok sets
    # manual_kill_switch directly rather than calling activate_kill_switch,
    # but the two set the same flag, and this is the handler the cockpit's
    # Kill Switch button actually posts to).
    await activate_kill_switch(engine)(None)

    # activate_kill_switch already clears last_cycle_time itself (routes.py),
    # which is what lets the immediate authorize_cycle() call below miss the
    # 30s rate limiter (core.constants.MIN_CYCLE_INTERVAL_SECONDS) and be
    # refused by manual_kill_switch instead. The explicit reset here is just
    # a guard against that line being removed from the handler later --
    # without it, this assertion would start passing for the rate limiter's
    # reasons even if the kill-switch check in authorize_cycle were deleted.
    engine.last_cycle_time = None
    assert await engine.authorize_cycle() is False
    print("\n[RAGNAROK] Success: Engine halted after kill switch.")

    # And lifting it lets cycles resume, confirming the refusal really was
    # the kill switch and not some other halt tripped along the way.
    await deactivate_kill_switch(engine)(None)
    engine.last_cycle_time = None
    assert await engine.authorize_cycle() is True
