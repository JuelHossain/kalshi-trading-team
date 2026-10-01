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


async def _authorize(monkeypatch, vault, balance, is_paper_trading=False):
    """Run the real authorize_cycle against a stub balance.

    is_paper_trading defaults to False -- "drive everything off the real
    balance" -- which is what every call in this file made before
    authorize_cycle gained the parameter, and what it must keep meaning:
    these tests assert the real-money safety net (the hard floor, the kill
    switch) works whether or not a cycle happens to be trading paper.
    """
    import main

    engine = main.GhostEngine.__new__(main.GhostEngine)
    engine.vault = vault
    engine.manual_kill_switch = False
    engine.last_cycle_time = None
    engine.synapse = None
    monkeypatch.setattr(main, "kalshi_client", _Kalshi(balance))
    return await engine.authorize_cycle(is_paper_trading)


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


class TestThePaperBankrollDrivesAuthorizeCycleInPaperMode:
    """authorize_cycle used to overwrite vault.current_balance with the real
    Kalshi balance on every cycle, paper or live -- so a paper soak's
    spending never depleted the balance Kelly and the floor read, and
    neither the hard floor nor the kill switch could trip on a paper loss.

    In paper mode it must feed the vault the paper bankroll instead, while
    the real balance's own hard floor keeps gating regardless of mode: that
    is what protects the account, independent of what a paper soak believes
    it has.
    """

    @pytest.fixture(autouse=True)
    def clean_paper_book(self):
        from core import trading_mode

        trading_mode.reset_paper_positions()
        yield
        trading_mode.reset_paper_positions()

    @pytest.mark.asyncio
    async def test_a_paper_cycle_seeds_and_uses_the_paper_bankroll(self, vault, monkeypatch):
        from core import trading_mode

        assert trading_mode.paper_cash() is None

        authorized = await _authorize(monkeypatch, vault, 32813, is_paper_trading=True)

        assert authorized is True
        assert trading_mode.paper_cash() == 32813
        assert vault.current_balance == 32813

    @pytest.mark.asyncio
    async def test_paper_spending_persists_across_cycles(self, vault, monkeypatch):
        """The whole point: a paper stake must still be gone on the next
        cycle's floor check, unlike before, when the real balance reset the
        vault to the same figure every cycle."""
        from core import trading_mode

        await _authorize(monkeypatch, vault, 32813, is_paper_trading=True)
        trading_mode.adjust_paper_cash(-7_500)  # a $75 paper stake

        # A second cycle: the real Kalshi balance has not moved (paper
        # spending never touches it), but the vault this cycle actually
        # sizes against must reflect the paper spend, not reset to 32813.
        await _authorize(monkeypatch, vault, 32813, is_paper_trading=True)

        assert vault.current_balance == 32813 - 7_500

    @pytest.mark.asyncio
    async def test_the_real_hard_floor_still_gates_a_paper_cycle(self, vault, monkeypatch):
        """The real balance's floor check is a safety net that must not
        depend on what the paper bankroll believes it has."""
        from core import trading_mode

        trading_mode.seed_paper_cash(1_000_000)  # plenty of paper cash

        authorized = await _authorize(monkeypatch, vault, 20000, is_paper_trading=True)

        assert authorized is False, "real balance below the hard floor must still halt paper"

    @pytest.mark.asyncio
    async def test_the_paper_bankroll_can_also_trip_its_own_floor(self, vault, monkeypatch):
        """The other direction: real cash is fine, but paper trading has
        spent itself past the floor. Before this fix, nothing in paper mode
        could ever halt on the floor at all."""
        from core import trading_mode

        trading_mode.seed_paper_cash(vault.HARD_FLOOR_CENTS - 100)

        authorized = await _authorize(monkeypatch, vault, 32813, is_paper_trading=True)

        assert authorized is False

    @pytest.mark.asyncio
    async def test_a_live_cycle_is_unaffected_by_a_depleted_paper_bankroll(
        self, vault, monkeypatch
    ):
        """The default (is_paper_trading=False, what every other test in
        this file calls) must still mean "real balance drives everything",
        exactly as before authorize_cycle gained the parameter."""
        from core import trading_mode

        trading_mode.seed_paper_cash(0)  # paper trading has nothing left

        authorized = await _authorize(monkeypatch, vault, 32813, is_paper_trading=False)

        assert authorized is True
        assert vault.current_balance == 32813

    @pytest.mark.asyncio
    async def test_the_profit_lock_measures_the_paper_bankroll_against_itself(
        self, vault, monkeypatch
    ):
        """The paper bankroll is persisted and can carry accumulated P&L
        across a restart, while the vault's start_of_day_balance is only
        ever the real balance at *this* boot (vault.initialize, called once
        at boot with the real Kalshi balance -- see main.py). Comparing a
        restart's recovered paper cash against that real boot-time figure
        could trip the profit lock -- freezing the paper soak's own
        principal -- for a gap that has nothing to do with what this paper
        session itself made, and never re-trips for a paper session that
        starts behind the real balance but is genuinely profitable.

        Simulates a restart that recovered a paper bankroll ($60 ahead of
        the real balance, clearing the $50 default threshold) from disk.
        """
        from core import trading_mode

        trading_mode.seed_paper_cash(32813 + 6_000)  # a restart recovered this from disk

        authorized = await _authorize(monkeypatch, vault, 32813, is_paper_trading=True)

        assert authorized is True
        assert vault.is_locked is False, "must not lock on a gap that predates this session"

    @pytest.mark.asyncio
    async def test_the_profit_lock_still_trips_on_the_paper_bankrolls_own_profit(
        self, vault, monkeypatch
    ):
        """The other direction: the lock must still work for paper, measured
        from its own start-of-day, once *this* session's paper trading
        actually clears the threshold."""
        from core import trading_mode

        await _authorize(monkeypatch, vault, 32813, is_paper_trading=True)
        assert vault.is_locked is False

        trading_mode.adjust_paper_cash(6_000)  # this session's own $60 paper profit

        authorized = await _authorize(monkeypatch, vault, 32813, is_paper_trading=True)

        assert authorized is True
        assert vault.is_locked is True

    @pytest.mark.asyncio
    async def test_a_locked_paper_bankroll_does_not_lock_a_live_cycle(self, vault, monkeypatch):
        """The two latches must not bleed into each other either."""
        from core import trading_mode

        await _authorize(monkeypatch, vault, 32813, is_paper_trading=True)
        trading_mode.adjust_paper_cash(6_000)
        await _authorize(monkeypatch, vault, 32813, is_paper_trading=True)
        assert vault.is_locked is True

        authorized = await _authorize(monkeypatch, vault, 32813, is_paper_trading=False)

        assert authorized is True
        assert vault.is_locked is False
