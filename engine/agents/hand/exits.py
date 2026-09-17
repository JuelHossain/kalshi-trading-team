"""When to leave a position.

The engine gained the ability to close a position, but nothing decided when to
use it: every holding rode to settlement unless a human ran Ragnarok. That is a
coherent strategy for binary contracts -- they settle at 0 or 100, so time is
on the side of a correct forecast -- but it should be a choice, and it has a
cost. A contract bought at 60c that drifts to 5c is almost certainly lost, and
holding it to settlement converts "almost certainly" into "certainly" while
tying up capital that could be working elsewhere.

These are pure functions over prices and time. They take no client, touch no
state, and make no network calls, so the policy can be reasoned about and
tested independently of the machinery that carries it out.

All prices are in cents, 1-99, the scale Kalshi quotes.
"""

from dataclasses import dataclass

from core.constants import (
    HAND_EXIT_BEFORE_EXPIRY_HOURS,
    HAND_STOP_LOSS_PCT,
    HAND_TAKE_PROFIT_PCT,
)


@dataclass(frozen=True)
class ExitDecision:
    """Whether to close, and why. The reason is recorded, so it must be specific."""

    should_exit: bool
    reason: str = ""


HOLD = ExitDecision(should_exit=False)


def evaluate_exit(
    entry_price_cents: int,
    current_price_cents: int,
    hours_to_expiry: float | None = None,
    stop_loss_pct: float = HAND_STOP_LOSS_PCT,
    take_profit_pct: float = HAND_TAKE_PROFIT_PCT,
    exit_before_expiry_hours: float = HAND_EXIT_BEFORE_EXPIRY_HOURS,
) -> ExitDecision:
    """Decide whether to close a YES position.

    Three rules, checked in order of urgency:

    1. Stop loss -- the price has fallen by `stop_loss_pct` of what was paid.
       Cuts a position the market has moved decisively against before it
       reaches zero.

    2. Take profit -- the price has captured `take_profit_pct` of the distance
       from entry to 100. Trades the last of the upside for certainty, which is
       worth doing when the remaining gain is small relative to the risk of
       giving back what is already won.

    3. Expiry, only when losing -- close out shortly before settlement if the
       position is underwater. A winning position is left to settle, since
       settlement pays 100 and selling into a thin pre-expiry book does not.

    Returns HOLD when no rule fires. Nonsensical inputs hold rather than guess:
    an exit decision made on bad data is worse than no decision.
    """
    if not _is_valid_price(entry_price_cents) or not _is_valid_price(current_price_cents):
        return HOLD

    # 1. Stop loss
    stop_level = entry_price_cents * (1.0 - stop_loss_pct)
    if current_price_cents <= stop_level:
        loss_pct = (entry_price_cents - current_price_cents) / entry_price_cents
        return ExitDecision(
            True,
            f"stop loss: {current_price_cents}c is {loss_pct:.0%} below entry "
            f"{entry_price_cents}c (limit {stop_loss_pct:.0%})",
        )

    # 2. Take profit
    upside = 100 - entry_price_cents
    if upside > 0:
        target = entry_price_cents + upside * take_profit_pct
        if current_price_cents >= target:
            captured = (current_price_cents - entry_price_cents) / upside
            return ExitDecision(
                True,
                f"take profit: {current_price_cents}c captures {captured:.0%} of "
                f"the move to 100 (target {take_profit_pct:.0%})",
            )

    # 3. Near expiry and losing
    if (
        hours_to_expiry is not None
        and hours_to_expiry <= exit_before_expiry_hours
        and current_price_cents < entry_price_cents
    ):
        return ExitDecision(
            True,
            f"expiring in {hours_to_expiry:.1f}h while down "
            f"({current_price_cents}c vs entry {entry_price_cents}c)",
        )

    return HOLD


def average_entry_price_cents(position: dict) -> int | None:
    """Recover what was paid per contract from a Kalshi position row.

    Kalshi reports exposure and quantity rather than an average price, so it is
    derived. Returns None when the row does not carry enough to derive it --
    the caller must then hold, because an exit computed from a guessed entry
    price is an exit made on fiction.
    """
    quantity = position.get("position")
    exposure = position.get("market_exposure", position.get("total_traded"))

    if not quantity or exposure in (None, 0):
        return None

    try:
        average = abs(float(exposure)) / abs(int(quantity))
    except (TypeError, ValueError, ZeroDivisionError):
        return None

    return round(average) if _is_valid_price(average) else None


def _is_valid_price(price: float | int | None) -> bool:
    """Kalshi quotes 1-99. Anything else is not a price we can reason about."""
    if price is None:
        return False
    try:
        return 1 <= float(price) <= 99
    except (TypeError, ValueError):
        return False
