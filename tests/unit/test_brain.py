import pytest
import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# Add engine to path
sys.path.append(os.path.join(os.getcwd(), 'engine'))

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
    opportunity = {
        "kalshi_price": 0.4,
        "vegas_prob": 0.8
    }
    
    result = brain_agent.run_simulation(opportunity)
    
    # EV should be approx: (0.8 * (1 - 0.4)) - (0.2 * 0.4) = 0.48 - 0.08 = 0.40
    print(f"High Prob EV: {result['ev']}")
    assert result["ev"] > 0.35
    assert result["win_rate"] > 0.75

def test_simulation_low_prob_high_payoff(brain_agent):
    """Test Case 2: Low Probability (20%), High Payoff -> Check EV"""
    opportunity = {
        "kalshi_price": 0.1,
        "vegas_prob": 0.2
    }
    
    result = brain_agent.run_simulation(opportunity)
    
    # EV = (0.2 * 0.9) - (0.8 * 0.1) = 0.18 - 0.08 = 0.10
    print(f"Low Prob EV: {result['ev']}")
    assert result["ev"] > 0.05

def test_simulation_negative_ev(brain_agent):
    """Test Case 3: 50/50 Coin Flip with negative EV"""
    opportunity = {
        "kalshi_price": 0.6,
        "vegas_prob": 0.5
    }
    
    result = brain_agent.run_simulation(opportunity)
    
    # EV = (0.5 * 0.4) - (0.5 * 0.6) = 0.2 - 0.3 = -0.1
    print(f"Neg Prob EV: {result['ev']}")
    assert result["ev"] < -0.05
