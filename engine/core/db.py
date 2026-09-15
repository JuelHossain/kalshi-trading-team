import os

from dotenv import load_dotenv
from supabase import Client, create_client

from core.display import log_error, log_warning, AgentType

load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")

supabase: Client = None

if url and key:
    try:
        supabase = create_client(url, key)
    except Exception as e:
        log_error(f"Failed to initialize Supabase: {e}")


async def send_heartbeat(agent_id: int, name: str, status: str = "ACTIVE"):
    if not supabase:
        raise RuntimeError("Supabase client not initialized. Check SUPABASE_URL and SUPABASE_KEY in environment.")

    try:
        data = {
            "agent_id": agent_id,
            "agent_name": name,
            "status": status,
            "last_active": "now()",  # Supabase will handle this or we send ISO
        }
        # Using upsert with onConflict on agent_id
        # Note: supabase-py doesn't have a direct 'now()' string handler usually, better to use datetime
        from datetime import datetime

        data["last_active"] = datetime.utcnow().isoformat()

        supabase.table("agent_heartbeats").upsert(data, on_conflict="agent_id").execute()
    except Exception as e:
        log_error(f"Heartbeat failed for {name}: {e}")


_warned_unconfigured: set[str] = set()


async def log_to_db(table: str, data: dict):
    """Record an analytics row. Never raises.

    This is a telemetry sink, and Supabase is optional. Raising here took down
    the caller: BrainAgent.queue_for_execution awaits this between appending an
    approved trade and publishing EXECUTION_READY, the event the Hand agent
    places orders on. With Supabase unconfigured, an approved trade was queued
    and then silently never executed -- because an analytics write failed.

    An insert failure was already tolerated a few lines below; only the
    unconfigured case escalated to fatal, which was the inconsistency.
    """
    if not supabase:
        if table not in _warned_unconfigured:
            _warned_unconfigured.add(table)
            log_warning(
                f"Supabase not configured; skipping analytics for '{table}'. "
                "Set SUPABASE_URL and SUPABASE_KEY to record these rows.",
                AgentType.SOUL,
            )
        return
    try:
        supabase.table(table).insert(data).execute()
    except Exception as e:
        log_error(f"Error logging to {table}: {e}", AgentType.SOUL)


async def set_system_status(status: str, reason: str = ""):
    if not supabase:
        raise RuntimeError("Supabase client not initialized. Check SUPABASE_URL and SUPABASE_KEY in environment.")
    try:
        from datetime import datetime

        data = {
            "id": 1,
            "status": status,
            "reason": reason,
            "updated_at": datetime.utcnow().isoformat(),
        }
        supabase.table("system_status").upsert(data).execute()
    except Exception as e:
        log_error(f"Failed to set system status: {e}", AgentType.SOUL)


async def check_connection() -> bool:
    """Simple health check for Supabase connection."""
    if not supabase:
        raise RuntimeError("Supabase client not initialized. Check SUPABASE_URL and SUPABASE_KEY in environment.")
    try:
        # Using a lightweight query (fetch 1 header row from agent_heartbeats or similar)
        # We use count operation which is usually cheap
        supabase.table("agent_heartbeats").select("agent_id", count="exact").limit(1).execute()
        return True
    except Exception as e:
        log_error(f"Connection probe failed: {e}", AgentType.SOUL)
        return False
