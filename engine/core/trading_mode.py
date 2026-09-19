"""Whether orders are real.

`is_paper_trading` existed before this module, but only ever reached the
progress display and the event payloads. Nothing on the path that places an
order read it, so a cycle rendered in yellow as PAPER TRADING would still send
a live order to Kalshi. The label was cosmetic exactly where it mattered.

The switch lives here rather than being threaded through Soul -> Brain -> Hand
because the Hand is several events downstream of the request that chose the
mode, and every layer in between would have to carry a flag it does not
otherwise use. One switch, consulted at the single point where money moves
(`KalshiClient.place_order`, which entries, exits and Ragnarok all funnel
through), cannot be bypassed by a new call site that forgets to pass it along.

It is default-deny: until something explicitly enables live trading, orders are
simulated. A wiring mistake therefore costs a paper fill, not money.
"""

import os
import sqlite3

from core.shared_utils import retry_sqlite

_live = False

# What paper mode holds. Kalshi's portfolio never sees a simulated fill, so
# anything that asks "do we already hold this?" by reading Kalshi gets an
# empty book back in paper mode and answers "no". The first successful paper
# run doubled into two markets that way. Keyed by ticker; "position" is
# signed the way Kalshi signs it: YES contracts positive, NO negative.
#
# This dict was the only copy, and every restart source -- systemd's
# Restart=always, deploy/update.sh, a crash, POST /engine/restart's os.execv
# -- emptied it: has_open_position then answered "not held" for a market the
# soak already bought, and check_exits could not see the earlier holding at
# all. (The kill switch and /cancel used to restart the process too, and
# would have had the same effect; b70be88 stopped them from restarting it,
# but the other restart sources remain.) It is mirrored to GHOST_VAULT_DB on
# every change and reloaded once at boot by load_paper_positions() so a
# restart recovers it.
_paper_positions: dict[str, dict] = {}

# The paper bankroll, seeded once from the real Kalshi balance the first time
# a process ever boots, then adjusted purely by paper activity: debited on a
# paper buy, credited on a paper sell or a settlement payout. None until
# seed_paper_cash has run at least once (either this process's boot, or an
# earlier one whose value load_paper_positions recovered from disk).
#
# Before this existed, authorize_cycle overwrote vault.current_balance with
# the real demo balance every cycle, which never moved for paper trades. A
# paper soak's spending vanished on the next cycle, Kelly always sized on the
# full real balance, and the hard floor and kill switch -- both keyed off
# vault.current_balance -- could not trip on paper losses the way they would
# in live.
_paper_cash: int | None = None


def _vault_db_path() -> str:
    return os.getenv("GHOST_VAULT_DB", "engine/ghost_memory.db")


def _connect_paper_db() -> sqlite3.Connection:
    conn = sqlite3.connect(_vault_db_path())
    conn.execute("""CREATE TABLE IF NOT EXISTS paper_positions (
            ticker          TEXT PRIMARY KEY,
            position        INTEGER NOT NULL,
            market_exposure INTEGER NOT NULL
        )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS paper_cash (
            id         INTEGER PRIMARY KEY CHECK (id = 1),
            cash_cents INTEGER NOT NULL
        )""")
    return conn


@retry_sqlite()
def _write_paper_positions() -> None:
    """The retried unit. Raises on a locked database so retry_sqlite's
    backoff gets a chance to run; _persist_paper_positions is what callers
    use and never raises. (Decorating a function whose own body caught every
    exception left retry_sqlite nothing to ever retry.)"""
    with _connect_paper_db() as conn:
        conn.execute("DELETE FROM paper_positions")
        conn.executemany(
            "INSERT INTO paper_positions (ticker, position, market_exposure) VALUES (?,?,?)",
            [
                (ticker, row["position"], row["market_exposure"])
                for ticker, row in _paper_positions.items()
            ],
        )


def _persist_paper_positions() -> None:
    """Mirror the in-memory paper book to disk. Never raises: a persistence
    failure must not be able to stop a trade, the same reason the ledger and
    telemetry do not (see core/db.log_to_db)."""
    try:
        _write_paper_positions()
    except Exception:
        pass


@retry_sqlite()
def _write_paper_cash() -> None:
    """The retried unit; see _write_paper_positions."""
    with _connect_paper_db() as conn:
        conn.execute(
            "INSERT INTO paper_cash (id, cash_cents) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET cash_cents = excluded.cash_cents",
            (_paper_cash,),
        )


