"""Kill switch and Cancel must halt cycles without ending the process.

activate_kill_switch and cancel_cycle both used to set engine.running = False.
That flag is the condition of main.run's own loop (`while self.running: sleep
1`), so clearing it did not halt trading -- it exited the whole Python
process. Under systemd's Restart=always plus the autopilot drop-in
(ExecStartPost calling POST /autopilot/start on every start), the engine came
back up within seconds with manual_kill_switch reset to its in-memory default
and autopilot re-armed: pressing Kill Switch or Cancel undid itself.

authorize_cycle already refuses every cycle while manual_kill_switch is set
(or, for Cancel, while autopilot is stopped) -- that is the actual halt, and
these tests exercise it through the same handlers routes.py registers rather
than hand-simulating the fix, so a regression here fails for real.
"""

import pytest
from core.synapse import Synapse
from http_api.routes import activate_kill_switch, cancel_cycle, deactivate_kill_switch


class _Bus:
    """Records every publish; SYSTEM_CONTROL actions are also applied to autopilot_enabled."""

    def __init__(self):
        self.published = []

    async def publish(self, topic, payload, sender):
        self.published.append((topic, payload, sender))


class _Vault:
    def __init__(self):
        self.released = False

    def release_all_reservations(self):
        self.released = True


class _Engine:
    """The surface activate_kill_switch/cancel_cycle/deactivate_kill_switch touch."""

    def __init__(self, synapse):
        self.manual_kill_switch = False
        self.is_processing = True
        self.running = True
        self.cycle_count = 7
        self.last_cycle_time = "not-none"
        self.bus = _Bus()
        self.vault = _Vault()
        self.synapse = synapse

    async def authorize_cycle(self) -> bool:
        """The one real gate: mirrors main.GhostEngine.authorize_cycle's kill-switch check."""
        return not self.manual_kill_switch


class _Request:
    pass


@pytest.fixture
def engine(tmp_path):
    return _Engine(Synapse(db_path=str(tmp_path / "kill_switch.db")))


class TestKillSwitchDoesNotStopTheProcess:
    @pytest.mark.asyncio
    async def test_kill_switch_does_not_touch_running(self, engine):
        """The regression: kill switch used to exit the main loop."""
        await activate_kill_switch(engine)(_Request())

        assert engine.running is True, "the process (and its HTTP server) must keep running"
        assert engine.manual_kill_switch is True
        assert engine.is_processing is False

    @pytest.mark.asyncio
    async def test_kill_switch_halts_cycle_authorization(self, engine):
        """The real halt: authorize_cycle refuses while the switch is set."""
        await activate_kill_switch(engine)(_Request())

        assert await engine.authorize_cycle() is False

    @pytest.mark.asyncio
    async def test_kill_switch_persists_across_checks(self, engine):
        """Repeated authorization attempts stay refused; the switch does not self-clear."""
        await activate_kill_switch(engine)(_Request())

        for _ in range(5):
            assert await engine.authorize_cycle() is False
            assert engine.manual_kill_switch is True

    @pytest.mark.asyncio
    async def test_deactivate_clears_it_and_cycles_resume(self, engine):
        await activate_kill_switch(engine)(_Request())
        assert await engine.authorize_cycle() is False

        await deactivate_kill_switch(engine)(_Request())

        assert engine.manual_kill_switch is False
        assert await engine.authorize_cycle() is True
        assert engine.running is True


class TestCancelDoesNotStopTheProcess:
    @pytest.mark.asyncio
    async def test_cancel_does_not_touch_running(self, engine):
        """The identical regression, on the /cancel handler."""
        await cancel_cycle(engine)(_Request())

        assert engine.running is True, "the process (and its HTTP server) must keep running"
        assert engine.is_processing is False

    @pytest.mark.asyncio
    async def test_cancel_publishes_stop_autopilot(self, engine):
        await cancel_cycle(engine)(_Request())

        actions = [
            payload.get("action")
            for topic, payload, _sender in engine.bus.published
            if topic == "SYSTEM_CONTROL"
        ]
        assert "STOP_AUTOPILOT" in actions

    @pytest.mark.asyncio
    async def test_cancel_releases_vault_reservations(self, engine):
        await cancel_cycle(engine)(_Request())

        assert engine.vault.released is True
