"""
HTTP route handlers for Ghost Engine.
Extracted from main.py for better organization.
"""
import asyncio
import json
import sqlite3
from datetime import datetime

from aiohttp import web
from core.constants import AGENT_NAME_TO_ID, AGENT_TO_PHASE, MAX_EXECUTION_QUEUE_SIZE
from core.event_formatter import (
    format_error_event,
    format_log_event,
    format_simulation_event,
    format_state_event,
    format_vault_event,
)


def register_all_routes(app, engine):
    """
    Register all HTTP routes for the Ghost Engine.

    Args:
        app: aiohttp Application
        engine: GhostEngine instance
    """
    # Cycle control routes
    app.router.add_post("/trigger", trigger_cycle(engine))
    app.router.add_post("/cancel", cancel_cycle(engine))
    app.router.add_post("/api/trigger", trigger_cycle(engine))
    app.router.add_post("/api/cancel", cancel_cycle(engine))

    # Kill switch routes
    app.router.add_post("/kill-switch", activate_kill_switch(engine))
    app.router.add_post("/deactivate-kill-switch", deactivate_kill_switch(engine))
    app.router.add_post("/api/kill-switch", activate_kill_switch(engine))
    app.router.add_post("/api/deactivate-kill-switch", deactivate_kill_switch(engine))

    # System control routes
    app.router.add_post("/reset", reset_system(engine))
    app.router.add_get("/health", health_check(engine))
    app.router.add_post("/api/reset", reset_system(engine))
    app.router.add_get("/api/health", health_check(engine))

    # Autopilot routes
    app.router.add_post("/autopilot/start", start_autopilot(engine))
    app.router.add_post("/autopilot/stop", stop_autopilot(engine))
    app.router.add_get("/autopilot/status", autopilot_status(engine))
    app.router.add_post("/api/autopilot/start", start_autopilot(engine))
    app.router.add_post("/api/autopilot/stop", stop_autopilot(engine))
    app.router.add_get("/api/autopilot/status", autopilot_status(engine))

    # Data routes
    app.router.add_get("/pnl", get_pnl(engine))
    app.router.add_get("/pnl/heatmap", get_pnl_heatmap(engine))
    app.router.add_get("/api/pnl", get_pnl(engine))
    app.router.add_get("/api/pnl/heatmap", get_pnl_heatmap(engine))

    # SSE stream
    app.router.add_get("/stream", stream_logs(engine))
    app.router.add_get("/api/stream", stream_logs(engine))

    # Synapse routes
    app.router.add_get("/synapse/queues", get_synapse_queues(engine))
    app.router.add_get("/api/synapse/queues", get_synapse_queues(engine))

    # Environment routes
    app.router.add_get("/env-health", get_env_health(engine))
    app.router.add_get("/api/env-health", get_env_health(engine))

    # Emergency routes
    app.router.add_post("/ragnarok", trigger_ragnarok(engine))
    app.router.add_post("/api/ragnarok", trigger_ragnarok(engine))

    # Auth routes
    from core.auth import login_handler, logout_handler, verify_handler
    app.router.add_post("/auth/login", login_handler)
    app.router.add_get("/auth/verify", verify_handler)
    app.router.add_post("/auth/logout", logout_handler)
    app.router.add_post("/api/auth/login", login_handler)
    app.router.add_get("/api/auth/verify", verify_handler)
    app.router.add_post("/api/auth/logout", logout_handler)

    # Legacy auth endpoint
    app.router.add_post("/auth", auth_handler(engine))
    app.router.add_post("/api/auth", auth_handler(engine))


# ==============================================================================
# Route Handlers
# ==============================================================================

def trigger_cycle(engine):
    async def handler(request):
        data = await request.json()
        is_paper = data.get("isPaperTrading", True)
        asyncio.create_task(engine.execute_single_cycle(is_paper))
        return web.json_response(
            {
                "status": "triggered",
                "cycleId": engine.cycle_count + 1,
                "isProcessing": engine.is_processing,
            }
        )
    return handler


def activate_kill_switch(engine):
    async def handler(request):
        engine.manual_kill_switch = True
        # FIX: Immediate Halt (Atomicity)
        engine.is_processing = False
        engine.cycle_count = 0
        engine.last_cycle_time = None  # Rate limit tracking
        engine.running = False

        await engine.bus.publish(
            "SYSTEM_LOG",
            {
                "level": "ERROR",
                "message": "[GHOST] MANUAL KILL SWITCH ACTIVATED - Engine Halted",
                "agent_id": 1,
                "timestamp": datetime.now().isoformat(),
            },
            "GHOST",
        )
        return web.json_response(
            {"status": "killed", "message": "Manual Kill Switch Activated. Engine Halted."}
        )
    return handler


