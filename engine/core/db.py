import os

from dotenv import load_dotenv
from supabase import Client, create_client

from core.display import log_error, AgentType

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


async def log_to_db(table: str, data: dict):
    if not supabase:
        raise RuntimeError("Supabase client not initialized. Check SUPABASE_URL and SUPABASE_KEY in environment.")
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
