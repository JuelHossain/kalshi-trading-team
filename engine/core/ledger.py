"""Decision ledger: what the engine predicted, and what actually happened.

The engine had no record of its own judgement. It logged that a trade
happened, never what it believed at the time, so there was no way to ask the
only question that decides whether any of this is worth running:

    when this bot says 80%, does the event happen about 80% of the time?

A model can be confidently, consistently wrong and look identical from the
outside to one that is right, until the money runs out. Calibration is the
difference, and it can only be measured against settled outcomes.

Every decision is recorded, including the ones that did not trade -- a veto is
a prediction too, and a bot that vetoes all its winners is worth knowing about.
Settlement is filled in later, when the market resolves.
"""

import os
import sqlite3
from datetime import UTC, datetime

from core.shared_utils import retry_sqlite

_SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    decided_at           TEXT    NOT NULL,
    ticker               TEXT    NOT NULL,
    market_price         REAL    NOT NULL,   -- 0-1 at decision time
    estimated_probability REAL,              -- what the engine believed
    confidence           REAL,
    edge                 REAL,               -- estimate minus price
    outcome              TEXT    NOT NULL,   -- APPROVED / VETOED / STALE / ...
    veto_reason          TEXT,
    stake_cents          INTEGER,
    order_id             TEXT,
    settled_yes          INTEGER,            -- 1 / 0 once the market resolves
    settled_at           TEXT
);
CREATE INDEX IF NOT EXISTS idx_decisions_ticker ON decisions(ticker);
CREATE INDEX IF NOT EXISTS idx_decisions_settled ON decisions(settled_yes);
"""


def _db_path() -> str:
    return os.getenv("GHOST_LEDGER_DB", "ghost_ledger.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.executescript(_SCHEMA)
    return conn


@retry_sqlite()
def record_decision(
    ticker: str,
    market_price: float,
    outcome: str,
    estimated_probability: float | None = None,
    confidence: float | None = None,
    veto_reason: str | None = None,
    stake_cents: int | None = None,
    order_id: str | None = None,
) -> int:
    """Record one judgement. Returns the row id.

    Never raises into the caller: a ledger failure must not stop a trade, for
    the same reason analytics must not (see core/db.log_to_db).
    """
    edge = None
    if estimated_probability is not None:
        edge = estimated_probability - market_price

    try:
        with _connect() as conn:
            cur = conn.execute(
                """INSERT INTO decisions
                   (decided_at, ticker, market_price, estimated_probability,
                    confidence, edge, outcome, veto_reason, stake_cents, order_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    datetime.now(UTC).isoformat(),
                    ticker,
                    market_price,
                    estimated_probability,
                    confidence,
                    edge,
                    outcome,
                    veto_reason,
                    stake_cents,
                    order_id,
                ),
            )
            return cur.lastrowid
    except Exception:
        return -1


@retry_sqlite()
def record_fill(ticker: str, stake_cents: int, order_id: str | None) -> int:
    """Attach an executed order to its APPROVED decision. Returns rows updated.

    stake_cents and order_id existed as columns from the start and nothing
    ever wrote them: five paper fills in one run left zero filled rows. Without
    this, realised P&L cannot be computed from the ledger, which is the one
    thing a paper soak exists to measure.

    Targets the most recent APPROVED row for the ticker that has no order
    yet, so two fills on one market attach to two decisions rather than the
    second overwriting the first.
    """
    try:
        with _connect() as conn:
            cur = conn.execute(
                """UPDATE decisions
                      SET stake_cents = ?, order_id = ?
                    WHERE id = (
                        SELECT id FROM decisions
                         WHERE ticker = ? AND outcome = 'APPROVED' AND order_id IS NULL
                         ORDER BY id DESC LIMIT 1
                    )""",
                (int(stake_cents), order_id, ticker),
            )
            return cur.rowcount
    except Exception:
        return 0


@retry_sqlite()
def record_settlement(ticker: str, settled_yes: bool) -> int:
    """Fill in how a market resolved. Returns rows updated."""
    try:
        with _connect() as conn:
            cur = conn.execute(
                """UPDATE decisions
                      SET settled_yes = ?, settled_at = ?
                    WHERE ticker = ? AND settled_yes IS NULL""",
                (1 if settled_yes else 0, datetime.now(UTC).isoformat(), ticker),
            )
            return cur.rowcount
    except Exception:
        return 0


def calibration(buckets: int = 5) -> list[dict]:
    """Group settled predictions and compare belief against reality.

    A calibrated forecaster's `predicted` and `actual` track each other. A
    bucket where predicted is 0.80 and actual is 0.45 is the engine being
    confidently wrong in a way no amount of downstream engineering can fix.
    """
    with _connect() as conn:
        rows = conn.execute("""SELECT estimated_probability, settled_yes
                 FROM decisions
                WHERE settled_yes IS NOT NULL
                  AND estimated_probability IS NOT NULL""").fetchall()

    if not rows:
        return []

    width = 1.0 / buckets
    grouped: dict[int, list[tuple[float, int]]] = {}
    for probability, settled in rows:
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