def deactivate_kill_switch(engine):
    async def handler(request):
        engine.manual_kill_switch = False
        await engine.bus.publish(
            "SYSTEM_LOG",
            {
                "level": "INFO",
                "message": "[GHOST] MANUAL KILL SWITCH DEACTIVATED",
                "agent_id": 1,
                "timestamp": datetime.now().isoformat(),
            },
            "GHOST",
        )
        return web.json_response(
            {"status": "active", "message": "Manual Kill Switch Deactivated."}
        )
    return handler


def reset_system(engine):
    async def handler(request):
        engine.manual_kill_switch = False
        engine.is_processing = False
        engine.running = False
        return web.json_response({"status": "reset"})
    return handler


def cancel_cycle(engine):
    async def handler(request):
        """Gracefully cancel the current cycle and disable autopilot."""
        # Always allow cancellation to ensure we can stop runaway loops
        engine.is_processing = False

        # 1. Stop Autopilot (Critical fix for "runaway train")
        await engine.bus.publish("SYSTEM_CONTROL", {"action": "STOP_AUTOPILOT"}, "HTTP")
        engine.running = False

        # --- HARDENING: Emergency Rollback on Cancellation ---
        engine.vault.release_all_reservations()

        # 2. Reset System State
        await engine.bus.publish(
            "SYSTEM_STATE",
            {"isProcessing": False, "activeAgentId": None},
            "GHOST",
        )

        # 3. Log Cancellation
        await engine.bus.publish(
            "SYSTEM_LOG",
            {
                "level": "WARN",
                "message": "[GHOST] Cycle cancelled by user. Autopilot DISABLED.",
                "agent_id": 1,
                "timestamp": datetime.now().isoformat(),
            },
            "GHOST",
        )

        return web.json_response({"status": "cancelled", "message": "Cycle cancelled and Autopilot disabled."})
    return handler


def health_check(engine):
    async def handler(request):
        return web.json_response(
            {
                "status": "healthy",
                "agents": 4,
                "cycle": engine.cycle_count,
                "balance": engine.vault.current_balance / 100,
            }
        )
    return handler


def start_autopilot(engine):
    async def handler(request):
        """Enable autonomous cycle looping."""
        data = await request.json()
        is_paper = data.get("isPaperTrading", True)
        await engine.bus.publish("SYSTEM_CONTROL", {"action": "START_AUTOPILOT", "isPaperTrading": is_paper}, "HTTP")
        return web.json_response({"status": "autopilot_started", "mode": "AUTOPILOT"})
    return handler


def stop_autopilot(engine):
    async def handler(request):
        """Disable autonomous cycle looping (Graceful Pause)."""
        await engine.bus.publish("SYSTEM_CONTROL", {"action": "STOP_AUTOPILOT"}, "HTTP")
        return web.json_response({"status": "autopilot_stopped", "mode": "MANUAL"})
    return handler


def autopilot_status(engine):
    async def handler(request):
        """Get current autopilot status."""
        return web.json_response({
            "autopilot_enabled": engine.soul.autopilot_enabled if hasattr(engine, "soul") else False,
            "is_paper_trading": engine.soul.is_paper_trading if hasattr(engine, "soul") else True,
            "is_locked_down": engine.soul.is_locked_down if hasattr(engine, "soul") else False,
            "is_processing": engine.is_processing,
            "cycle_count": engine.cycle_count,
        })
    return handler


def stream_logs(engine):
    async def handler(request):
        """SSE stream for real-time logs with proper error handling."""
        response = web.StreamResponse(
            status=200,
            reason="OK",
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                # CORS handled by middleware
            },
        )

        try:
            await response.prepare(request)
        except (ConnectionResetError, asyncio.CancelledError, OSError) as e:
            print(f"[GHOST] SSE connection error: {e}")
            return response

        queue = asyncio.Queue()
        engine.sse_clients.add(queue)

        try:
            while True:
                event = await queue.get()
                data = json.dumps(event)
                try:
                    await response.write(f"data: {data}\n\n".encode())
                except (ConnectionResetError, asyncio.CancelledError, OSError):
                    # Client disconnected - benign error
                    break
        except asyncio.CancelledError:
            pass
        finally:
            try:
                engine.sse_clients.remove(queue)
            except KeyError:
                pass  # Already removed

        return response
    return handler


