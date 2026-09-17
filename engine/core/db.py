"""Optional Supabase analytics sink.

Nothing a trading decision depends on lives here. Heartbeats, analytics rows
and the connection probe are telemetry, and every function in this module
follows one rule: it never raises into the caller. An unconfigured or
unreachable Supabase costs a log line, not a cycle.

The project this repository was originally paired with no longer resolves in
DNS, which made the old behaviour visible: every agent attempted a DNS lookup
on every tick, each one failed, and each failure was logged. The circuit
breaker below opens on the first failure and stays open for
BREAKER_SECONDS, so an unreachable sink costs one attempt per window rather
than one per tick per agent.
"""

import os
import time
from datetime import UTC, datetime

from core.display import AgentType, log_error, log_warning
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

url: str | None = os.getenv("SUPABASE_URL")
key: str | None = os.getenv("SUPABASE_KEY")

supabase: Client | None = None

if url and key:
    try:
        supabase = create_client(url, key)
    except Exception as e:
        log_error(f"Failed to initialize Supabase: {e}")

# Seconds to stop trying after a failure. Long enough that a dead project
# costs a handful of attempts an hour; short enough that a transient outage
# recovers on its own.
BREAKER_SECONDS = float(os.getenv("SUPABASE_BREAKER_SECONDS", "300"))
_breaker_open_until = 0.0
_warned_unconfigured: set[str] = set()


def _available(purpose: str) -> bool:
    """Whether a Supabase call should be attempted right now."""
    if not supabase:
        if purpose not in _warned_unconfigured:
            _warned_unconfigured.add(purpose)
            log_warning(
                f"Supabase not configured; skipping {purpose}. "
                "Set SUPABASE_URL and SUPABASE_KEY to enable it.",
                AgentType.SOUL,
            )
        return False
    return time.monotonic() >= _breaker_open_until


def _trip_breaker(what: str, error: Exception) -> None:
    """Open the breaker after a failure and say so once per window."""
    global _breaker_open_until
    if time.monotonic() >= _breaker_open_until:
        log_error(
            f"{what} failed: {error}. Supabase disabled for {BREAKER_SECONDS:.0f}s.",
            AgentType.SOUL,
        )
    _breaker_open_until = time.monotonic() + BREAKER_SECONDS


async def send_heartbeat(agent_id: int, name: str, status: str = "ACTIVE") -> None:
    """Upsert an agent liveness row. Never raises."""
    if not _available("heartbeats"):
        return
    try:
        supabase.table("agent_heartbeats").upsert(
            {
                "agent_id": agent_id,
                "agent_name": name,
                "status": status,
                "last_active": datetime.now(UTC).isoformat(),
            },
            on_conflict="agent_id",
        ).execute()
    except Exception as e:
        _trip_breaker(f"Heartbeat for {name}", e)


async def log_to_db(table: str, data: dict) -> None:
    """Insert an analytics row. Never raises.

    BrainAgent.queue_for_execution awaits this between approving a trade and
    publishing the event the Hand places orders on. Raising here once left an
    approved trade queued and never executed because an analytics write
    failed.
    """
    if not _available(f"analytics for '{table}'"):
        return
    try:
        supabase.table(table).insert(data).execute()
    except Exception as e:
        _trip_breaker(f"Insert into {table}", e)


async def check_connection() -> bool:
    """Health probe. False when unconfigured, unreachable, or breaker open.

    Declared bool so SoulAgent.check_api_health can report "unreachable"
    without one optional dependency masking the status of every other one.
    """
    if not _available("connection probe"):
        return False
    try:
        supabase.table("agent_heartbeats").select("agent_id", count="exact").limit(1).execute()
        return True
    except Exception as e:
        _trip_breaker("Connection probe", e)
        return False
