"""A hung AI call must not stall the Brain.

google-genai's default HTTP timeout is None: a request the server accepted and
never answered blocked forever, and because the Brain awaits the ensemble
inline in its only queue-draining loop, one silent socket stopped all analysis
with no log line (reproduced in the audit against a server that never replies).
"""

import asyncio

import pytest
from agents.brain import debate


@pytest.mark.asyncio
async def test_a_hung_sample_is_dropped_and_the_rest_still_count(monkeypatch):
    monkeypatch.setattr(debate, "SAMPLE_DEADLINE_SECONDS", 0.2)
    calls = {"n": 0}

    async def run_debate(**_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            await asyncio.sleep(60)  # the silent socket
        return {"estimated_probability": 0.4, "confidence": 0.9, "reasoning": "r"}

    monkeypatch.setattr(debate, "run_debate", run_debate)

    result = await asyncio.wait_for(debate.run_debate_ensemble(samples=3), timeout=5)

    assert result["samples"] == 2
    assert result["estimated_probability"] == pytest.approx(0.4)


@pytest.mark.asyncio
async def test_a_single_hung_sample_is_a_veto_not_a_hang(monkeypatch):
    monkeypatch.setattr(debate, "SAMPLE_DEADLINE_SECONDS", 0.2)

    async def run_debate(**_kwargs):
        await asyncio.sleep(60)

    monkeypatch.setattr(debate, "run_debate", run_debate)

    result = await asyncio.wait_for(debate.run_debate_ensemble(samples=1), timeout=5)

    assert result["estimated_probability"] is None and result["confidence"] == 0.0


def test_the_gemini_client_has_a_timeout(monkeypatch):
    from core import ai_utils

    seen = {}

    class _Client:
        def __init__(self, **kwargs):
            seen.update(kwargs)

    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setattr(ai_utils.genai, "Client", _Client)

    ai_utils.initialize_gemini_client()

    assert seen["http_options"].timeout, "the SDK default of None waits forever"
