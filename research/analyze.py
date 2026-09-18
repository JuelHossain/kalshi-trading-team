"""Score model probability estimates against the market's own prices.

The question this answers: over settled markets, were the model's
probabilities closer to the truth than the prices it would have traded
against? If not, no amount of engineering downstream produces a profit,
because there is nothing to trade on.

Primary number is the paired Brier difference. Brier score is mean squared
error of a probability forecast — lower is better, and the comparison is
paired because both forecasters are scored on the identical set of events.

Usage:
    python research/analyze.py
    python research/analyze.py --variant anchored --edge 0.10
"""

from __future__ import annotations

import argparse
import math
import sqlite3
import statistics
from collections.abc import Sequence

from research import store

# Kalshi's published trading fee is approximately
#   ceil(0.07 x contracts x price x (1 - price)) in dollars.
# Verify against the current fee schedule before trusting the P&L figure.
FEE_COEFFICIENT = 0.07

_MIN_USEFUL_SAMPLE = 100
_T_SIGNIFICANT = 2.0
_EPSILON = 1e-9


def brier(probability: float, outcome: int) -> float:
    """Squared error of a probability forecast against a binary outcome."""
    return (probability - outcome) ** 2


def log_loss(probability: float, outcome: int) -> float:
    """Negative log likelihood, clamped to keep confident misses finite."""
    p = min(max(probability, _EPSILON), 1 - _EPSILON)
    return -(math.log(p) if outcome == 1 else math.log(1 - p))


def paired_brier(rows: Sequence[sqlite3.Row]) -> dict[str, float]:
    """Compare model and market Brier scores on the same events.

    Returns:
        Mean scores, the mean paired difference (positive means the model
        beat the market), its standard error, and the t statistic.
    """
    model = [brier(r["model_prob"], r["outcome"]) for r in rows]
    market = [brier(r["market_prob"], r["outcome"]) for r in rows]
    diffs = [mk - md for mk, md in zip(market, model, strict=True)]

    mean_diff = statistics.fmean(diffs)
    if len(diffs) > 1:
        stderr = statistics.stdev(diffs) / math.sqrt(len(diffs))
    else:
        # One observation carries no information about spread.
        stderr = float("inf")

    if stderr > 0:
        # An infinite stderr drives this to 0.0, which is the intent.
        t_stat = mean_diff / stderr
    elif mean_diff == 0:
        t_stat = 0.0
    else:
        # Every pair differed by the same non-zero amount, so the gap is
        # deterministic rather than unmeasurable. Returning 0.0 here would
        # report the strongest possible signal as no signal at all.
        t_stat = math.copysign(float("inf"), mean_diff)

    return {
        "n": len(rows),
        "model_brier": statistics.fmean(model),
        "market_brier": statistics.fmean(market),
        "model_log_loss": statistics.fmean(
            [log_loss(r["model_prob"], r["outcome"]) for r in rows]
        ),
        "market_log_loss": statistics.fmean(
            [log_loss(r["market_prob"], r["outcome"]) for r in rows]
        ),
        "mean_diff": mean_diff,
        "stderr": stderr,
        "t_stat": t_stat,
    }


def calibration(rows: Sequence[sqlite3.Row], bins: int = 5) -> list[dict[str, float]]:
    """Bucket predictions by model probability and compare to reality.

    A calibrated forecaster that says 70% should be right about 70% of the
    time within that bucket.
    """
    table = []
    for i in range(bins):
        low, high = i / bins, (i + 1) / bins
        bucket = [
            r for r in rows if low <= r["model_prob"] < high or (i == bins - 1 and r["model_prob"] == 1.0)
        ]
        if not bucket:
            continue
        table.append(
            {
                "low": low,
                "high": high,
                "count": len(bucket),
                "mean_predicted": statistics.fmean([r["model_prob"] for r in bucket]),
                "realised": statistics.fmean([float(r["outcome"]) for r in bucket]),
            }
        )
    return table


def _fee_cents(price_cents: int, contracts: int = 1) -> int:
    """Approximate Kalshi trading fee for a fill, in cents."""
    price = price_cents / 100
    dollars = FEE_COEFFICIENT * contracts * price * (1 - price)
    return math.ceil(dollars * 100)


