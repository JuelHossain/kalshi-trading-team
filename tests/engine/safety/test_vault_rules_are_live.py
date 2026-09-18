"""The vault's capital rules must act while the engine runs, not only at boot.

Audit finding: authorize_cycle refreshed the balance with a plain
`vault.current_balance = ...`, and update_balance -- the only thing that
re-evaluates the 85% kill switch and the profit lock -- had no production
caller. So both were evaluated once, at boot: a balance falling through 85% of
principal mid-session tripped nothing, and a boot that could not fetch the
balance (vault initialised at $0) latched the kill switch for good because
authorize_cycle read it before refreshing. Sizing read get_available_balance,
so the profit lock froze nothing, and the hard floor was checked against the
balance before a trade, so one stake could carry it through.
"""

import pytest
import pytest_asyncio
from agents.hand.execution import calculate_kelly_stake, execute_order
from core.vault import RecursiveVault


@pytest_asyncio.fixture
async def vault():
    v = RecursiveVault(test_mode=True)
    v.PRINCIPAL_CAPITAL_CENTS = 30000
    v.KILL_SWITCH_THRESHOLD_PCT = 0.85
    v.HARD_FLOOR_CENTS = 25500
    await v.initialize(32813)
    return v


class _Kalshi:
    def __init__(self, balance):
        self.balance = balance

    async def get_balance(self):
        return self.balance


async def _authorize(monkeypatch, vault, balance):
    """Run the real authorize_cycle against a stub balance."""
    import main

    engine = main.GhostEngine.__new__(main.GhostEngine)
    engine.vault = vault
    engine.manual_kill_switch = False
    engine.last_cycle_time = None
    engine.synapse = None
    monkeypatch.setattr(main, "kalshi_client", _Kalshi(balance))
    return await engine.authorize_cycle()


class TestTheKillSwitchFollowsTheBalance:
    @pytest.mark.asyncio
    async def test_a_mid_session_fall_below_85_percent_trips_it(self, vault, monkeypatch):
        # 85% of $300 is $255, the same as the hard floor; lower the floor so
        # it is the kill switch, not the floor check, that refuses the cycle.
        vault.HARD_FLOOR_CENTS = 10000
        assert await _authorize(monkeypatch, vault, 20000) is False
        assert vault.kill_switch_active is True

    @pytest.mark.asyncio
    async def test_a_boot_at_zero_clears_once_a_real_balance_returns(self, monkeypatch):
        v = RecursiveVault(test_mode=True)
        v.PRINCIPAL_CAPITAL_CENTS = 30000
        v.KILL_SWITCH_THRESHOLD_PCT = 0.85
        v.HARD_FLOOR_CENTS = 25500
        await v.initialize(0)  # main.py's fallback when the boot fetch fails
        assert v.kill_switch_active is True

        assert await _authorize(monkeypatch, v, 32813) is True
        assert v.kill_switch_active is False


class TestSizingRespectsTheLockAndTheFloor:
    @pytest.mark.asyncio
    async def test_once_locked_only_house_money_is_tradeable(self, vault):
        vault.is_locked = True
        assert vault.get_tradeable_balance() == 32813 - 30000

    @pytest.mark.asyncio
    async def test_a_stake_is_clamped_above_the_floor(self, vault):
        headroom = 32813 - 25500
        stake = calculate_kelly_stake(
            0.9, 0.5, vault, max_stake_cents=1_000_000, probability=0.95, price_cents=40
        )
        assert 0 < stake <= headroom

    @pytest.mark.asyncio
    async def test_execute_order_refuses_a_stake_that_would_breach_the_floor(self, vault):
        stake = (32813 - 25500) + 100

        result = await execute_order(object(), vault, "KXA", 50, stake, max_stake_cents=1_000_000)

        assert result["success"] is False
        assert "hard floor" in result["error"]
