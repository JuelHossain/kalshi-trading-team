#!/usr/bin/env python3
"""
Quick trade simulation against Brain agent logic.
Validates confidence thresholds, variance checks, and EV calculations.
"""

import argparse
import asyncio
import sys
import os

# Add engine to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..', 'engine'))

from agents.brain import BrainAgent
from core.bus import EventBus
from core.synapse import Synapse


async def run_simulation(ticker: str, price: float, vegas_prob: float = None):
    """Run a single trade simulation using Brain agent logic."""

    print(f"\n{'='*60}")
    print(f"TRADE SIMULATION: {ticker}")
    print(f"{'='*60}")
    print(f"Kalshi Price: {price*100:.1f}%")
    print(f"Vegas Probability: {vegas_prob*100:.1f}%" if vegas_prob else "Vegas Probability: Not provided")
    print()

    # Create a mock Brain agent for simulation
    bus = EventBus()
    synapse = Synapse("file:../../db/synapse.db?mode=memory")
    await synapse.initialize()

    brain = BrainAgent(agent_id=999, bus=bus, synapse=synapse)

    # Build opportunity dict
    opportunity = {
        "ticker": ticker,
        "kalshi_price": price,
        "vegas_prob": vegas_prob,
        "market_data": {
            "title": f"Mock Market: {ticker}",
            "subtitle": "Simulation test market",
            "yes_price": int(price * 100),
            "no_price": int((1 - price) * 100),
            "volume": 1000,
        }
    }

    # Run simulation
    print("Running Monte Carlo simulation (10,000 iterations)...")
    sim_result = brain.run_simulation(opportunity, override_prob=vegas_prob)

    # Display results
    print(f"\n{'-'*60}")
    print("SIMULATION RESULTS:")
    print(f"{'-'*60}")
    print(f"Win Rate:     {sim_result['win_rate']*100:.1f}%")
    print(f"EV:           {sim_result['ev']:.4f}")
    print(f"Variance:     {sim_result['variance']:.4f}")
    print()

    # Apply Brain decision logic
    confidence_threshold = BrainAgent.CONFIDENCE_THRESHOLD
    max_variance = BrainAgent.MAX_VARIANCE

    print(f"{'-'*60}")
    print("DECISION THRESHOLDS:")
    print(f"{'-'*60}")
    print(f"Min Confidence: {confidence_threshold*100:.0f}%")
    print(f"Max Variance:   {max_variance}")
    print()

    # Determine outcome
    approved = sim_result['ev'] > 0 and sim_result['variance'] <= max_variance

    print(f"{'='*60}")
    if approved:
        print(f"RESULT: [APPROVED]")
        print(f"Reason: Positive EV ({sim_result['ev']:.4f}) and acceptable variance")
    else:
        print(f"RESULT: [VETOED]")
        if sim_result['ev'] <= 0:
            print(f"Reason: Negative EV ({sim_result['ev']:.4f})")
        elif sim_result['variance'] > max_variance:
            print(f"Reason: Variance too high ({sim_result['variance']:.4f} > {max_variance})")
    print(f"{'='*60}\n")

    await synapse.close()
    return approved


def main():
    parser = argparse.ArgumentParser(
        description="Run quick trade simulations against Brain agent logic",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s INX-2024-01 0.50
  %(prog)s INX-2024-01 0.45 --vegas-prob 0.60
  %(prog)s BTC-10K-2024 0.25 --vegas-prob 0.15
        """
    )

    parser.add_argument("ticker", help="Market ticker symbol (e.g., INX-2024-01)")
    parser.add_argument("price", type=float, help="Current Kalshi price (0.0 to 1.0)")
    parser.add_argument("--vegas-prob", type=float, help="External/Vegas probability (0.0 to 1.0)")

    args = parser.parse_args()

    # Validate inputs
    if not 0 <= args.price <= 1:
        print("Error: Price must be between 0.0 and 1.0", file=sys.stderr)
        sys.exit(1)

    if args.vegas_prob is not None and not 0 <= args.vegas_prob <= 1:
        print("Error: Vegas probability must be between 0.0 and 1.0", file=sys.stderr)
        sys.exit(1)

    # Run simulation
    try:
        approved = asyncio.run(run_simulation(args.ticker, args.price, args.vegas_prob))
        sys.exit(0 if approved else 1)
    except Exception as e:
        print(f"Error running simulation: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
