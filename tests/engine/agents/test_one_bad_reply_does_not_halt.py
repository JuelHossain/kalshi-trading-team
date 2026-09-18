"""One bad AI reply must veto one market, not halt the engine.

Every per-sample failure in the debate (unparseable reply, timeout, no model)
was dispatched at HIGH, and the dispatcher pushed every error it saw -- MEDIUM
and LOW too -- into the Synapse error box. authorize_cycle refuses every cycle
while that box holds anything, and only /reset drains it. Seen live on
2026-09-18: a free fallback model returned truncated JSON for one of three
samples, the other two still scored the ticker, and the engine halted anyway.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from agents.brain.debate import run_debate
from core.error_codes import ErrorDomain, ErrorSeverity
from core.error_dispatcher import ErrorDispatcher


def _client(text: str):
    client = MagicMock()
    client.models.generate_content = lambda model=None, contents=None, config=None: MagicMock(
        text=text
    )
    return client


@pytest.mark.asyncio
async def test_an_unparseable_reply_is_logged_below_high():
    log_error = AsyncMock()

    result = await run_debate(
        opportunity={"ticker": "KXA", "kalshi_price": 0.4, "market_data": {"title": "t"}},
        client=_client('{"optimist": "truncated mid-sen'),
        gemini_model="m",
        personas={"optimist": "o", "critic": "c"},
        trading_instructions="",
        ai_client=None,
        log_callback=AsyncMock(),
        log_error_callback=log_error,
    )

    assert result["confidence"] == 0.0, "a failed sample must veto, as before"
    severities = [call.kwargs.get("severity") for call in log_error.await_args_list]
    assert severities, "the failure must still be reported"
    assert ErrorSeverity.HIGH not in severities and ErrorSeverity.CRITICAL not in severities


@pytest.mark.asyncio
@pytest.mark.parametrize("severity", [ErrorSeverity.LOW, ErrorSeverity.MEDIUM])
async def test_below_high_never_reaches_the_error_box(severity):
    synapse = MagicMock()
    synapse.errors.push = AsyncMock()
    dispatcher = ErrorDispatcher(agent_name="BRAIN", event_bus=None, synapse=synapse)

    await dispatcher.dispatch(
        code="INTELLIGENCE_PARSE_ERROR", severity=severity, domain=ErrorDomain.INTELLIGENCE
    )
    await asyncio.sleep(0.05)  # the old path pushed fire-and-forget; let it run

    synapse.errors.push.assert_not_called()


@pytest.mark.asyncio
async def test_high_still_latches():
    """The box still does its job for errors that should halt the engine."""
    synapse = MagicMock()
    synapse.errors.push = AsyncMock()
    dispatcher = ErrorDispatcher(agent_name="SOUL", event_bus=None, synapse=synapse)

    await dispatcher.dispatch(
        code="NETWORK_CONNECTION_FAILED", severity=ErrorSeverity.HIGH, domain=ErrorDomain.NETWORK
    )

    synapse.errors.push.assert_awaited_once()