def recent_decisions(limit: int = 200, ticker: str | None = None) -> list[dict]:
    """Every judgement the Brain recorded, newest first: approvals and vetoes alike.

    This is the persistent answer to "what did the bot think, and why", so
    the dashboard's Brain history survives a restart.
    """
    try:
        with _connect() as conn:
            where = "WHERE ticker = ?" if ticker else ""
            args: tuple = (ticker, int(limit)) if ticker else (int(limit),)
            rows = conn.execute(
                f"""SELECT id, decided_at, ticker, market_price, estimated_probability,
                           confidence, edge, outcome, veto_reason, stake_cents, order_id,
                           settled_yes, settled_at
                      FROM decisions {where}
                     ORDER BY id DESC
                     LIMIT ?""",
                args,
            ).fetchall()
    except Exception:
        return []
    keys = (
        "id",
        "decided_at",
        "ticker",
        "market_price",
        "estimated_probability",
        "confidence",
        "edge",
        "outcome",
        "veto_reason",
        "stake_cents",
        "order_id",
        "settled_yes",
        "settled_at",
    )
    return [dict(zip(keys, row, strict=True)) for row in rows]


def recent_fills(limit: int = 200) -> list[dict]:
    """Executed orders, newest first, for the dashboard's Orders panel.

    A fill is an APPROVED decision that record_fill attached an order id to.
    Paper ids encode the side, price and count (PAPER-buy-no-TICKER-23x8), so
    the panel can show the ticket without a second table. Settled rows carry
    the realised P&L in cents; open rows carry None.
    """
    try:
        with _connect() as conn:
            rows = conn.execute(
                """SELECT id, decided_at, ticker, market_price, estimated_probability,
                          edge, stake_cents, order_id, settled_yes, settled_at
                     FROM decisions
                    WHERE order_id IS NOT NULL
                    ORDER BY id DESC
                    LIMIT ?""",
                (int(limit),),
            ).fetchall()
    except Exception:
        return []

    fills = []
    for row in rows:
        (
            row_id,
            decided_at,
            ticker,
            market_price,
            estimated_probability,
            edge,
            stake_cents,
            order_id,
            settled_yes,
            settled_at,
        ) = row
        side, price_cents, count = _parse_order_id(order_id, market_price, stake_cents)
        pnl_cents = None
        if settled_yes is not None and price_cents and count:
            won = bool(settled_yes) if side == "yes" else not bool(settled_yes)
            pnl_cents = (100 - price_cents) * count if won else -price_cents * count
        fills.append(
            {
                "id": row_id,
                "decided_at": decided_at,
                "ticker": ticker,
                "side": side,
                "price_cents": price_cents,
                "count": count,
                "stake_cents": stake_cents,
                "order_id": order_id,
                "market_price": market_price,
                "estimated_probability": estimated_probability,
                "edge": edge,
                "settled_yes": settled_yes,
                "settled_at": settled_at,
                "pnl_cents": pnl_cents,
            }
        )
    return fills


def _parse_order_id(
    order_id: str | None, market_price: float | None, stake_cents: int | None
) -> tuple[str, int | None, int | None]:
    """Recover (side, price_cents, count) from a paper order id, else estimate.

    Paper ids look like PAPER-buy-no-KXNFLGAME-26SEP21-23x8. A real Kalshi
    order id carries none of this, so fall back to the YES market price and
    the stake to estimate a count.
    """
    text = str(order_id or "")
    if text.startswith("PAPER-"):
        parts = text.split("-")
        if len(parts) >= 5 and "x" in parts[-1]:
            side = parts[2].lower() if parts[2].lower() in ("yes", "no") else "yes"
            try:
                price, count = parts[-1].split("x")
                return side, int(price), int(count)
            except ValueError:
                pass
    price_cents = round(float(market_price) * 100) if market_price else None
    count = int(stake_cents) // price_cents if stake_cents and price_cents else None
    return "yes", price_cents, count


def realised_edge() -> dict:
    """Actual profit per $1 staked on settled trades, against what was expected.

    `expected` is what the engine thought it was buying; `realised` is what the
    market paid. A persistent gap between them is the answer to whether this
    strategy works.
    """
    with _connect() as conn:
        rows = conn.execute("""SELECT market_price, edge, settled_yes
                 FROM decisions
                WHERE settled_yes IS NOT NULL
                  AND outcome = 'APPROVED'
                  AND edge IS NOT NULL""").fetchall()

    if not rows:
        return {"n": 0, "expected": None, "realised": None}

    expected = sum(edge for _, edge, _ in rows) / len(rows)
    # A contract bought at k returns (1 - k) if it settles yes, else -k.
    realised = sum((1 - k) if settled else -k for k, _, settled in rows) / len(rows)
    return {
        "n": len(rows),
        "expected": round(expected, 4),
        "realised": round(realised, 4),
        "gap": round(realised - expected, 4),
    }
