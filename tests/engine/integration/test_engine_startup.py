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

import pytest

from core.bus import EventBus
from core.error_manager import ErrorManager
from core.synapse import Synapse
from core.vault import RecursiveVault


AGENT_CASES = [
    ("soul", lambda bus, deps: __import__("agents.soul", fromlist=["SoulAgent"]).SoulAgent(
        1, bus, vault=deps["vault"], synapse=deps["synapse"], error_manager=deps["em"])),
    ("senses", lambda bus, deps: __import__("agents.senses", fromlist=["SensesAgent"]).SensesAgent(
        2, bus, kalshi_client=None, synapse=deps["synapse"], error_manager=deps["em"])),
    ("brain", lambda bus, deps: __import__("agents.brain", fromlist=["BrainAgent"]).BrainAgent(
        3, bus, synapse=deps["synapse"], error_manager=deps["em"])),
    ("hand", lambda bus, deps: __import__("agents.hand", fromlist=["HandAgent"]).HandAgent(
        4, bus, vault=deps["vault"], kalshi_client=None, synapse=deps["synapse"],
        error_manager=deps["em"])),
    ("gateway", lambda bus, deps: __import__("agents.gateway", fromlist=["GatewayAgent"]).GatewayAgent(
        5, bus, vault=deps["vault"], error_manager=deps["em"])),
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
    assert agent.error_manager is deps["em"], (
        f"{name} did not forward error_manager to BaseAgent"
    )


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
    assert names == {"SOUL", "SENSES", "BRAIN", "HAND", "GATEWAY"}, (
        f"engine did not build all five agents, got {names}"
    )
    assert all(a.error_manager is not None for a in engine.agents)