def auth_handler(engine):
    async def handler(request):
        """Handle authentication check."""
        from core.auth import auth_manager

        # Return actual session data from auth_manager
        # In 2-tier architecture, we check the auth_manager session state
        if auth_manager.authenticated:
            return web.json_response({
                "isAuthenticated": True,
                "user": {
                    "id": "user_1",
                    "email": "trader@sentient-alpha.com" if auth_manager.is_production else "demo@kalshi.com",
                    "name": "Sentient Trader" if auth_manager.is_production else "Demo Trader"
                },
                "mode": auth_manager.mode,
                "is_production": auth_manager.is_production
            })
        return web.json_response({
            "isAuthenticated": False,
            "user": None,
            "mode": "demo",
            "is_production": False
        })
    return handler


def get_pnl(engine):
    async def handler(request):
        """Get PnL history (simulated for now)."""
        # In a real scenario, query database for balance history
        current_balance = engine.vault.current_balance / 100

        # Generate mock history for the last 24h
        now = datetime.now()
        history = []
        for i in range(24):
            ts = now.timestamp() - (i * 3600)
            # Simulated fluctuation
            val = current_balance - (i * 5)
            history.append({
                "timestamp": datetime.fromtimestamp(ts).isoformat(),
                "balance": val
            })

        return web.json_response({
            "currentBalance": current_balance,
            "history": history[::-1] # Oldest first
        })
    return handler


def get_pnl_heatmap(engine):
    async def handler(request):
        """Get daily PnL heatmap."""
        # Mock data for heatmap
        heatmap = []
        import random
        today = datetime.now()
        for i in range(30): # Last 30 days
            date = today.timestamp() - (i * 86400)
            heatmap.append({
                "date": datetime.fromtimestamp(date).strftime("%Y-%m-%d"),
                "pnl": random.uniform(-50, 100),
                "count": random.randint(1, 10)
            })
        return web.json_response({"heatmap": heatmap})
    return handler


def get_synapse_queues(engine):
    async def handler(request):
        """Get current Synapse queue states for real-time logistics visualization."""
        # Get queue sizes
        opp_size = await engine.synapse.opportunities.size()
        exec_size = await engine.synapse.executions.size()

        # Snapshot opportunity queue (peek without consuming)
        opportunities = []
        executions = []

        # Peek at opportunities (read from DB without popping)
        conn = sqlite3.connect(engine.synapse.db_path)
        try:
            cursor = conn.cursor()
            # Get last 10 opportunities
            cursor.execute("""
                SELECT payload FROM queue_opportunities
                WHERE status='QUEUED'
                ORDER BY priority DESC, timestamp ASC
                LIMIT 10
            """)
            for row in cursor.fetchall():
                from core.synapse import Opportunity
                opp = Opportunity.model_validate_json(row[0])
                opportunities.append({
                    "id": opp.id,
                    "ticker": opp.ticker,
                    "title": opp.market_data.title,
                    "subtitle": opp.market_data.subtitle,
                    "yes_price": opp.market_data.yes_price,
                    "no_price": opp.market_data.no_price,
                    "volume": opp.market_data.volume,
                    "expiration": opp.market_data.expiration,
                    "timestamp": opp.timestamp.isoformat()
                })

            # Get last 10 executions
            cursor.execute("""
                SELECT payload FROM queue_executions
                WHERE status='QUEUED'
                ORDER BY priority DESC, timestamp ASC
                LIMIT 10
            """)
            for row in cursor.fetchall():
                from core.synapse import ExecutionSignal
                exec_sig = ExecutionSignal.model_validate_json(row[0])
                executions.append({
                    "id": exec_sig.id,
                    "ticker": exec_sig.target_opportunity.ticker,
                    "title": exec_sig.target_opportunity.market_data.title,
                    "subtitle": exec_sig.target_opportunity.market_data.subtitle,
                    "action": exec_sig.action,
                    "side": exec_sig.side,
                    "confidence": exec_sig.confidence,
                    "suggested_count": exec_sig.suggested_count,
                    "reasoning": exec_sig.reasoning[:100] + "..." if len(exec_sig.reasoning) > 100 else exec_sig.reasoning,
                    "timestamp": exec_sig.target_opportunity.timestamp.isoformat()
                })
        finally:
            conn.close()

        return web.json_response({
            "opportunities": {
                "size": opp_size,
                "items": opportunities
            },
            "executions": {
                "size": exec_size,
                "items": executions
            },
            "flow_control": {
                "execution_queue_at_limit": exec_size >= MAX_EXECUTION_QUEUE_SIZE,
                "limit": MAX_EXECUTION_QUEUE_SIZE
            }
        })
    return handler


