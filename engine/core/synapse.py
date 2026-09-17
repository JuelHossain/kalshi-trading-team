"""Persistent queues between the agents.

Three SQLite-backed queues: opportunities (Senses to Brain), executions
(Brain to Hand) and errors. Rows survive a restart, which is the point.
The error box doubles as a safety latch: while it holds anything, no cycle
is authorised, and only an explicit drain clears it.
"""

import asyncio
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Generic, TypeVar

from core.display import log_warning
from core.shared_utils import retry_sqlite
from pydantic import BaseModel, Field

# -------------------------------------------------------------------------
# 1. Type Definitions (Schemas)
# -------------------------------------------------------------------------


class MarketData(BaseModel):
    """Raw market data payload"""

    ticker: str
    title: str
    subtitle: str
    yes_price: int
    no_price: int
    volume: int
    expiration: str
    raw_response: dict = {}


class Opportunity(BaseModel):
    """An identified opportunity ready for analysis"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ticker: str
    market_data: MarketData
    source: str = "SENSES"
    timestamp: datetime = Field(default_factory=datetime.now)
    vegas_odds: float | None = None

    # Priority for processing (Higher = More Urgent)
    priority: int = 0


class ExecutionSignal(BaseModel):
    """A vetted trade decision ready for execution"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    target_opportunity: Opportunity
    action: str = "BUY"  # BUY / SELL
    side: str = "YES"  # YES / NO
    confidence: float
    monte_carlo_ev: float
    # The Brain's probability estimate. The Hand needs it to size the position:
    # Kelly is (p - k)/(1 - k), so edge alone is not enough.
    estimated_probability: float | None = None
    # The side's own price and probability. For NO these are (1-k) and (1-p),
    # so the Hand sizes and prices the side it is actually buying.
    side_price: float | None = None
    side_probability: float | None = None
    reasoning: str
    suggested_count: int
    status: str = "PENDING"  # PENDING, EXECUTED, FAILED, CANCELLED


