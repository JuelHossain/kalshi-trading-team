"""A grounded estimate must never be silently replaced by an ungrounded one.

When grounded Gemini failed, the debate fell back to a free OpenRouter chat
model with no tools, answering a prompt that tells it to search for current
information. Its estimate entered the same median and sized the same Kelly
stake, and nothing on the decision said where it came from. With grounding
on, a failure now vetoes that sample; the fallback remains only when the
operator has switched grounding off, where both paths are ungrounded anyway.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from agents.brain.debate import run_debate

GOOD = '{"estimated_probability": 0.62, "confidence": 90}'


def _failing_gemini():
    client = MagicMock()

    def boom(model=None, contents=None, config=None):
        raise RuntimeError("429 RESOURCE_EXHAUSTED")

    client.models.generate_content = boom
    return client


async def _run(ai_client):
    return await run_debate(
        opportunity={"ticker": "KXA", "kalshi_price": 0.4, "market_data": {"title": "t"}},
        client=_failing_gemini(),
        gemini_model="m",
        personas={"optimist": "o", "critic": "c"},
        trading_instructions="",
        ai_client=ai_client,
        log_callback=AsyncMock(),
        log_error_callback=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_grounded_failure_vetoes_instead_of_falling_back(monkeypatch):
    monkeypatch.setenv("BRAIN_SEARCH_GROUNDING", "true")
    ai_client = MagicMock()
    ai_client._call_openrouter = AsyncMock(return_value=GOOD)

    result = await _run(ai_client)

    ai_client._call_openrouter.assert_not_awaited()
    assert result["confidence"] == 0.0
    assert result["estimated_probability"] is None


@pytest.mark.asyncio
async def test_with_grounding_off_the_fallback_still_serves(monkeypatch):
    monkeypatch.setenv("BRAIN_SEARCH_GROUNDING", "false")
    ai_client = MagicMock()
    ai_client._call_openrouter = AsyncMock(return_value=GOOD)

    result = await _run(ai_client)

    ai_client._call_openrouter.assert_awaited_once()
    assert result["estimated_probability"] == pytest.approx(0.62)
