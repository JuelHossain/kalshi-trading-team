"""Several independent estimates, and a veto on how much they disagree.

A single call produces a probability with no uncertainty attached, and the
engine treated that number as fact. Its only risk gate was the variance of the
outcome, p(1-p) -- a fixed function of the probability, so it carried no
information the probability did not already carry, and could never bind.

Disagreement between independent estimates varies independently of the
probability, so it can actually reject a trade.
"""

from unittest.mock import AsyncMock, patch

import pytest
from agents.brain import debate as debate_module
from agents.brain.debate import run_debate_ensemble

from tests.engine.support import _opportunity


def _estimates(*probabilities, confidence=0.9):
    """Patch run_debate to return this sequence of estimates."""
    values = iter(probabilities)

    async def fake(**_kwargs):
        return {
            "estimated_probability": next(values),
            "confidence": confidence,
            "reasoning": "r",
        }

    return patch.object(debate_module, "run_debate", fake)


class TestAggregation:
    @pytest.mark.asyncio
    async def test_the_median_is_used_not_the_mean(self):
        """One wild draw must not drag the estimate."""
        with _estimates(0.70, 0.72, 0.05):
            result = await run_debate_ensemble(samples=3)

        assert result["estimated_probability"] == pytest.approx(0.70)

    @pytest.mark.asyncio
    async def test_agreeing_samples_report_low_disagreement(self):
        with _estimates(0.70, 0.72, 0.68):
            result = await run_debate_ensemble(samples=3)

        assert result["disagreement"] == pytest.approx(0.04)

    @pytest.mark.asyncio
    async def test_scattered_samples_report_high_disagreement(self):
        with _estimates(0.10, 0.90, 0.50):
            result = await run_debate_ensemble(samples=3)

        assert result["disagreement"] == pytest.approx(0.80)

    @pytest.mark.asyncio
    async def test_confidence_is_the_least_confident_sample(self):
        """If any run was unsure, the ensemble is unsure."""
        values = iter([(0.7, 0.95), (0.7, 0.40), (0.7, 0.99)])

        async def fake(**_kwargs):
            p, c = next(values)
            return {"estimated_probability": p, "confidence": c, "reasoning": "r"}

        with patch.object(debate_module, "run_debate", fake):
            result = await run_debate_ensemble(samples=3)

        assert result["confidence"] == pytest.approx(0.40)

    @pytest.mark.asyncio
    async def test_a_single_sample_behaves_as_before(self):
        """samples=1 must cost one call and assert no disagreement."""
        with _estimates(0.70):
            result = await run_debate_ensemble(samples=1)

        assert result["estimated_probability"] == pytest.approx(0.70)
        assert result["disagreement"] == 0.0


class TestPartialFailure:
    @pytest.mark.asyncio
    async def test_usable_samples_survive_a_failed_one(self):
        calls = {"n": 0}

        async def flaky(**_kwargs):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("API error")
            return {"estimated_probability": 0.70, "confidence": 0.9, "reasoning": "r"}

        with patch.object(debate_module, "run_debate", flaky):
            result = await run_debate_ensemble(samples=3)

        assert result["samples"] == 2
        assert result["estimated_probability"] == pytest.approx(0.70)

    @pytest.mark.asyncio
    async def test_all_samples_failing_vetoes(self):
        async def broken(**_kwargs):
            return {"estimated_probability": None, "confidence": 0.0, "reasoning": "x"}

        with patch.object(debate_module, "run_debate", broken):
            result = await run_debate_ensemble(samples=3)

        assert result["estimated_probability"] is None
        assert result["confidence"] == 0.0
        assert result["disagreement"] == 1.0


class TestTheDisagreementVeto:
    @pytest.mark.asyncio
    async def test_scattered_estimates_do_not_trade(self, cycle):
        """The gate the variance veto could never be."""
        brain = cycle["brain"]
        # Median 0.90 is a large edge at 50c -- only disagreement can stop this.
        brain.run_debate = AsyncMock(
            return_value={
                "estimated_probability": 0.90,
                "confidence": 0.95,
                "reasoning": "r",
                "disagreement": brain.MAX_DISAGREEMENT + 0.01,
            }
        )

        result = await brain.process_single_opportunity(_opportunity(kalshi_price=0.50))

        assert result == "VETOED"
        assert await cycle["synapse"].executions.size() == 0

    @pytest.mark.asyncio
    async def test_agreeing_estimates_still_trade(self, cycle):
        """A veto that blocks everything is not a veto."""
        brain = cycle["brain"]
        brain.run_debate = AsyncMock(
            return_value={
                "estimated_probability": 0.90,
                "confidence": 0.95,
                "reasoning": "r",
                "disagreement": 0.02,
            }
        )

        await brain.process_single_opportunity(_opportunity(kalshi_price=0.50))

        assert await cycle["synapse"].executions.size() == 1