class SynapseError(BaseModel):
    """A persistent error entry for debugging and monitoring"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    agent_name: str
    code: str
    message: str
    severity: str
    domain: str
    hint: str | None = None
    context: dict = {}
    stack_trace: str | None = None


# Generic Type for Queues
T = TypeVar("T", bound=BaseModel)

# -------------------------------------------------------------------------
# 2. Persistent Queue (SQLite Backed)
# -------------------------------------------------------------------------


class PersistentQueue(Generic[T]):
    """
    Asyncio-compatible queue backed by SQLite.
    Ensures data survival across crashes/restarts.
    """

    # Whitelist of allowed table names to prevent SQL injection
    ALLOWED_TABLES = {"queue_opportunities", "queue_executions", "queue_errors"}

    def __init__(self, db_path: str, table_name: str, model_cls: type[T]):
        if table_name not in self.ALLOWED_TABLES:
            raise ValueError(
                f"Invalid table name: {table_name}. Must be one of: {self.ALLOWED_TABLES}"
            )

        self.db_path = db_path
        self.table_name = table_name
        self.model_cls = model_cls
        self._lock = asyncio.Lock()

        # One connection for the life of the queue. Every operation used to
        # open, use and close its own, and every single-row commit paid a
        # full fsync: 2.6 ms per push and per pop measured here, with the
        # Brain polling size() every second on top. WAL journaling with
        # synchronous=NORMAL keeps the database consistent across a process
        # crash -- what these queues exist to survive -- without forcing the
        # disk to sync on every row. Only an OS crash or power loss can drop
        # the most recent commits, and a queue of market opportunities does
        # not need that guarantee.
        #
        # Operations run on executor threads, so check_same_thread is off;
        # the lock above serialises them, which is what sqlite3 requires of
        # a connection shared that way.
        self._conn: sqlite3.Connection | None = sqlite3.connect(
            self.db_path, check_same_thread=False
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._init_db()

    def _init_db(self):
        """Create the table and its FIFO index if they do not exist."""
        conn = self._conn
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id TEXT PRIMARY KEY,
                priority INTEGER DEFAULT 0,
                timestamp REAL,
                payload TEXT,
                status TEXT DEFAULT 'QUEUED'
            )
        """)
        # Index for efficient FIFO retrieval
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_prio ON {self.table_name} (priority DESC, timestamp ASC)"
        )
        conn.commit()

    def close(self) -> None:
        """Release the connection. Safe to call more than once."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    async def push(self, item: T, priority: int = 0):
        """Add an item to the queue"""
        async with self._lock:
            # We use runs_in_executor for DB ops to keep the loop non-blocking
            await asyncio.get_event_loop().run_in_executor(None, self._push_sync, item, priority)
            # Notify potential listeners (if implementing wait logic later)

    @retry_sqlite(max_retries=3, base_delay=0.05)
    def _push_sync(self, item: T, priority: int):
        payload_json = item.model_dump_json()
        # Use item.id if available, else gen generic
        item_id = getattr(item, "id", str(uuid.uuid4()))
        ts = datetime.now().timestamp()

        self._conn.execute(
            f"""
            INSERT OR REPLACE INTO {self.table_name} (id, priority, timestamp, payload, status)
            VALUES (?, ?, ?, ?, 'QUEUED')
        """,
            (str(item_id), priority, ts, payload_json),
        )
        self._conn.commit()

    async def pop(self) -> T | None:
        """Get and REMOVE the next item from the queue"""
        async with self._lock:
            return await asyncio.get_event_loop().run_in_executor(None, self._pop_sync)

    @retry_sqlite(max_retries=3, base_delay=0.05)
    def _pop_sync(self) -> T | None:
        cursor = self._conn.cursor()
        # FIFO: highest priority first, then oldest timestamp.
        cursor.execute(f"""
            SELECT id, payload FROM {self.table_name}
            WHERE status='QUEUED'
            ORDER BY priority DESC, timestamp ASC
            LIMIT 1
        """)
        row = cursor.fetchone()
        if not row:
            return None

        item_id, payload = row
        # Pop is consume: the row is deleted, not marked. A row that vanished
        # between the SELECT and the DELETE means a second reader, which this
        # queue is not designed for; say so rather than return a duplicate.
        cursor.execute(f"DELETE FROM {self.table_name} WHERE id = ?", (item_id,))
        self._conn.commit()
        if cursor.rowcount == 0:
            log_warning(f"Popped {item_id} from {self.table_name} but it was already gone")
            return None

        return self.model_cls.model_validate_json(payload)

    async def size(self) -> int:
        """Number of rows currently queued."""
        async with self._lock:
            return await asyncio.get_event_loop().run_in_executor(None, self._size_sync)

    def _size_sync(self) -> int:
        return self._conn.execute(f"SELECT COUNT(*) FROM {self.table_name}").fetchone()[0]

    async def clear(self) -> int:
        """Remove every row. Returns how many were removed.

        The table name is fixed at construction and checked against
        ALLOWED_TABLES, so it is not attacker-controlled here.
        """
        async with self._lock:
            return await asyncio.get_event_loop().run_in_executor(None, self._clear_sync)

    def _clear_sync(self) -> int:
        removed = self._conn.execute(f"DELETE FROM {self.table_name}").rowcount
        self._conn.commit()
        return max(0, removed)


# -------------------------------------------------------------------------
# 3. Synapse Manager (The Central Nervous System)
# -------------------------------------------------------------------------


class Synapse:
    """
    Central Message Broker using Persistent Queues.
    Passed to all agents to replace direct references.
    """

    def __init__(self, db_path: str | None = None):
        # Explicit arg wins, then GHOST_SYNAPSE_DB, then the production default.
        db_path = db_path or os.getenv("GHOST_SYNAPSE_DB", "ghost_memory.db")
        self.db_path = db_path

        # 1. Opportunity Queue (Senses -> Brain)
        self.opportunities = PersistentQueue[Opportunity](
            db_path, "queue_opportunities", Opportunity
        )

        self.executions = PersistentQueue[ExecutionSignal](
            db_path, "queue_executions", ExecutionSignal
        )

        # 3. Error Box (All Agents -> Engine Monitoring)
        self.errors = PersistentQueue[SynapseError](db_path, "queue_errors", SynapseError)

    def close(self) -> None:
        """Close every queue's connection. Called at engine shutdown."""
        for queue in (self.opportunities, self.executions, self.errors):
            queue.close()

    async def drain_errors(self) -> int:
        """Empty the error box and report how many entries were cleared.

        authorize_cycle halts while this box is non-empty. That latch is
        deliberate, but without a drain a single recoverable error stopped
        every future cycle permanently. Deliberately narrow: the opportunity
        and execution queues are untouched, so acknowledging an error cannot
        silently discard pending work.
        """
        return await self.errors.clear()

    async def clear_all(self) -> dict[str, int]:
        """Emergency wipe of every queue. Returns per-queue removal counts.

        Previously a stub with no body, so an emergency reset reported
        success while leaving all three queues exactly as they were.
        """
        return {
            "opportunities": await self.opportunities.clear(),
            "executions": await self.executions.clear(),
            "errors": await self.errors.clear(),
        }
