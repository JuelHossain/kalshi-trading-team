"""
Monte Carlo Simulation for Brain Agent
Calculates variance, EV, and win rates for trading opportunities.
"""
import os

import numpy as np


def run_simulation(opportunity: dict, override_prob: float = None, simulation_iterations: int = 10000) -> dict:
    """
    Monte Carlo simulation for variance and EV calculation.

    Args:
        opportunity: Market opportunity data
        override_prob: Override probability (AI estimate) if available
        simulation_iterations: Number of simulation iterations

    Returns:
        Dictionary with win_rate, ev, and variance
    """
    # Use overridden probability (AI estimate) if available
    vegas_prob = override_prob if override_prob is not None else opportunity.get("vegas_prob")

    # If no valid probability available, return failure state
    if vegas_prob is None:
        return {
            "win_rate": 0.0,
            "ev": -999.0,  # Highly negative EV to force veto
            "variance": 999.0  # High variance to force veto
        }

    kalshi_price = opportunity.get("kalshi_price", 0.5)

    # Simulate outcomes
    # Only use fixed seed for debugging/testing (set SIMULATION_USE_FIXED_SEED=true in .env)
    # Production simulations should be truly random for accurate variance estimation
    if os.getenv("SIMULATION_USE_FIXED_SEED") == "true":
        np.random.seed(42)
    outcomes = np.random.binomial(1, vegas_prob, simulation_iterations)

    # Calculate returns per simulation
    # Win: (1 - kalshi_price) profit | Lose: kalshi_price loss
    returns = np.where(outcomes == 1, (1 - kalshi_price), -kalshi_price)

    win_rate = outcomes.mean()
    ev = returns.mean()
    variance = returns.var()

    return {"win_rate": float(win_rate), "ev": float(ev), "variance": float(variance)}