def _persist_paper_cash() -> None:
    """Mirror the paper bankroll to disk. Never raises, for the same reason
    _persist_paper_positions does not."""
    if _paper_cash is None:
        return
    try:
        _write_paper_cash()
    except Exception:
        pass


def load_paper_positions() -> None:
    """Rebuild the in-memory paper book and bankroll from disk. Call once at boot.

    Restores whatever _persist_paper_positions and _persist_paper_cash last
    wrote, so a restart resumes the paper soak with the holdings and balance
    it already had rather than an empty book and a re-seeded bankroll.
    """
    global _paper_positions, _paper_cash
    try:
        with _connect_paper_db() as conn:
            rows = conn.execute(
                "SELECT ticker, position, market_exposure FROM paper_positions"
            ).fetchall()
            cash_row = conn.execute("SELECT cash_cents FROM paper_cash WHERE id = 1").fetchone()
    except Exception:
        return
    _paper_positions = {
        ticker: {"ticker": ticker, "position": position, "market_exposure": exposure}
        for ticker, position, exposure in rows
    }
    if cash_row is not None:
        _paper_cash = cash_row[0]


def seed_paper_cash(real_balance_cents: int) -> None:
    """Give the paper book a starting bankroll -- once.

    Only takes effect the first time this process's paper cash is still
    unknown (a fresh database, or a boot whose load_paper_positions found no
    persisted row). A later call, including on every subsequent restart, is
    a no-op: a restart must resume the paper P&L that has already accrued,
    not re-seed it from the real Kalshi balance again, which is the bug this
    exists to fix (see the module docstring on _paper_cash).
    """
    global _paper_cash
    if _paper_cash is not None:
        return
    _paper_cash = int(real_balance_cents)
    _persist_paper_cash()


def paper_cash() -> int | None:
    """The current paper bankroll in cents, or None if seed_paper_cash has
    never run (and load_paper_positions found nothing persisted either)."""
    return _paper_cash


def adjust_paper_cash(delta_cents: int) -> None:
    """Apply a paper P&L event to the bankroll: negative to debit a buy,
    positive to credit a sell's proceeds or a settlement payout.

    A no-op before the bankroll has ever been seeded -- there is nothing to
    adjust yet, and a caller (a buy that races the first seed) must not
    invent a balance out of a debit alone. Clamped at 0 the same way the
    vault's own get_available_balance is, so a rounding edge cannot show a
    negative bankroll.
    """
    global _paper_cash
    if _paper_cash is None:
        return
    _paper_cash = max(0, _paper_cash + int(delta_cents))
    _persist_paper_cash()


def set_live(live: bool) -> None:
    """Arm or disarm real order placement. Returns nothing; call it once per cycle."""
    global _live
    _live = bool(live)


def is_live() -> bool:
    """Whether orders placed right now reach Kalshi."""
    return _live


# Why new exposure is refused right now, keyed by who halted it. Empty means
# positions may be opened.
#
# The kill switch, Ragnarok, a Soul lockdown and the error box used to be read
# only by authorize_cycle -- they gated the cycle heartbeat and nothing else.
# The Brain's queue loop and the Hand run independently of cycles, so a signal
# already queued went straight through to an order with every halt engaged:
# reproduced in the audit as "ORDER EXECUTED" with the kill switch set, right
# after Ragnarok had flattened. place_order consults this for buys only, so
# exits and Ragnarok's own closes keep working while halted.
_halts: dict[str, str] = {}


def halt(key: str, reason: str) -> None:
    """Refuse new exposure until `key` is lifted. Re-halting a key replaces its reason."""
    _halts[key] = reason


def unhalt(key: str) -> None:
    """Lift one halt; others stay in force."""
    _halts.pop(key, None)


def clear_halts() -> None:
    """Lift every halt (what /reset means)."""
    _halts.clear()


def halted_by(key: str) -> str | None:
    """The reason recorded under `key`, or None if that halt is not set."""
    return _halts.get(key)


def halt_reasons() -> list[str]:
    """Every reason new exposure is refused, including the env KILL_SWITCH."""
    reasons = list(_halts.values())
    if env_kill_switch():
        reasons.append("env KILL_SWITCH")
    return reasons


def env_kill_switch() -> bool:
    """KILL_SWITCH as the Config view reads it (1/true/yes/on, any case).

    Three places compared the raw value to the exact string "true", so a
    hand-edited KILL_SWITCH=1 or TRUE showed ON in the cockpit and halted
    nothing.
    """
    from core.settings import settings

    return settings.get_bool("KILL_SWITCH")


