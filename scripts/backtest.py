#!/usr/bin/env python3
"""Score the engine against markets that have already settled.

    python scripts/backtest.py data/settled.csv

The file needs one row per market: ticker, probability, price, settled_yes,
and optionally confidence. See engine/backtest/runner.py for the format.

Fetching that data needs network access to Kalshi, which is why this script
only scores: run the fetch wherever the network is, and score anywhere.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

from backtest.runner import format_report, run_backtest  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    try:
        result = run_backtest(sys.argv[1])
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}")
        return 1

    print(format_report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
