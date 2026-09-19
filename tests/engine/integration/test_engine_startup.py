"""The engine must be able to construct its agents.

Every agent test built agents directly -- SoulAgent(1, bus, vault) -- so none
of them exercised main.initialize_system(), which injects error_manager into
every constructor. No agent subclass accepted that argument, so the real
startup path raised TypeError on the first agent and shut the engine down:

    TypeError: SoulAgent.__init__() got an unexpected keyword argument
    'error_manager'
    SHUTDOWN PROTOCOL INITIATED: Failed to initialize agents

The suite was fully green while the bot could not start. These tests cover the
wiring rather than the parts.
"""

from unittest.mock import AsyncMock

import pytest
from core.bus import EventBus
from core.error_manager import ErrorManager
from core.synapse import Synapse
from core.vault import RecursiveVault

AGENT_CASES = [
    (
        "soul",
        lambda bus, deps: __import__("agents.soul", fromlist=["SoulAgent"]).SoulAgent(
            1, bus, vault=deps["vault"], synapse=deps["synapse"], error_manager=deps["em"]
        ),
    ),
    (
        "senses",
        lambda bus, deps: __import__("agents.senses", fromlist=["SensesAgent"]).SensesAgent(
            2, bus, kalshi_client=None, synapse=deps["synapse"], error_manager=deps["em"]
        ),
    ),
    (
        "brain",
        lambda bus, deps: __import__("agents.brain", fromlist=["BrainAgent"]).BrainAgent(
            3, bus, synapse=deps["synapse"], error_manager=deps["em"]
        ),
    ),
    (
        "hand",
        lambda bus, deps: __import__("agents.hand", fromlist=["HandAgent"]).HandAgent(
            4,
            bus,
            vault=deps["vault"],
            kalshi_client=None,
            synapse=deps["synapse"],
            error_manager=deps["em"],
        ),
    ),
    (
        "gateway",
        lambda bus, deps: __import__("agents.gateway", fromlist=["GatewayAgent"]).GatewayAgent(
            5, bus, vault=deps["vault"], error_manager=deps["em"]
        ),
    ),
]


@pytest.fixture
def deps(test_db):
    return {
        "vault": RecursiveVault(test_mode=True),
        "synapse": Synapse(db_path=test_db),
        "em": ErrorManager(),
    }


@pytest.mark.parametrize("name,build", AGENT_CASES, ids=[c[0] for c in AGENT_CASES])
def test_agent_accepts_injected_error_manager(name, build, deps):
    """main.initialize_system passes error_manager to every agent."""
    agent = build(EventBus(), deps)
    assert agent.error_manager is deps["em"], f"{name} did not forward error_manager to BaseAgent"


@pytest.mark.asyncio
async def test_initialize_system_builds_every_agent(monkeypatch, test_db):
    """The real startup path, end to end.

    This is the test that was missing: it goes through GhostEngine rather than
    constructing agents by hand, so a mismatch between main.py and any agent
    signature fails here.
    """
    import main

    engine = main.GhostEngine()
    monkeypatch.setattr(engine, "synapse", Synapse(db_path=test_db))

    await engine.initialize_system()

    names = {a.name for a in engine.agents}
    assert names == {
        "SOUL",
        "SENSES",
        "BRAIN",
        "HAND",
        "GATEWAY",
    }, f"engine did not build all five agents, got {names}"
    assert all(a.error_manager is not None for a in engine.agents)


@pytest.mark.asyncio
async def test_initialize_system_reloads_the_paper_book_and_bankroll(monkeypatch, test_db):
    """A restart must not empty the paper book or re-seed the paper bankroll
    from real cash.

    trading_mode.load_paper_positions() (the paper book and bankroll) lives
    only in memory otherwise: every restart source -- systemd's
    Restart=always, deploy/update.sh, a crash, POST /engine/restart -- would
    otherwise empty it, so has_open_position would answer "not held" for a
    market the soak already bought, and authorize_cycle's paper floor check
    would start back at the real balance every time.

    Driven through GhostEngine.initialize_system -- the real boot path --
    rather than calling trading_mode.load_paper_positions() directly, so
    deleting that call from main.py fails here rather than only in
    trading_mode's own unit tests (tests/engine/core/test_paper_positions.py).
    """
    import main
    from core import trading_mode

    trading_mode.reset_paper_positions()
    try:
        trading_mode.paper_fill("KXBOOT", "yes", 35, 7, "buy")
        trading_mode.seed_paper_cash(100_000)
        trading_mode.adjust_paper_cash(-2_000)  # some paper spending already happened

        # A restart is a fresh process: nothing survives but disk.
        trading_mode._paper_positions.clear()
        trading_mode._paper_cash = None
        assert trading_mode.paper_position("KXBOOT") == 0
        assert trading_mode.paper_cash() is None

        engine = main.GhostEngine()
        monkeypatch.setattr(engine, "synapse", Synapse(db_path=test_db))

        await engine.initialize_system()

        assert trading_mode.paper_position("KXBOOT") == 7
        assert trading_mode.paper_cash() == 98_000
    finally:
        trading_mode.reset_paper_positions()


@pytest.mark.asyncio
async def test_a_paper_cycle_feeds_the_vault_the_paper_bankroll(monkeypatch, test_db):
    """A paper cycle must size and floor-check against the paper bankroll,
    not the real Kalshi balance authorize_cycle also fetches this cycle.

    Driven through GhostEngine.execute_single_cycle(is_paper_trading=True) --
    the real production call (main.py's autopilot loop) -- rather than
    calling authorize_cycle(is_paper_trading=True) directly the way every
    paper-bankroll test in tests/engine/safety/test_vault_rules_are_live.py
    does. Those tests pass is_paper_trading explicitly, so they stay green
    even if execute_single_cycle stopped forwarding its own is_paper_trading
    argument down to `if not await self.authorize_cycle(is_paper_trading):`
    -- authorize_cycle's own default (False, real balance) would then take
    over and "paper vault resets to real cash every cycle" would come back
    with nothing here noticing. This drives the real call site instead.
    """
    import main
    from core import trading_mode

    class _Kalshi:
        async def get_balance(self):
            return 32_813  # the real demo balance -- must NOT end up in the vault

    trading_mode.reset_paper_positions()
    try:
        engine = main.GhostEngine()
        monkeypatch.setattr(engine, "synapse", Synapse(db_path=test_db))
        await engine.initialize_system()
        engine.hand.kalshi_client = AsyncMock()
        monkeypatch.setattr(main, "kalshi_client", _Kalshi())
        engine.last_cycle_time = None

        trading_mode.seed_paper_cash(40_000)  # a different figure than real cash

        await engine.execute_single_cycle(is_paper_trading=True)

        assert engine.vault.current_balance == 40_000
    finally:
        trading_mode.reset_paper_positions()
