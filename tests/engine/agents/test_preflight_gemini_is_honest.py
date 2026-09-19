"""Pre-flight must not report Gemini as passing when only the fallback answered.

The check went through generate_with_fallback: five Gemini models, then
OpenRouter. Any OpenRouter reply counted as "Gemini PASSED". Seen live on
2026-09-18: five "API key not valid" failures followed by PRE-FLIGHT API CHECK
PASSED (Kalshi, Supabase, Gemini), while every Brain estimate failed after it.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from agents.soul import SoulAgent


@pytest.fixture
def soul(bus, synapse, vault, monkeypatch):
    import agents.soul.agent as soul_module

    s = SoulAgent(1, bus, vault=vault, synapse=synapse)
    s.log = AsyncMock()
    s.ai_client = MagicMock()
    s.ai_client._call_openrouter = AsyncMock(return_value="pong")

    kalshi = MagicMock()
    kalshi.get_balance = AsyncMock(return_value=32813)
    monkeypatch.setattr(soul_module, "kalshi_client", kalshi)
    monkeypatch.setattr(soul_module, "check_supabase_connection", AsyncMock(return_value=True))
    return s


def _logged(soul):
    return [(c.args[0], c.kwargs.get("level")) for c in soul.log.await_args_list]


@pytest.mark.asyncio
async def test_a_dead_key_is_not_reported_as_passing(soul):
    client = MagicMock()

    def invalid(model=None, contents=None, config=None):
        raise RuntimeError("400 INVALID_ARGUMENT API_KEY_INVALID: API key not valid")

    client.models.generate_content = invalid
    soul.client = client

    await soul.check_api_health()

    lines = _logged(soul)
    passed = [msg for msg, _ in lines if msg.startswith("PRE-FLIGHT API CHECK PASSED")]
    assert passed and "Gemini" not in passed[0]
    assert any("Gemini" in msg and level == "ERROR" for msg, level in lines)
    soul.ai_client._call_openrouter.assert_not_awaited()
    assert soul.is_locked_down is False, "a Gemini outage must not become a restart loop"


@pytest.mark.asyncio
async def test_a_working_key_passes(soul):
    client = MagicMock()
    client.models.generate_content = lambda model=None, contents=None, config=None: MagicMock(
        text="pong"
    )
    soul.client = client

    await soul.check_api_health()

    passed = [msg for msg, _ in _logged(soul) if msg.startswith("PRE-FLIGHT API CHECK PASSED")]
    assert passed == ["PRE-FLIGHT API CHECK PASSED (Kalshi, Supabase, Gemini)"]
