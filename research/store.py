"""SQLite store for the probability-calibration experiment.

One row per (market, variant, prediction time). Deliberately standalone:
nothing in this package imports from ``engine/``, so the experiment runs
while the engine is being repaired, and can be deleted wholesale if the
measurement shows no edge.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "predictions.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker      TEXT NOT NULL,
    title       TEXT,
    variant     TEXT NOT NULL DEFAULT 'blind',
    asked_at    TEXT NOT NULL,
    close_time  TEXT,
    market_prob REAL NOT NULL,
    yes_bid     INTEGER,
    yes_ask     INTEGER,
    no_bid      INTEGER,
    no_ask      INTEGER,
    volume      INTEGER,
    model_prob  REAL NOT NULL,
    model_conf  REAL,
    model_name  TEXT,
    reasoning   TEXT,
    outcome     INTEGER,
    settled_at  TEXT,
    UNIQUE (ticker, variant, asked_at)
);
CREATE INDEX IF NOT EXISTS idx_pending ON predictions (outcome, close_time);
"""


@contextmanager
def connect(db_path: Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    """Open the store, creating the schema on first use.

    Args:
        db_path: Location of the SQLite file.

    Yields:
        An open connection with ``sqlite3.Row`` row factory. Committed on
        clean exit, rolled back if the block raises.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def record_prediction(conn: sqlite3.Connection, fields: dict[str, object]) -> bool:
    """Insert one prediction.

    Args:
        conn: Open connection.
        fields: Column values. Keys must match the ``predictions`` schema.

    Returns:
        True if inserted, False if it duplicated an existing
        (ticker, variant, asked_at) triple.
    """
    columns = ", ".join(fields)
    placeholders = ", ".join(f":{k}" for k in fields)
    try:
        conn.execute(
            f"INSERT INTO predictions ({columns}) VALUES ({placeholders})",  # noqa: S608
            fields,
        )
    except sqlite3.IntegrityError:
        return False
    return True


def predicted_tickers(conn: sqlite3.Connection, variant: str) -> set[str]:
    """Return tickers already predicted under ``variant``.

    Used to keep one observation per market, so settled outcomes stay
    independent rather than being the same event counted repeatedly.
    """
    rows = conn.execute(
        "SELECT DISTINCT ticker FROM predictions WHERE variant = ?", (variant,)
    )
    return {row["ticker"] for row in rows}


def pending_settlement(conn: sqlite3.Connection, now_iso: str) -> list[sqlite3.Row]:
    """Return unresolved predictions whose market close time has passed."""
    return list(
        conn.execute(
            """
            SELECT id, ticker FROM predictions
            WHERE outcome IS NULL
              AND close_time IS NOT NULL
              AND close_time < ?
            ORDER BY close_time ASC
            """,
            (now_iso,),
        )
    )


def record_outcome(
    conn: sqlite3.Connection, row_id: int, outcome: int, settled_at: str
) -> None:
    """Attach a realised outcome (1 for yes, 0 for no) to a prediction."""
    conn.execute(
        "UPDATE predictions SET outcome = ?, settled_at = ? WHERE id = ?",
        (outcome, settled_at, row_id),
    )


def settled(conn: sqlite3.Connection, variant: str | None = None) -> list[sqlite3.Row]:
    """Return every prediction that has a realised outcome."""
    if variant is None:
        return list(
            conn.execute("SELECT * FROM predictions WHERE outcome IS NOT NULL")
        )
    return list(
        conn.execute(
            "SELECT * FROM predictions WHERE outcome IS NOT NULL AND variant = ?",
            (variant,),
        )
    )


def counts(conn: sqlite3.Connection) -> dict[str, tuple[int, int]]:
    """Return per-variant (total, resolved) counts."""
    rows = conn.execute(
        """
        SELECT variant,
               COUNT(*) AS total,
               SUM(CASE WHEN outcome IS NOT NULL THEN 1 ELSE 0 END) AS resolved
        FROM predictions GROUP BY variant
        """
    )
    return {r["variant"]: (r["total"], r["resolved"]) for r in rows}
