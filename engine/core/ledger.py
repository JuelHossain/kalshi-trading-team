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

# Added after the table above shipped, so existing databases need the columns
# added rather than created. Without these, the only way to know which side a
# fill bought and at what price was to parse it back out of a paper order id
# (_parse_order_id) -- which cannot be done at all for a real Kalshi order id,
# so every live fill's realised P&L was computed as though it had bought YES.
_FILL_COLUMNS = {
    "side": "TEXT",
    "price_cents": "INTEGER",
    "count": "INTEGER",
}

_SETTLED_STATUSES = {"settled", "finalized", "determined"}


def _db_path() -> str:
    return os.getenv("GHOST_LEDGER_DB", "ghost_ledger.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.executescript(_SCHEMA)
    existing = {row[1] for row in conn.execute("PRAGMA table_info(decisions)")}
    for column, sqltype in _FILL_COLUMNS.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE decisions ADD COLUMN {column} {sqltype}")
    return conn


def outcome_from_market(market: dict) -> bool | None:
    """Whether a Kalshi market record resolved yes, no, or not yet.

    A market can be past its close time but not yet determined, so status is
    checked before the result field is trusted. Mirrors research/settle's
    outcome_from; duplicated rather than imported so the trading engine does
    not pull in research's own dependencies (aiohttp session helpers, its own
    prediction store) just for this one mapping.
    """
    status = str(market.get("status", "")).lower()
    result = str(market.get("result", "")).lower()
    if status not in _SETTLED_STATUSES and not result:
        return None
    if result == "yes":
        return True
    if result == "no":
        return False
    return None


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
def record_fill(
    ticker: str,
    stake_cents: int,
    order_id: str | None,
    side: str | None = None,
    price_cents: int | None = None,
    count: int | None = None,
) -> int:
    """Attach an executed order to its APPROVED decision. Returns rows updated.

    stake_cents and order_id existed as columns from the start and nothing
    ever wrote them: five paper fills in one run left zero filled rows. Without
    this, realised P&L cannot be computed from the ledger, which is the one
    thing a paper soak exists to measure.

    side, price_cents and count are optional so existing callers (and the
    test suite) keep working unchanged, but the caller in hand/agent.py
    supplies them: they are what recent_fills and realised_edge need to get a
    live NO fill's P&L sign right, which _parse_order_id cannot recover from a
    real Kalshi order id.

    Targets the most recent APPROVED row for the ticker that has no order
    yet, so two fills on one market attach to two decisions rather than the
    second overwriting the first.
    """
    try:
        with _connect() as conn:
            cur = conn.execute(
                """UPDATE decisions
                      SET stake_cents = ?, order_id = ?, side = ?, price_cents = ?, count = ?
                    WHERE id = (
                        SELECT id FROM decisions
                         WHERE ticker = ? AND outcome = 'APPROVED' AND order_id IS NULL
                         ORDER BY id DESC LIMIT 1
                    )""",
                (
                    int(stake_cents),
                    order_id,
                    side.lower() if side else None,
                    int(price_cents) if price_cents is not None else None,
                    int(count) if count is not None else None,
                    ticker,
                ),
            )
            return cur.rowcount
    except Exception:
        return 0


def unsettled_fill_tickers() -> list[str]:
    """Tickers with an executed fill whose settlement is still unknown.

    What Hand.settle_positions polls each cycle. Nothing called
    record_settlement in production before this existed, so every fill's
    pnl_cents stayed None forever and calibration() had nothing to measure.
    """
    try:
        with _connect() as conn:
            rows = conn.execute("""SELECT DISTINCT ticker FROM decisions
                    WHERE order_id IS NOT NULL AND settled_yes IS NULL""").fetchall()
        return [row[0] for row in rows]
    except Exception:
        return []


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
    record_fill now stores the ticket (side, price_cents, count) directly;
    _parse_order_id is kept only for rows written before those columns
    existed, or for a caller that did not supply them. Settled rows carry
    the realised P&L in cents; open rows carry None.
    """
    try:
        with _connect() as conn:
            rows = conn.execute(
                """SELECT id, decided_at, ticker, market_price, estimated_probability,
                          edge, stake_cents, order_id, settled_yes, settled_at,
                          side, price_cents, count
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
            side,
            price_cents,
            count,
        ) = row
        if side is None or price_cents is None or count is None:
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

    edge and market_price are always in YES terms (Brain records them from
    the YES market price, regardless of which side it went on to buy -- see
    agents/brain/agent.py). A NO trade's own edge and P&L are the negation of
    that: buying NO at (1 - k) when the model believes p is the same bet as
    buying YES at k when it believes (1 - p), so this is side-aware rather
    than treating every fill as a YES purchase, which silently flipped the
    sign of every live NO trade's reported P&L.

    Rows with no stored side fall back to _parse_order_id, the same recovery
    recent_fills uses -- a legacy PAPER- id encodes its own side correctly, so
    defaulting it to "yes" here (as this used to) flipped those rows' P&L
    exactly like a real order id with no ticket does.
    """
    with _connect() as conn:
        rows = conn.execute(
            """SELECT market_price, edge, settled_yes, side, price_cents, order_id, stake_cents
                 FROM decisions
                WHERE settled_yes IS NOT NULL
                  AND outcome = 'APPROVED'
                  AND edge IS NOT NULL"""
        ).fetchall()

    if not rows:
        return {"n": 0, "expected": None, "realised": None}

    total_expected = 0.0
    total_realised = 0.0
    for market_price, edge, settled_yes, side, price_cents, order_id, stake_cents in rows:
        if side is None:
            side, price_cents, _count = _parse_order_id(order_id, market_price, stake_cents)
        side = side.lower()
        k = (price_cents / 100.0) if price_cents is not None else market_price
        won = bool(settled_yes) if side == "yes" else not bool(settled_yes)
        # A contract bought at k returns (1 - k) if its own side wins, else -k.
        total_realised += (1 - k) if won else -k
        total_expected += edge if side == "yes" else -edge

    n = len(rows)
    expected = total_expected / n
    realised = total_realised / n
    return {
        "n": n,
        "expected": round(expected, 4),
        "realised": round(realised, 4),
        "gap": round(realised - expected, 4),
    }
