"""Score forecasts against known outcomes.

The ledger answers "is the engine calibrated?" going forward, one settlement at
a time. It cannot answer it retrospectively, so the only way to know whether
the strategy has edge was to risk money and wait.

Kalshi markets settle, which makes every past market labelled data: the
question, the price it traded at, and the answer. Scoring the engine's
estimates against a few hundred of those says in an afternoon what paper
trading suggests in weeks.

Pure functions over rows. Nothing here touches the network or the engine's
databases, so the same scorer runs over a live ledger, a replay, or a
hand-built fixture.
"""

from dataclasses import dataclass, field


@dataclass
class BacktestResult:
    """What the engine would have done, and what it would have been worth."""

    n: int = 0
    traded: int = 0
    wins: int = 0
    # Profit per $1 staked, summed over trades. Positive means the strategy made
    # money on this sample; it does not mean it will.
    total_return: float = 0.0
    brier: float | None = None
    calibration: list[dict] = field(default_factory=list)

    @property
    def hit_rate(self) -> float | None:
        return self.wins / self.traded if self.traded else None

    @property
    def return_per_trade(self) -> float | None:
        return self.total_return / self.traded if self.traded else None

    def summary(self) -> str:
        if not self.traded:
            return f"{self.n} markets scored, 0 passed the filters -- nothing to judge."
        return (
            f"{self.n} markets scored, {self.traded} traded. "
            f"Hit rate {self.hit_rate:.1%}, "
            f"return {self.return_per_trade:+.3f} per $1 staked, "
            f"Brier {self.brier:.4f}."
        )


def score_predictions(
    rows: list[dict],
    min_edge: float = 0.05,
    min_confidence: float = 0.85,
    buckets: int = 5,
) -> BacktestResult:
    """Replay decisions over settled markets.

    Each row needs `probability` (the engine's estimate), `price` (the YES
    price it could have traded at, 0-1) and `settled_yes` (what happened).
    `confidence` is optional and defaults to passing.

    The same two-sided rule the live engine uses applies here: the side with
    the better edge is taken, so an overpriced market is a NO trade rather than
    a skip. Scoring it any other way would flatter or damn a strategy the
    engine does not actually run.

    Brier score is computed over ALL rows with an estimate, not only the traded
    ones -- calibration is a property of the forecaster, not of the filter.
    Lower is better; 0.25 is what you get by always saying 50%.
    """
    result = BacktestResult()
    brier_terms: list[float] = []
    scored: list[tuple[float, int]] = []

    for row in rows:
        probability = row.get("probability")
        price = row.get("price")
        settled = row.get("settled_yes")

        if probability is None or price is None or settled is None:
            continue
        if not (0.0 <= probability <= 1.0) or not (0.0 < price < 1.0):
            continue

        settled_yes = 1 if settled else 0
        result.n += 1
        brier_terms.append((probability - settled_yes) ** 2)
        scored.append((probability, settled_yes))

        if row.get("confidence") is not None and row["confidence"] < min_confidence:
            continue

        side, side_price, _, edge = _best_side(probability, price)
        if edge < min_edge:
            continue

        result.traded += 1
        won = settled_yes == 1 if side == "yes" else settled_yes == 0
        if won:
            result.wins += 1
            result.total_return += (1.0 - side_price) / side_price
        else:
            result.total_return += -1.0

    if brier_terms:
        result.brier = sum(brier_terms) / len(brier_terms)
    result.calibration = _calibration(scored, buckets)
    return result


def _best_side(probability: float, yes_price: float) -> tuple[str, float, float, float]:
    """Mirror of simulation.best_side, duplicated to keep the scorer dependency-free.

    The scorer must be runnable against a CSV on a laptop with no engine
    imports and no configuration; importing the agent tree to get one formula
    would defeat that.
    """
    yes_edge = probability - yes_price
    no_edge = yes_price - probability
    if no_edge > yes_edge:
        return ("no", 1.0 - yes_price, 1.0 - probability, no_edge)
    return ("yes", yes_price, probability, yes_edge)


def _calibration(scored: list[tuple[float, int]], buckets: int) -> list[dict]:
    if not scored:
        return []

    width = 1.0 / buckets
    grouped: dict[int, list[tuple[float, int]]] = {}
    for probability, settled in scored:
        index = min(int(probability / width), buckets - 1)
        grouped.setdefault(index, []).append((probability, settled))

    report = []
    for index in sorted(grouped):
        entries = grouped[index]
        predicted = sum(p for p, _ in entries) / len(entries)
        actual = sum(s for _, s in entries) / len(entries)
        report.append(
            {
                "bucket": f"{index * width:.0%}-{(index + 1) * width:.0%}",
                "n": len(entries),
                "predicted": round(predicted, 4),
                "actual": round(actual, 4),
                "gap": round(actual - predicted, 4),
            }
        )
    return report
