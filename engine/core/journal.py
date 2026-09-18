"""A durable record of everything the engine says and does.

The console scrolls away and the dashboard only sees what happens while
it is open. This journal writes every bus event of interest to SQLite so
the bot's behaviour can be studied afterwards: what each agent logged,
every estimate and verdict, every fill and exit, every vault reading,
every error, with the cycle it belonged to.

One connection in WAL mode, the same trade-off as the Synapse queues: a
process crash loses nothing, and a single row costs no fsync. Rows are
pruned past `MAX_ROWS` so the file stays bounded on a small VM.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import UTC, datetime
from typing import Any

MAX_ROWS = 200_000
PRUNE_EVERY = 5_000

# Bus topics worth keeping, and the level they are filed under when the
# payload carries none of its own.
TOPICS: dict[str, str] = {
    "SYSTEM_LOG": "INFO",
    "SIM_RESULT": "INFO",
    "TRADE_RESULT": "INFO",
    "EXECUTION_READY": "INFO",
    "POSITION_CLOSED": "INFO",
    "SYSTEM_ERROR": "ERROR",
    "SYSTEM_LOCKDOWN": "ERROR",
    "SYSTEM_FATAL": "ERROR",
    "CYCLE_START": "INFO",
    "CYCLE_COMPLETE": "INFO",
    "REQUEST_RESTOCK": "DEBUG",
    "OPPORTUNITIES_READY": "INFO",
    "MANDATE_SELECTED": "INFO",
    "VAULT_UPDATE": "DEBUG",
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       TEXT    NOT NULL,
    topic    TEXT    NOT NULL,
    agent    TEXT,
    level    TEXT,
    cycle    INTEGER,
    message  TEXT,
    payload  TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_topic ON events(topic);
CREATE INDEX IF NOT EXISTS idx_events_agent ON events(agent);
CREATE INDEX IF NOT EXISTS idx_events_cycle ON events(cycle);
"""


def _db_path() -> str:
    return os.getenv("GHOST_JOURNAL_DB", "ghost_journal.db")


class Journal:
    """Append-only event log. Never raises into the caller."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or _db_path()
        self._lock = threading.Lock()
        self._writes = 0
        self._conn: sqlite3.Connection | None = None
        try:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.executescript(_SCHEMA)
        except sqlite3.Error:
            self._conn = None

    # ── writes ─────────────────────────────────────────────────────────
    def record(
        self,
        topic: str,
        payload: dict[str, Any] | None,
        sender: str | None = None,
        cycle: int | None = None,
    ) -> int:
        """File one event. Returns the row id, or -1 if the journal is unavailable."""
        if self._conn is None:
            return -1
        payload = payload or {}
        agent = str(payload.get("agent_name") or sender or "").upper() or None
        level = str(
            payload.get("level") or payload.get("severity") or TOPICS.get(topic, "INFO")
        ).upper()
        message = payload.get("message")
        if message is None:
            message = _summarise(topic, payload)
        row_cycle = payload.get("cycle", payload.get("cycleId", cycle))
        try:
            with self._lock:
                cur = self._conn.execute(
                    "INSERT INTO events (ts, topic, agent, level, cycle, message, payload) VALUES (?,?,?,?,?,?,?)",
                    (
                        str(payload.get("timestamp") or datetime.now(UTC).isoformat()),
                        topic,
                        agent,
                        level,
                        int(row_cycle) if isinstance(row_cycle, int | float) else None,
                        str(message)[:2000],
                        json.dumps(payload, default=str)[:8000],
                    ),
                )
                self._conn.commit()
                self._writes += 1
                if self._writes % PRUNE_EVERY == 0:
                    self._prune()
                return cur.lastrowid or -1
        except sqlite3.Error:
            return -1

    def _prune(self) -> None:
        assert self._conn is not None
        self._conn.execute(
            "DELETE FROM events WHERE id < (SELECT COALESCE(MAX(id), 0) - ? FROM events)",
            (MAX_ROWS,),
        )
        self._conn.commit()

    # ── reads ──────────────────────────────────────────────────────────
    def query(
        self,
        limit: int = 200,
        agent: str | None = None,
        topic: str | None = None,
        cycle: int | None = None,
        since_id: int | None = None,
        level: str | None = None,
    ) -> list[dict[str, Any]]:
        """Newest first unless `since_id` is given, in which case oldest first after it."""
        if self._conn is None:
            return []
        clauses: list[str] = []
        args: list[Any] = []
        if agent:
            clauses.append("agent = ?")
            args.append(agent.upper())
        if topic:
            clauses.append("topic = ?")
            args.append(topic)
        if cycle is not None:
            clauses.append("cycle = ?")
            args.append(int(cycle))
        if since_id is not None:
            clauses.append("id > ?")
            args.append(int(since_id))
        if level:
            clauses.append("level = ?")
            args.append(level.upper())
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        order = "ASC" if since_id is not None else "DESC"
        try:
            with self._lock:
                rows = self._conn.execute(
                    f"SELECT id, ts, topic, agent, level, cycle, message, payload FROM events {where} ORDER BY id {order} LIMIT ?",
                    (*args, max(1, min(5000, int(limit)))),
                ).fetchall()
        except sqlite3.Error:
            return []
        out = []
        for row_id, ts, row_topic, row_agent, row_level, row_cycle, message, payload in rows:
            try:
                data = json.loads(payload) if payload else {}
            except json.JSONDecodeError:
                data = {}
            out.append(
                {
                    "id": row_id,
                    "ts": ts,
                    "topic": row_topic,
                    "agent": row_agent,
                    "level": row_level,
                    "cycle": row_cycle,
                    "message": message,
                    "payload": data,
                }
            )
        return out

    def count(self) -> int:
        if self._conn is None:
            return 0
        try:
            with self._lock:
                return int(self._conn.execute("SELECT COUNT(*) FROM events").fetchone()[0])
        except sqlite3.Error:
            return 0

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None


def _summarise(topic: str, payload: dict[str, Any]) -> str:
    """A one-line message for events that carry structured data only."""
    if topic == "SIM_RESULT":
        return (
            f"{payload.get('ticker', '?')}: win rate {float(payload.get('win_rate', 0)):.2f}, "
            f"EV {float(payload.get('ev_score', 0)):+.3f}, {'veto' if payload.get('veto') else 'pass'}"
        )
    if topic == "TRADE_RESULT":
        return f"{payload.get('ticker', '?')}: {payload.get('outcome', '?')} · {payload.get('details', '')}"
    if topic == "EXECUTION_READY":
        return f"{payload.get('ticker', '?')}: signal {payload.get('signal_id', '')} · EV {float(payload.get('ev', 0)):+.3f}"
    if topic == "POSITION_CLOSED":
        return f"{payload.get('ticker', '?')}: closed at {payload.get('price', '?')}¢ · {payload.get('reason', '')}"
    if topic == "VAULT_UPDATE":
        return f"balance ${float(payload.get('total', 0)):.2f} · profit ${float(payload.get('currentProfit', 0)):.2f}"
    if topic in ("CYCLE_START", "CYCLE_COMPLETE"):
        return f"cycle {payload.get('cycle', '?')}"
    if topic in ("SYSTEM_LOCKDOWN", "SYSTEM_FATAL"):
        return str(payload.get("reason") or payload.get("message") or topic)
    if topic == "OPPORTUNITIES_READY":
        return f"{payload.get('count', '?')} opportunities queued"
    return topic.lower().replace("_", " ")