def simulate(
    rows: Sequence[sqlite3.Row], edge: float, min_confidence: float
) -> dict[str, float]:
    """Hypothetical one-contract P&L from trading the model's disagreement.

    Assumes a fill at the quoted ask — it crosses the spread rather than
    resting an order. Ignores slippage, market impact, and the possibility
    that a resting order never fills, all of which make real results worse.
    """
    trades = 0
    wins = 0
    gross = 0
    fees = 0
    deployed = 0

    for row in rows:
        delta = row["model_prob"] - row["market_prob"]
        if abs(delta) < edge or (row["model_conf"] or 0) < min_confidence:
            continue

        if delta > 0:
            entry, won = row["yes_ask"], row["outcome"] == 1
        else:
            entry, won = row["no_ask"], row["outcome"] == 0
        if not entry or not 0 < entry < 100:
            continue

        trades += 1
        deployed += entry
        fees += _fee_cents(entry)
        if won:
            wins += 1
            gross += 100 - entry
        else:
            gross -= entry

    net = gross - fees
    return {
        "trades": trades,
        "wins": wins,
        "win_rate": wins / trades if trades else 0.0,
        "gross_cents": gross,
        "fees_cents": fees,
        "net_cents": net,
        "deployed_cents": deployed,
        "roi": net / deployed if deployed else 0.0,
    }


def _report(rows: list[sqlite3.Row], args: argparse.Namespace) -> None:
    """Print the full scoring report for one variant."""
    scores = paired_brier(rows)

    print(f"\n{'=' * 62}")
    print(f"  variant: {args.variant}    settled markets: {scores['n']}")
    print(f"{'=' * 62}")

    print("\nForecast accuracy (lower is better)")
    print(f"  model  Brier {scores['model_brier']:.4f}   log loss {scores['model_log_loss']:.4f}")
    print(f"  market Brier {scores['market_brier']:.4f}   log loss {scores['market_log_loss']:.4f}")

    print("\nPaired difference (market Brier minus model Brier)")
    print(f"  mean {scores['mean_diff']:+.4f}  stderr {scores['stderr']:.4f}  t {scores['t_stat']:+.2f}")

    print("\nCalibration of the model")
    print(f"  {'bucket':<14}{'n':>6}{'predicted':>12}{'realised':>11}")
    for bucket in calibration(rows, args.bins):
        label = f"{bucket['low']:.1f} - {bucket['high']:.1f}"
        print(
            f"  {label:<14}{bucket['count']:>6}"
            f"{bucket['mean_predicted']:>12.3f}{bucket['realised']:>11.3f}"
        )

    sim = simulate(rows, args.edge, args.min_confidence)
    print(f"\nHypothetical P&L  (edge >= {args.edge:.2f}, confidence >= {args.min_confidence:.2f})")
    if sim["trades"]:
        print(f"  trades {sim['trades']}   win rate {sim['win_rate']:.3f}")
        print(
            f"  gross {sim['gross_cents'] / 100:+.2f}   fees {sim['fees_cents'] / 100:.2f}"
            f"   net {sim['net_cents'] / 100:+.2f} on {sim['deployed_cents'] / 100:.2f} deployed"
        )
        print(f"  return on capital deployed: {sim['roi'] * 100:+.1f}%")
    else:
        print("  no signals cleared the thresholds")

    print(f"\n{'-' * 62}")
    if scores["n"] < _MIN_USEFUL_SAMPLE:
        print(f"  VERDICT: too early. {scores['n']} settled, want {_MIN_USEFUL_SAMPLE}+.")
    elif scores["t_stat"] > _T_SIGNIFICANT:
        print("  VERDICT: model beat the market. Edge worth pursuing —")
        print("  now check the P&L survives fees and the spread.")
    elif scores["t_stat"] < -_T_SIGNIFICANT:
        print("  VERDICT: market beat the model, clearly. Trading this")
        print("  signal loses money by construction.")
    else:
        print("  VERDICT: indistinguishable from the market price.")
        print("  No measurable edge. Fees and spread make that a net loss.")
    print(f"{'-' * 62}\n")


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("blind", "anchored"), default="blind")
    parser.add_argument("--edge", type=float, default=0.10, help="min model/market gap")
    parser.add_argument("--min-confidence", type=float, default=0.0)
    parser.add_argument("--bins", type=int, default=5)
    args = parser.parse_args()

    with store.connect() as conn:
        rows = store.settled(conn, args.variant)
        totals = store.counts(conn)

    if not rows:
        print(f"No settled predictions yet for variant '{args.variant}'.")
        print(f"Collected so far (total, resolved): {totals}")
        return

    _report(rows, args)


if __name__ == "__main__":
    main()
