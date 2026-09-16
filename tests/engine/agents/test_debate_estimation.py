"""The probability estimate must be formed without seeing the market price.

The prompt used to contain "Current Kalshi Price: {x}%" immediately before
asking the model for the true probability. The bot's edge is the gap between
that estimate and the price, so showing the price first anchors the estimate
toward it and collapses the very quantity being traded on.

The price is not needed in the prompt: EV and sizing are computed in Python.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.brain.debate import (
    _normalise_confidence,
    _validate_probability,
    run_debate,
)


def _client(payload: str):
    """A stand-in Gemini client that records the prompt it was handed."""
    client = MagicMock()
    sent = {}

    def generate_content(model=None, contents=None):
        sent["prompt"] = contents
        return MagicMock(text=payload)

    client.models.generate_content = generate_content
    client.sent = sent
    return client


async def _run(client, opportunity):
    return await run_debate(
        opportunity=opportunity,
        client=client,
        gemini_model="test-model",
        personas={"optimist": "OPTIMIST: x", "critic": "CRITIC: y"},
        trading_instructions="",
        ai_client=None,
        log_callback=AsyncMock(),
        log_error_callback=AsyncMock(),
    )


OPPORTUNITY = {
    "ticker": "KXTEST-01",
    "kalshi_price": 0.63,
    "market_data": {"title": "Will X happen?", "subtitle": "by Friday"},
}

GOOD = '{"optimist":"a","critic":"b","judge_verdict":"c","estimated_probability":0.75,"confidence":85}'


class TestThePromptIsPriceBlind:
    @pytest.mark.asyncio
    async def test_market_price_never_reaches_the_model(self):
        client = _client(GOOD)
        await _run(client, OPPORTUNITY)
        prompt = client.sent["prompt"]

        assert "63" not in prompt, "the market price leaked into the prompt"
        assert "0.63" not in prompt
        assert "Kalshi Price" not in prompt

    @pytest.mark.asyncio
    async def test_the_question_still_reaches_the_model(self):
        """De-anchoring must not have removed the actual market being judged."""
        client = _client(GOOD)
        await _run(client, OPPORTUNITY)
        prompt = client.sent["prompt"]

        assert "KXTEST-01" in prompt
        assert "Will X happen?" in prompt
        assert "by Friday" in prompt

    @pytest.mark.asyncio
    async def test_news_context_is_still_supplied(self):
        client = _client(GOOD)
        await _run(client, {**OPPORTUNITY, "external_context": "Reuters: X is likely"})

        assert "Reuters: X is likely" in client.sent["prompt"]


class TestConfidenceScale:
    """85 and 0.85 both mean 85%. The old parser turned the latter into 0.85%."""

    @pytest.mark.parametrize(
        "raw,expected",
        [(85, 0.85), (0.85, 0.85), (100, 1.0), (1, 1.0), (0, 0.0), (50, 0.5)],
    )
    def test_both_scales_are_accepted(self, raw, expected):
        assert _normalise_confidence(raw) == pytest.approx(expected)

    @pytest.mark.parametrize("raw", [-5, 150, "high", None, object()])
    def test_unusable_values_mean_no_confidence(self, raw):
        assert _normalise_confidence(raw) == 0.0

    @pytest.mark.asyncio
    async def test_fractional_confidence_survives_the_round_trip(self):
        """The failure this guards: a model answering 0.85 silently halted trading."""
        payload = '{"judge_verdict":"c","estimated_probability":0.7,"confidence":0.85}'
        result = await _run(_client(payload), OPPORTUNITY)

        assert result["confidence"] == pytest.approx(0.85)


class TestProbabilityValidation:
    @pytest.mark.parametrize("raw,expected", [(0.75, 0.75), (0, 0.0), (1, 1.0)])
    def test_in_range_values_pass(self, raw, expected):
        assert _validate_probability(raw) == pytest.approx(expected)

    @pytest.mark.parametrize("raw", [1.5, -0.1, "likely", None])
    def test_out_of_range_is_rejected(self, raw):
        assert _validate_probability(raw) is None

    @pytest.mark.asyncio
    async def test_a_bad_probability_vetoes_rather_than_defaulting(self):
        """Defaulting to 0.5 would trade on a coin flip the model never gave."""
        payload = '{"judge_verdict":"c","estimated_probability":1.8,"confidence":95}'
        result = await _run(_client(payload), OPPORTUNITY)

        assert result["estimated_probability"] is None
        assert result["confidence"] == 0.0
