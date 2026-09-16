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
NO_ESTIMATE = {"win_rate": 0.0, "ev": -999.0, "variance": 999.0, "edge": -999.0}


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

    edge = probability - price
    return {
        "win_rate": float(probability),
        "ev": float(edge),
        "variance": float(probability * (1.0 - probability)),
        "edge": float(edge),
    }


def kelly_fraction(probability: float, price: float) -> float:
    """Full-Kelly stake as a fraction of bankroll for a binary contract.

        f* = (p - k) / (1 - k)

    Zero when there is no edge, and never negative -- this engine only buys,
    so a negative edge means "do not trade", not "trade the other way".
    """
    if price >= 1.0 or price <= 0.0:
        return 0.0

    fraction = (probability - price) / (1.0 - price)
    return max(0.0, min(1.0, fraction))
