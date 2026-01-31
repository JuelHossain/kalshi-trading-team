import asyncio
import sqlite3
import time
import uuid
from datetime import datetime
from functools import wraps
from typing import Generic, TypeVar

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
    side: str = "YES"    # YES / NO
    confidence: float
    monte_carlo_ev: float
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
# Retry Decorator for SQLite Operations
# -------------------------------------------------------------------------

def _retry_sqlite(max_retries=3, base_delay=0.05):
    """Retry decorator for SQLite operations that may encounter locked database."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "locked" in str(e).lower() and attempt < max_retries - 1:
                        # Exponential backoff
                        delay = base_delay * (2 ** attempt)
                        time.sleep(delay)
                        continue
                    # Re-raise if not locked error or retries exhausted
                    raise
            return None
        return wrapper
    return decorator

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
            raise ValueError(f"Invalid table name: {table_name}. Must be one of: {self.ALLOWED_TABLES}")

        self.db_path = db_path
        self.table_name = table_name
        self.model_cls = model_cls
        self._lock = asyncio.Lock()

        # Initialize DB synchronously (safe at startup)
        self._init_db()

    def _init_db(self):
        """Create the table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
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
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_prio ON {self.table_name} (priority DESC, timestamp ASC)")
        conn.commit()
        conn.close()

    async def push(self, item: T, priority: int = 0):
        """Add an item to the queue"""
        async with self._lock:
            # We use runs_in_executor for DB ops to keep the loop non-blocking
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._push_sync,
                item,
                priority
            )
            # Notify potential listeners (if implementing wait logic later)

    @_retry_sqlite(max_retries=3, base_delay=0.05)
    def _push_sync(self, item: T, priority: int):
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            payload_json = item.model_dump_json()
            # Use item.id if available, else gen generic
            item_id = getattr(item, "id", str(uuid.uuid4()))
            ts = datetime.now().timestamp()
            
            cursor.execute(f"""
                INSERT OR REPLACE INTO {self.table_name} (id, priority, timestamp, payload, status)
                VALUES (?, ?, ?, ?, 'QUEUED')
            """, (str(item_id), priority, ts, payload_json))
            conn.commit()
        finally:
            conn.close()

    async def pop(self) -> T | None:
        """Get and REMOVE the next item from the queue"""
        async with self._lock:
            return await asyncio.get_event_loop().run_in_executor(
                None,
                self._pop_sync
            )

    @_retry_sqlite(max_retries=3, base_delay=0.05)
    def _pop_sync(self) -> T | None:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            # FIFO: Highest priority first, then oldest timestamp
            cursor.execute(f"""
                SELECT id, payload FROM {self.table_name} 
                WHERE status='QUEUED' 
                ORDER BY priority DESC, timestamp ASC 
                LIMIT 1
            """)
            row = cursor.fetchone()
            
            if row:
                item_id, payload = row
                # Delete immediately (or mark processing if we want ACK logic later)
                # For now, simple queue semantics: Pop = Consume
                cursor.execute(f"DELETE FROM {self.table_name} WHERE id = ?", (item_id,))
                
                if cursor.rowcount == 0:
                    # This should rarely happen in single-reader scneario, but good for safety
                    print(f"[SYNAPSE] WARN: Failed to delete popped item {item_id} (rowcount=0)")
                    
                conn.commit()
                
                # Reconstruct Pydantic model
                return self.model_cls.model_validate_json(payload)
            return None
        finally:
            conn.close()
    
    async def size(self) -> int:
        async with self._lock:
             return await asyncio.get_event_loop().run_in_executor(None, self._size_sync)

    def _size_sync(self) -> int:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            return cursor.fetchone()[0]
        finally:
            conn.close()

# -------------------------------------------------------------------------
# 3. Synapse Manager (The Central Nervous System)
# -------------------------------------------------------------------------

class Synapse:
    """
    Central Message Broker using Persistent Queues.
    Passed to all agents to replace direct references.
    """
    def __init__(self, db_path: str = "ghost_memory.db"):
        self.db_path = db_path
        
        # 1. Opportunity Queue (Senses -> Brain)
        self.opportunities = PersistentQueue[Opportunity](
            db_path, "queue_opportunities", Opportunity
        )
        
        self.executions = PersistentQueue[ExecutionSignal](
            db_path, "queue_executions", ExecutionSignal
        )

        # 3. Error Box (All Agents -> Engine Monitoring)
        self.errors = PersistentQueue[SynapseError](
            db_path, "queue_errors", SynapseError
        )

    async def clear_all(self):
        """Emergency Wipe (Kill Switch Reset)"""
        # ... logic to truncate tables ...
