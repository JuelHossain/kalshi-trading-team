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
from datetime import datetime, timezone

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
                    datetime.now(timezone.utc).isoformat(),
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
    except Exception:  # noqa: BLE001 - the ledger must not break the engine
        return -1


@retry_sqlite()
def record_settlement(ticker: str, settled_yes: bool) -> int:
    """Fill in how a market resolved. Returns rows updated."""
    try:
        with _connect() as conn:
            cur = conn.execute(
                """UPDATE decisions
                      SET settled_yes = ?, settled_at = ?
                    WHERE ticker = ? AND settled_yes IS NULL""",
                (1 if settled_yes else 0, datetime.now(timezone.utc).isoformat(), ticker),
            )
            return cur.rowcount
    except Exception:  # noqa: BLE001
        return 0


def calibration(buckets: int = 5) -> list[dict]:
    """Group settled predictions and compare belief against reality.

    A calibrated forecaster's `predicted` and `actual` track each other. A
    bucket where predicted is 0.80 and actual is 0.45 is the engine being
    confidently wrong in a way no amount of downstream engineering can fix.
    """
    with _connect() as conn:
        rows = conn.execute(
            """SELECT estimated_probability, settled_yes
                 FROM decisions
                WHERE settled_yes IS NOT NULL
                  AND estimated_probability IS NOT NULL"""
        ).fetchall()

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


def realised_edge() -> dict:
    """Actual profit per $1 staked on settled trades, against what was expected.

    `expected` is what the engine thought it was buying; `realised` is what the
    market paid. A persistent gap between them is the answer to whether this
    strategy works.
    """
    with _connect() as conn:
        rows = conn.execute(
            """SELECT market_price, edge, settled_yes
                 FROM decisions
                WHERE settled_yes IS NOT NULL
                  AND outcome = 'APPROVED'
                  AND edge IS NOT NULL"""
        ).fetchall()

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
