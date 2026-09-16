"""Outcome maths for a binary contract.

A Kalshi contract costs `k` and pays 1 if the event happens, 0 otherwise. For a
true probability `p` every quantity of interest has a closed form:

    EV       = p(1 - k) + (1 - p)(-k) = p - k
    variance = p(1 - p)                     (the payoff spread is exactly 1)

This module used to draw 10,000 random samples to approximate those two
numbers. That added sampling noise to exact answers and made the result
non-deterministic between runs, for no gain.

It also made the variance veto meaningless. p(1 - p) has a maximum of 0.25 at
p = 0.5, and the veto triggered above 0.25, so it could never fire for any
input. Variance of a binary outcome is a fixed function of the probability, so
it carries no information the probability does not already carry -- it is not a
risk signal. The real gate is the size of the edge, which is what `min_edge`
below expresses.
"""


# Returned when no usable probability exists, to force a veto upstream.
NO_ESTIMATE = {
    "win_rate": 0.0, "ev": -999.0, "variance": 999.0, "edge": -999.0,
    "side": "yes", "side_price": 0.5, "side_probability": 0.0,
}


def run_simulation(
    opportunity: dict,
    override_prob: float | None = None,
    simulation_iterations: int = 0,  # retained for call-site compatibility; unused
) -> dict:
    """Evaluate a binary contract exactly.

    Args:
        opportunity: must carry `kalshi_price` as a 0-1 fraction.
        override_prob: the estimated true probability. Falls back to the
            opportunity's `vegas_prob` when not supplied.
        simulation_iterations: ignored. Kept so existing callers and tests do
            not break; there is nothing left to iterate.

    Returns:
        win_rate, ev, variance and edge. `edge` is the tradeable quantity:
        expected profit per $1 of contract, which is what sizing should use.
    """
    probability = override_prob if override_prob is not None else opportunity.get("vegas_prob")

    if probability is None:
        return dict(NO_ESTIMATE)

    price = opportunity.get("kalshi_price", 0.5)
    side, side_price, side_probability, edge = best_side(probability, price)

    return {
        "win_rate": float(side_probability),
        "ev": float(edge),
        "variance": float(probability * (1.0 - probability)),
        "edge": float(edge),
        "side": side,
        "side_price": float(side_price),
        "side_probability": float(side_probability),
    }


def best_side(probability: float, yes_price: float) -> tuple[str, float, float, float]:
    """Pick the side of the contract worth buying, and its edge.

    A Kalshi market has two sides that always sum to 1. Holding YES at k pays 1
    when the event happens; holding NO at (1 - k) pays 1 when it does not.

        buy YES  edge = p - k
        buy NO   edge = (1 - p) - (1 - k) = k - p

    The engine only ever bought YES, so it could express "this is too cheap"
    and never "this is too expensive". Every market it judged overpriced -- half
    of all disagreements with the market, and exactly as tradeable -- was
    discarded rather than shorted.

    Returns (side, price of that side, probability of that side, edge). The
    edge is the larger of the two, and is negative only when the estimate
    matches the price, where neither side is worth buying.
    """
    yes_edge = probability - yes_price
    no_edge = yes_price - probability

    if no_edge > yes_edge:
        return ("no", 1.0 - yes_price, 1.0 - probability, no_edge)
    return ("yes", yes_price, probability, yes_edge)


def kelly_fraction(probability: float, price: float) -> float:
    """Full-Kelly stake as a fraction of bankroll for a binary contract.

        f* = (p - k) / (1 - k)

    Takes the price and probability OF THE SIDE BEING BOUGHT, so it serves NO
    positions unchanged: pass (1 - p) and (1 - k) and the same formula applies.

    Zero when there is no edge, and never negative -- a negative edge means
    "do not buy this side", and best_side() has already chosen which side that
    question is being asked about.
    """
    if price >= 1.0 or price <= 0.0:
        return 0.0

    fraction = (probability - price) / (1.0 - price)
    return max(0.0, min(1.0, fraction))
