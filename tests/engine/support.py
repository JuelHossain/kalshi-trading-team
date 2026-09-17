"""Helpers shared by the agent and integration tests.

These lived in test_trade_cycle.py and were imported from there by three
other modules. Importing from a test module couples unrelated files to its
collection and gives pyflakes the impression of redefined names.
"""

from datetime import datetime
from unittest.mock import AsyncMock


def _opportunity(ticker="KXTEST-01", **over):
    opp = {
        "ticker": ticker,
        "title": "Integration test market",
        "yes_price": 50,
        "no_price": 50,
        "volume": 10000,
        "timestamp": datetime.now().isoformat(),
    }
    opp.update(over)
    return opp


def _debate(confidence=0.95, probability=0.80):
    return AsyncMock(
        return_value={
            "estimated_probability": probability,
            "confidence": confidence,
            "reasoning": "integration test",
        }
    )
