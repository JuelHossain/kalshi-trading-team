import os
from unittest.mock import MagicMock, patch

import pytest
from agents.brain import BrainAgent


@pytest.fixture
def brain_agent():
    bus = MagicMock()
    # Ensure GEMINI_API_KEY is not set or mock it to avoid real connection attempt
    with patch.dict(os.environ, {}, clear=True):
        agent = BrainAgent(agent_id=1, bus=bus)
    return agent


def test_simulation_high_prob(brain_agent):
    """Test Case 1: High Probability (80%), Low Payoff -> Should be positive EV"""
    opportunity = {"kalshi_price": 0.4, "vegas_prob": 0.8}

    result = brain_agent.run_simulation(opportunity)

    # EV should be approx: (0.8 * (1 - 0.4)) - (0.2 * 0.4) = 0.48 - 0.08 = 0.40
    print(f"High Prob EV: {result['ev']}")
    assert result["ev"] > 0.35
    assert result["win_rate"] > 0.75


def test_simulation_low_prob_high_payoff(brain_agent):
    """Test Case 2: Low Probability (20%), High Payoff -> Check EV"""
    opportunity = {"kalshi_price": 0.1, "vegas_prob": 0.2}

    result = brain_agent.run_simulation(opportunity)

    # EV = (0.2 * 0.9) - (0.8 * 0.1) = 0.18 - 0.08 = 0.10
    print(f"Low Prob EV: {result['ev']}")
    assert result["ev"] > 0.05


def test_an_overpriced_market_becomes_a_no_trade(brain_agent):
    """An estimate below the price is a NO opportunity, not a dead one.

    This asserted ev < -0.05 and treated the market as untradeable. That
    encoded the buy-YES-only assumption: at 60c with a 50% estimate the market
    is overpriced by 10c, which is exactly as tradeable as being underpriced by
    10c -- you buy NO at 40c instead.
    """
    opportunity = {"kalshi_price": 0.6, "vegas_prob": 0.5}

    result = brain_agent.run_simulation(opportunity)

    assert result["side"] == "no"
    assert result["ev"] == pytest.approx(0.1)  # 0.6 - 0.5
    assert result["side_price"] == pytest.approx(0.4)  # 1 - 0.6
    assert result["side_probability"] == pytest.approx(0.5)


def test_a_fairly_priced_market_has_no_edge_either_way(brain_agent):
    result = brain_agent.run_simulation({"kalshi_price": 0.5, "vegas_prob": 0.5})
    assert result["ev"] == pytest.approx(0.0)