def is_halted() -> bool:
    """Whether opening a position is refused right now."""
    return bool(halt_reasons())


def paper_fill(ticker: str, side: str, price: int, count: int, action: str) -> dict:
    """The response a simulated order returns.

    Shaped like a real fill so everything downstream -- reservation
    confirmation, notifications, the ledger, the dashboard -- runs the same code
    in paper as in live. A paper soak that skipped those paths would not be
    testing the thing that later handles real money.
    """
    _record_paper_fill(ticker, side, price, count, action)
    return {
        "order_id": f"PAPER-{action.lower()}-{side.lower()}-{ticker}-{price}x{count}",
        "status": "simulated",
        "paper": True,
        "ticker": ticker,
        "side": side.lower(),
        "action": action.lower(),
        "price": price,
        "count": count,
    }


def _record_paper_fill(ticker: str, side: str, price: int, count: int, action: str) -> None:
    """Apply a simulated fill to the paper book.

    A buy adds signed contracts and the cents paid, and debits that stake
    from the paper bankroll. A sell removes them and releases exposure in
    proportion, since Kalshi reports exposure rather than an average price
    and the exit policy derives entry from the ratio.

    A sell does NOT credit the bankroll here: `price` on a sell is the
    marketable-limit tick close_position asks for (1c in the held side's own
    price space; see KalshiClient.close_position), not what the position was
    actually worth, so crediting price*count would credit a cent a
    contract. The caller that knows the real proceeds -- check_exits, which
    already reads the current bid to decide whether to exit at all -- credits
    them itself via adjust_paper_cash once this returns.
    """
    signed = int(count) if side.lower() == "yes" else -int(count)
    row = _paper_positions.get(ticker, {"ticker": ticker, "position": 0, "market_exposure": 0})

    if action.lower() == "sell":
        held = row["position"]
        if held:
            per_contract = abs(row["market_exposure"]) / abs(held)
            row["market_exposure"] = max(
                0, round(abs(row["market_exposure"]) - per_contract * abs(count))
            )
        row["position"] = held - signed
    else:
        row["position"] = row["position"] + signed
        row["market_exposure"] = abs(row["market_exposure"]) + int(price) * int(count)
        adjust_paper_cash(-int(price) * int(count))

    if row["position"] == 0:
        _paper_positions.pop(ticker, None)
    else:
        _paper_positions[ticker] = row

    _persist_paper_positions()


def settle_paper_position(ticker: str, won_yes: bool) -> int:
    """Remove a resolved paper holding and report its payout in cents.

    A Kalshi contract pays $1 per contract on the winning side and nothing on
    the losing side, regardless of what was paid for it -- the entry price
    was already spent when the position was opened, so this returns the
    payout, not the P&L. 0 if the ticker was not held on paper, or if the
    held side lost.
    """
    row = _paper_positions.pop(ticker, None)
    _persist_paper_positions()
    if not row or not row["position"]:
        return 0

    held = row["position"]
    side_is_yes = held > 0
    if side_is_yes != won_yes:
        return 0
    return 100 * abs(held)


def paper_position(ticker: str) -> int:
    """Signed contracts held on paper for `ticker`; 0 if none."""
    return int(_paper_positions.get(ticker, {}).get("position", 0))


def paper_positions() -> list[dict]:
    """Every paper holding, shaped like a Kalshi market_positions row.

    Carries "position" and "market_exposure", which is what
    average_entry_price_cents and the exit review read.
    """
    return [dict(row) for row in _paper_positions.values()]


def reset_paper_positions() -> None:
    """Forget every paper holding and the paper bankroll, on disk and in memory.

    For tests and for a deliberate reset -- if only the in-memory state were
    cleared, the next boot's load_paper_positions() would resurrect what this
    call was meant to erase. Also what keeps test runs isolated from each
    other: both _paper_positions and _paper_cash are process-wide module
    globals, one process per test session.

    Clearing the bankroll back to None rather than 0 matters: 0 would look
    like a seeded, exhausted bankroll and refuse every trade; None is "not
    seeded yet", which is what a genuinely fresh process is, and lets the
    next seed_paper_cash actually seed it.
    """
    global _paper_cash
    _paper_positions.clear()
    _paper_cash = None
    _persist_paper_positions()
    try:
        with _connect_paper_db() as conn:
            conn.execute("DELETE FROM paper_cash")
    except Exception:
        pass