def get_env_health(engine):
    async def handler(request):
        """Verify 'Stay Alive' environment integrity."""
        import os

        # 1. Symlink Integrity
        opencode_skills_ok = os.path.islink(".opencode/skills")
        agent_workflows_ok = os.path.islink(".agent/workflows")

        # 2. Project Soul Status
        soul_path = "ai-env/soul/identity.md"
        soul_exists = os.path.exists(soul_path)
        last_snapshot = "No snapshot found."

        if soul_exists:
            try:
                with open(soul_path) as f:
                    lines = f.readlines()
                    # Find the last snapshot (lines starting with **Snapshot**)
                    snapshots = [l for l in lines if l.startswith("**Snapshot**")]
                    if snapshots:
                        last_snapshot = snapshots[-1].replace("**Snapshot**: ", "").strip()
            except Exception as e:
                last_snapshot = f"Error reading soul: {e}"

        return web.json_response({
            "symlinks": {
                "opencode_skills": "OK" if opencode_skills_ok else "BROKEN",
                "agent_workflows": "OK" if agent_workflows_ok else "BROKEN"
            },
            "project_soul": {
                "exists": soul_exists,
                "last_intuition": last_snapshot
            },
            "status": "HEALTHY" if (opencode_skills_ok and agent_workflows_ok and soul_exists) else "DEGRADED"
        })
    return handler


def trigger_ragnarok(engine):
    async def handler(request):
        """Emergency protocol to liquidate all positions and lock the vault."""
        from core.safety import execute_ragnarok

        await execute_ragnarok()
        engine.manual_kill_switch = True
        await engine.bus.publish(
            "SYSTEM_LOG",
            {
                "level": "ERROR",
                "message": "[GHOST] RAGNAROK EXECUTED - All positions liquidated",
                "agent_id": 1,
                "timestamp": datetime.now().isoformat(),
            },
            "GHOST",
        )
        return web.json_response({"status": "ragnarok_executed", "message": "Emergency liquidation complete. Vault locked."})
    return handler


def register_sse_subscriptions(engine):
    """
    Register SSE event subscriptions.

    Args:
        engine: GhostEngine instance
    """
    import asyncio

    async def _broadcast_to_sse(message):
        """Broadcast bus events to all SSE clients."""
        event_type = message.topic
        payload = message.payload

        formatted_event = None

        if event_type == "SYSTEM_LOG":
            formatted_event = format_log_event(payload, engine.cycle_count, AGENT_TO_PHASE)
        elif event_type == "VAULT_UPDATE":
            formatted_event = format_vault_event(payload)
        elif event_type == "SIM_RESULT":
            formatted_event = format_simulation_event(payload)
        elif event_type == "SYSTEM_STATE":
            formatted_event = format_state_event(payload)
        elif event_type == "SYSTEM_ERROR":
            formatted_event = format_error_event(payload, engine.cycle_count, AGENT_TO_PHASE, AGENT_NAME_TO_ID)

        if formatted_event:
            # Use list() to create a snapshot since we might modify during iteration
            for queue in list(engine.sse_clients):
                try:
                    await queue.put(formatted_event)
                except Exception:
                    # Client disconnected, remove from set
                    engine.sse_clients.discard(queue)

    # Subscribe to bus events for SSE broadcast
    asyncio.create_task(engine.bus.subscribe("SYSTEM_LOG", _broadcast_to_sse))
    asyncio.create_task(engine.bus.subscribe("VAULT_UPDATE", _broadcast_to_sse))
    asyncio.create_task(engine.bus.subscribe("SIM_RESULT", _broadcast_to_sse))
    asyncio.create_task(engine.bus.subscribe("SYSTEM_STATE", _broadcast_to_sse))
    asyncio.create_task(engine.bus.subscribe("SYSTEM_ERROR", _broadcast_to_sse))
