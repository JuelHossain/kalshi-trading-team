"""The estimate must not be read off the market it is compared against.

The prompt withheld the Kalshi price but sent the Kalshi ticker, and told the
model to search. Grounded estimates then sat an average of 0.006 from the
market price across 24 live decisions, and a research log cited "Prediction
markets price the New York Giants at 24%". An estimate copied from the market
can never disagree with it, so no edge was ever found except by noise.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from agents.brain.debate import prediction_market_sources, run_debate

GOOD = '{"estimated_probability": 0.3, "confidence": 90}'
RULE = (
    "If Las Vegas wins the LV Raiders vs LA Chargers Pro Football game originally "
    "scheduled for Sep 20, 2026, then the market resolves to Yes."
)
OPPORTUNITY = {
    "ticker": "KXNFLGAME-26SEP20LVLAC-LV",
    "kalshi_price": 0.27,
    "market_data": {
        "title": "Las Vegas wins",
        "raw_response": {"rules_primary": RULE, "expected_expiration_time": "2026-09-21T02:05:00Z"},
    },
}


def _response(domains=()):
    chunks = [
        SimpleNamespace(web=SimpleNamespace(domain=d, title=d, uri="https://g/x")) for d in domains
    ]
    meta = SimpleNamespace(grounding_chunks=chunks)
    return SimpleNamespace(text=GOOD, candidates=[SimpleNamespace(grounding_metadata=meta)])


def _client(response):
    client = MagicMock()
    sent = {}

    def generate_content(model=None, contents=None, config=None):
        sent["prompt"] = contents
        return response

    client.models.generate_content = generate_content
    client.sent = sent
    return client


async def _run(client, opportunity=OPPORTUNITY):
    return await run_debate(
        opportunity=opportunity,
        client=client,
        gemini_model="m",
        personas={"optimist": "o", "critic": "c"},
        trading_instructions="",
        ai_client=None,
        log_callback=AsyncMock(),
        log_error_callback=AsyncMock(),
    )


class TestThePromptDescribesTheEventNotTheMarket:
    @pytest.mark.asyncio
    async def test_the_rule_replaces_the_ticker(self):
        client = _client(_response())
        await _run(client)
        prompt = client.sent["prompt"]
        assert RULE in prompt
        assert "KXNFLGAME" not in prompt, "the ticker is a search key for the Kalshi page"

    @pytest.mark.asyncio
    async def test_prediction_market_prices_are_ruled_out(self):
        client = _client(_response())
        await _run(client)
        assert "Polymarket" in client.sent["prompt"] and "Kalshi" in client.sent["prompt"]

    @pytest.mark.asyncio
    async def test_without_a_rule_the_ticker_is_still_given_as_context(self):
        opp = {**OPPORTUNITY, "market_data": {"title": "Las Vegas wins"}}
        client = _client(_response())
        await _run(client, opp)
        assert "KXNFLGAME-26SEP20LVLAC-LV" in client.sent["prompt"]


class TestASampleThatReadTheMarketIsDropped:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("domain", ["kalshi.com", "polymarket.com"])
    async def test_it_is_vetoed(self, domain):
        result = await _run(_client(_response([domain, "espn.com"])))
        assert result["confidence"] == 0.0
        assert result["estimated_probability"] is None

    @pytest.mark.asyncio
    async def test_ordinary_sources_are_kept(self):
        result = await _run(_client(_response(["espn.com", "nfl.com"])))
        assert result["estimated_probability"] == pytest.approx(0.3)

    def test_unreadable_metadata_is_not_a_leak(self):
        assert prediction_market_sources(MagicMock(candidates=None)) == []
        assert prediction_market_sources(object()) == []
