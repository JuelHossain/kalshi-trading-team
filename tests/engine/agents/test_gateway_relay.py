"""The Gateway relays bus events outward. It must not echo them back in.

It subscribes to SIM_RESULT, SYSTEM_HEALTH and SYSTEM_ERROR, and emit()
used to republish each under the same topic -- re-invoking its own handler,
forever, with every level awaited. The Brain's SIM_RESULT publish never
returned and no trade decision was ever logged.

VAULT and STATE are different: the Gateway produces those itself in on_tick,
so publishing them is correct and the HTTP layer depends on it.
"""
import pytest

from agents.gateway import GatewayAgent


class _RecordingBus:
    def __init__(self):
        self.published: list[tuple[str, dict, str]] = []
        self.subscriptions: list[str] = []

    async def subscribe(self, topic, callback):
        self.subscriptions.append(topic)

    async def publish(self, topic, payload, sender):
        self.published.append((topic, payload, sender))


class _Vault:
    PRINCIPAL_CAPITAL_CENTS = 30000
    DAILY_PROFIT_THRESHOLD_CENTS = 5000
    current_balance = 32000
    start_of_day_balance = 30000
    is_locked = False


class _Message:
    def __init__(self, topic, payload):
        self.topic = topic
        self.payload = payload
        self.sender = "test"


@pytest.fixture
def gateway():
    bus = _RecordingBus()
    agent = GatewayAgent(5, bus, vault=_Vault())
    return agent, bus


def _topics(bus):
    return [t for t, _, _ in bus.published]


class TestRelayedEventsAreNotEchoed:
    @pytest.mark.asyncio
    async def test_a_simulation_result_is_not_republished(self, gateway):
        """The regression that froze the Brain."""
        agent, bus = gateway

        await agent.handle_sim(_Message("SIM_RESULT", {
            "ticker": "T", "win_rate": 0.5, "ev_score": 0.01,
            "variance": 0.2, "iterations": 1, "veto": True,
        }))

        assert "SIM_RESULT" not in _topics(bus)

    @pytest.mark.asyncio
    async def test_a_health_report_is_not_republished(self, gateway):
        agent, bus = gateway

        await agent.handle_health(_Message("SYSTEM_HEALTH", {"status": "ok"}))

        assert "SYSTEM_HEALTH" not in _topics(bus)

    @pytest.mark.asyncio
    async def test_an_error_is_not_republished(self, gateway):
        agent, bus = gateway

        await agent.handle_error(_Message("SYSTEM_ERROR", {
            "code": "X", "message": "boom", "severity": "HIGH",
            "agent_name": "TEST", "domain": "SYSTEM",
        }))

        assert "SYSTEM_ERROR" not in _topics(bus)

    @pytest.mark.asyncio
    async def test_no_subscribed_topic_is_ever_republished_by_emit(self, gateway):
        """Structural guard: subscribing to X and emitting X is a loop."""
        agent, bus = gateway
        await agent.setup()

        for msg_type in ("SIMULATION", "HEALTH", "ERROR", "LOG", "MARKET",
                         "INTERCEPT", "TRADE", "VAULT", "STATE"):
            bus.published.clear()
            await agent.emit(msg_type, {"probe": msg_type})
            echoed = set(_topics(bus)) & set(bus.subscriptions)
            assert not echoed, f"emit({msg_type!r}) republished subscribed topic(s) {echoed}"


class TestOriginatedEventsStillReachTheBus:
    @pytest.mark.asyncio
    async def test_on_tick_publishes_vault_state(self, gateway):
        """The HTTP layer reads vault state from the bus; keep it flowing."""
        agent, bus = gateway

        await agent.on_tick({"cycle": 1})

        assert "VAULT_UPDATE" in _topics(bus)

    @pytest.mark.asyncio
    async def test_on_tick_publishes_a_state_heartbeat(self, gateway):
        agent, bus = gateway

        await agent.on_tick({"cycle": 1})

        assert "SYSTEM_STATE" in _topics(bus)
