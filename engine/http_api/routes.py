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
from core.shared_utils import fire_and_forget


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

    # Ledger and configuration routes
    app.router.add_get("/orders", get_orders(engine))
    app.router.add_get("/api/orders", get_orders(engine))
    app.router.add_get("/config", get_config(engine))
    app.router.add_get("/api/config", get_config(engine))
    app.router.add_post("/config", update_config(engine))
    app.router.add_post("/api/config", update_config(engine))
    app.router.add_post("/engine/restart", restart_engine(engine))
    app.router.add_post("/api/engine/restart", restart_engine(engine))
    app.router.add_get("/journal", get_journal(engine))
    app.router.add_get("/api/journal", get_journal(engine))
    app.router.add_get("/decisions", get_decisions(engine))
    app.router.add_get("/api/decisions", get_decisions(engine))

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
    """POST /trigger: start one cycle. Body {"isPaperTrading": bool}."""

    async def handler(request):
        """Schedule the cycle and answer immediately with its id."""
        data = await request.json()
        is_paper = data.get("isPaperTrading", True)
        fire_and_forget(engine.execute_single_cycle(is_paper))
        return web.json_response(
            {
                "status": "triggered",
                "cycleId": engine.cycle_count + 1,
                "isProcessing": engine.is_processing,
            }
        )

    return handler


def activate_kill_switch(engine):
    """POST /kill-switch: halt authorisation of every cycle until deactivated."""

    async def handler(request):
        """Set the manual kill switch and log it at ERROR so it is impossible to miss."""
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
    """POST /deactivate-kill-switch: lift the manual kill switch."""

    async def handler(request):
        """Clear the manual kill switch and log it."""
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
        return web.json_response({"status": "active", "message": "Manual Kill Switch Deactivated."})

    return handler


def reset_system(engine):
    """POST /reset: return the engine to a runnable state without stopping it."""

    async def handler(request):
        """Return the engine to a state where a cycle can be authorised.

        This used to set engine.running = False, which is the condition of
        the main loop -- so the endpoint named "reset" terminated the engine
        instead of resetting it. Shutting down is what /kill-switch is for.

        It also has to drain the error box: authorize_cycle halts while that
        box is non-empty and nothing else empties it, so one recoverable
        error latched the engine off until someone deleted rows from SQLite
        by hand. The opportunity and execution queues are deliberately left
        alone -- acknowledging an error must not discard pending work.
        """
        engine.manual_kill_switch = False
        engine.is_processing = False

        errors_cleared = 0
        if getattr(engine, "synapse", None):
            errors_cleared = await engine.synapse.drain_errors()

        # A failed pre-flight latches this separately, and it halts cycles too.
        soul = getattr(engine, "soul", None)
        if soul is not None:
            soul.is_locked_down = False

        return web.json_response(
            {
                "status": "reset",
                "errors_cleared": errors_cleared,
                "running": engine.running,
            }
        )

    return handler


def cancel_cycle(engine):
    """POST /cancel: stop the running cycle, stop autopilot, release vault reservations."""

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

        return web.json_response(
            {"status": "cancelled", "message": "Cycle cancelled and Autopilot disabled."}
        )

    return handler


def health_check(engine):
    """GET /health: process liveness, agent count, cycle number, balance."""

    async def handler(request):
        """Answer from in-memory state; never touches Kalshi.

        Also says whether a cycle *could* run right now and why not: the
        error box, the kill switches and a Soul lockdown each halt
        authorisation silently otherwise, and the dashboard would show a
        healthy engine that never trades.
        """
        synapse = getattr(engine, "synapse", None)
        error_count = await synapse.errors.size() if synapse else 0
        soul = getattr(engine, "soul", None)
        halted: list[str] = []
        if engine.manual_kill_switch:
            halted.append("manual kill switch")
        if engine.vault.kill_switch_active:
            halted.append("vault kill switch")
        if soul is not None and soul.is_locked_down:
            halted.append("soul lockdown")
        if error_count:
            halted.append(f"error box holds {error_count}")
        return web.json_response(
            {
                "status": "healthy",
                "agents": len(engine.agents) or 4,
                "cycle": engine.cycle_count,
                "balance": engine.vault.current_balance / 100,
                "processing": engine.is_processing,
                "error_box": error_count,
                "kill_switch": engine.manual_kill_switch or engine.vault.kill_switch_active,
                "locked_down": bool(soul is not None and soul.is_locked_down),
                "halted": halted,
            }
        )

    return handler


def start_autopilot(engine):
    """POST /autopilot/start: let Soul start a new cycle after each completes."""

    async def handler(request):
        """Enable autonomous cycle looping."""
        data = await request.json()
        is_paper = data.get("isPaperTrading", True)
        await engine.bus.publish(
            "SYSTEM_CONTROL", {"action": "START_AUTOPILOT", "isPaperTrading": is_paper}, "HTTP"
        )
        return web.json_response({"status": "autopilot_started", "mode": "AUTOPILOT"})

    return handler


def stop_autopilot(engine):
    """POST /autopilot/stop: finish the current cycle, then stop."""

    async def handler(request):
        """Disable autonomous cycle looping (Graceful Pause)."""
        await engine.bus.publish("SYSTEM_CONTROL", {"action": "STOP_AUTOPILOT"}, "HTTP")
        return web.json_response({"status": "autopilot_stopped", "mode": "MANUAL"})

    return handler


def autopilot_status(engine):
    """GET /autopilot/status: whether autopilot is on."""

    async def handler(request):
        """Get current autopilot status."""
        return web.json_response(
            {
                "autopilot_enabled": (
                    engine.soul.autopilot_enabled if hasattr(engine, "soul") else False
                ),
                "is_paper_trading": (
                    engine.soul.is_paper_trading if hasattr(engine, "soul") else True
                ),
                "is_locked_down": engine.soul.is_locked_down if hasattr(engine, "soul") else False,
                "is_processing": engine.is_processing,
                "cycle_count": engine.cycle_count,
            }
        )

    return handler


def stream_logs(engine):
    """GET /stream: server-sent events (LOG, VAULT, SIMULATION, STATE, ERROR)."""

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
    """POST /auth: the original dashboard's login check; see core.auth for the real flow."""

    async def handler(request):
        """Handle authentication check."""
        from core.auth import auth_manager

        # Return actual session data from auth_manager
        # In 2-tier architecture, we check the auth_manager session state
        if auth_manager.authenticated:
            return web.json_response(
                {
                    "isAuthenticated": True,
                    "user": {
                        "id": "user_1",
                        "email": (
                            "trader@sentient-alpha.com"
                            if auth_manager.is_production
                            else "demo@kalshi.com"
                        ),
                        "name": "Sentient Trader" if auth_manager.is_production else "Demo Trader",
                    },
                    "mode": auth_manager.mode,
                    "is_production": auth_manager.is_production,
                }
            )
        return web.json_response(
            {"isAuthenticated": False, "user": None, "mode": "demo", "is_production": False}
        )

    return handler


def get_pnl(engine):
    """GET /pnl: balance history for the dashboard chart."""

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
            history.append({"timestamp": datetime.fromtimestamp(ts).isoformat(), "balance": val})

        return web.json_response(
            {"currentBalance": current_balance, "history": history[::-1]}  # Oldest first
        )

    return handler


def get_pnl_heatmap(engine):
    """GET /pnl/heatmap: daily P&L for the dashboard heatmap."""

    async def handler(request):
        """Get daily PnL heatmap."""
        # Mock data for heatmap
        heatmap = []
        import random

        today = datetime.now()
        for i in range(30):  # Last 30 days
            date = today.timestamp() - (i * 86400)
            heatmap.append(
                {
                    "date": datetime.fromtimestamp(date).strftime("%Y-%m-%d"),
                    "pnl": random.uniform(-50, 100),
                    "count": random.randint(1, 10),
                }
            )
        return web.json_response({"heatmap": heatmap})

    return handler


def get_synapse_queues(engine):
    """GET /synapse/queues: sizes of the opportunity, execution and error queues."""

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
                opportunities.append(
                    {
                        "id": opp.id,
                        "ticker": opp.ticker,
                        "title": opp.market_data.title,
                        "subtitle": opp.market_data.subtitle,
                        "yes_price": opp.market_data.yes_price,
                        "no_price": opp.market_data.no_price,
                        "volume": opp.market_data.volume,
                        "expiration": opp.market_data.expiration,
                        "timestamp": opp.timestamp.isoformat(),
                    }
                )

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
                executions.append(
                    {
                        "id": exec_sig.id,
                        "ticker": exec_sig.target_opportunity.ticker,
                        "title": exec_sig.target_opportunity.market_data.title,
                        "subtitle": exec_sig.target_opportunity.market_data.subtitle,
                        "action": exec_sig.action,
                        "side": exec_sig.side,
                        "confidence": exec_sig.confidence,
                        "suggested_count": exec_sig.suggested_count,
                        "reasoning": (
                            exec_sig.reasoning[:100] + "..."
                            if len(exec_sig.reasoning) > 100
                            else exec_sig.reasoning
                        ),
                        "timestamp": exec_sig.target_opportunity.timestamp.isoformat(),
                    }
                )
        finally:
            conn.close()

        return web.json_response(
            {
                "opportunities": {"size": opp_size, "items": opportunities},
                "executions": {"size": exec_size, "items": executions},
                "flow_control": {
                    "execution_queue_at_limit": exec_size >= MAX_EXECUTION_QUEUE_SIZE,
                    "limit": MAX_EXECUTION_QUEUE_SIZE,
                },
            }
        )

    return handler


def engine_config(engine) -> dict:
    """The engine's effective limits and settings, for the dashboard.

    Read at request time so environment overrides (BRAIN_MIN_EDGE and the
    like) are reported as they actually apply, not as the defaults.
    """
    import os

    from agents.senses import scanner
    from core import constants, trading_mode
    from core.shared_utils import get_env_bool

    vault = engine.vault
    brain = getattr(engine, "brain", None)
    return {
        "paper_pinned": get_env_bool("IS_PAPER_TRADING", default=False),
        "live_armed": trading_mode.is_live(),
        "kalshi_env": os.getenv("KALSHI_ENV", "demo"),
        "brain": {
            "model": getattr(brain, "gemini_model", None) or os.getenv("GEMINI_MODEL"),
            "min_edge": constants.BRAIN_MIN_EDGE,
            "confidence_threshold": constants.BRAIN_CONFIDENCE_THRESHOLD,
            "estimate_samples": constants.BRAIN_ESTIMATE_SAMPLES,
            "max_disagreement": constants.BRAIN_MAX_DISAGREEMENT,
            "stale_opportunity_seconds": constants.BRAIN_STALE_OPPORTUNITY_SECONDS,
            "search_grounding": os.getenv("BRAIN_SEARCH_GROUNDING", "true").strip().lower()
            not in ("false", "0", "no"),
        },
        "senses": {
            "min_volume": scanner.MIN_VOLUME,
            "max_spread_cents": scanner.MAX_SPREAD_CENTS,
            "max_days_to_close": scanner.MAX_DAYS_TO_CLOSE,
            "stock_buffer_size": constants.SENSES_STOCK_BUFFER_SIZE,
            "queue_batch_size": constants.SENSES_QUEUE_BATCH_SIZE,
        },
        "hand": {
            "max_stake_cents": constants.HAND_MAX_STAKE_CENTS,
            "kelly_fraction": constants.HAND_KELLY_FRACTION,
            "stop_loss_pct": constants.HAND_STOP_LOSS_PCT,
            "take_profit_pct": constants.HAND_TAKE_PROFIT_PCT,
            "exit_before_expiry_hours": constants.HAND_EXIT_BEFORE_EXPIRY_HOURS,
        },
        "vault": {
            "principal_cents": vault.PRINCIPAL_CAPITAL_CENTS,
            "hard_floor_cents": vault.HARD_FLOOR_CENTS,
            "kill_switch_pct": vault.KILL_SWITCH_THRESHOLD_PCT,
            "profit_lock_cents": vault.DAILY_PROFIT_THRESHOLD_CENTS,
            "is_locked": vault.is_locked,
            "kill_switch_active": vault.kill_switch_active,
        },
        "queues": {
            "max_execution": constants.MAX_EXECUTION_QUEUE_SIZE,
            "max_opportunity": constants.MAX_OPPORTUNITY_QUEUE_SIZE,
        },
        "min_cycle_interval_seconds": constants.MIN_CYCLE_INTERVAL_SECONDS,
    }


def _session_required(request) -> web.Response | None:
    """Writes to the engine need a signed-in dashboard session or the API key.

    Returns a 401 response to send, or None when the caller may proceed.
    """
    from core.auth import auth_manager

    bearer = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    if bearer and secrets_equal(bearer, auth_manager.api_key or ""):
        return None
    if auth_manager.authenticated:
        return None
    return web.json_response(
        {"error": "Unauthorized", "message": "Sign in to the dashboard or send the API key."},
        status=401,
    )


def secrets_equal(a: str, b: str) -> bool:
    import secrets as _secrets

    return bool(a) and bool(b) and _secrets.compare_digest(a, b)


def get_config(engine):
    """GET /config: the settings registry (secrets masked) plus the runtime summary."""

    async def handler(request):
        """Answer from the registry, constants and the vault; never touches Kalshi."""
        from core.settings import settings

        body = settings.describe()
        body["runtime"] = engine_config(engine)
        return web.json_response(body)

    return handler


def update_config(engine):
    """POST /config: change settings. Body `{"changes": {"KEY": value, ...}}`.

    Values are validated as a batch, persisted to the engine's .env, applied
    live where the reader can be patched, and reported back with any keys
    that need a restart to take effect. Requires a signed-in session.
    """

    async def handler(request):
        """Validate, persist, apply; answer with the update report and the new state."""
        denied = _session_required(request)
        if denied is not None:
            return denied
        from core.settings import settings

        try:
            data = await request.json()
        except Exception:
            return web.json_response(
                {"error": "Bad request", "message": "JSON body required"}, status=400
            )
        changes = data.get("changes") if isinstance(data, dict) else None
        if not isinstance(changes, dict) or not changes:
            return web.json_response(
                {"error": "Bad request", "message": 'Body must be {"changes": {KEY: value}}'},
                status=400,
            )
        report = settings.update(changes)
        status = (
            400 if report.errors and not report.applied and not report.restart_required else 200
        )
        await engine.bus.publish(
            "SYSTEM_LOG",
            {
                "level": "WARN" if report.errors else "INFO",
                "message": (
                    f"[GHOST] Settings changed: {', '.join(sorted(changes))}"
                    + (
                        f" · restart needed for {', '.join(report.restart_required)}"
                        if report.restart_required
                        else ""
                    )
                    + (f" · rejected {', '.join(report.errors)}" if report.errors else "")
                ),
                "agent_id": 1,
                "timestamp": datetime.now().isoformat(),
            },
            "GHOST",
        )
        body = report.as_dict()
        body["config"] = settings.describe()
        body["config"]["runtime"] = engine_config(engine)
        return web.json_response(body, status=status)

    return handler


def restart_engine(engine):
    """POST /engine/restart: re-exec the process so restart-only settings take effect."""

    async def handler(request):
        """Answer first, then replace the process a moment later."""
        denied = _session_required(request)
        if denied is not None:
            return denied
        import os
        import sys

        async def _restart():
            await asyncio.sleep(0.8)
            try:
                await engine.shutdown("Restart requested from the dashboard")
            finally:
                os.execv(sys.executable, [sys.executable, *sys.argv])

        fire_and_forget(_restart())
        return web.json_response(
            {
                "status": "restarting",
                "message": "The engine is restarting; reconnect in a few seconds.",
            }
        )

    return handler


def get_journal(engine):
    """GET /journal: the durable event log. Filters: agent, topic, cycle, level, since_id, limit."""

    async def handler(request):
        """Read from the journal; `since_id` pages forward, otherwise newest first."""
        journal = getattr(engine, "journal", None)
        if journal is None:
            return web.json_response({"events": [], "count": 0})
        q = request.query

        def _int(name):
            try:
                return int(q[name]) if name in q else None
            except ValueError:
                return None

        events = journal.query(
            limit=_int("limit") or 200,
            agent=q.get("agent"),
            topic=q.get("topic"),
            cycle=_int("cycle"),
            since_id=_int("since_id"),
            level=q.get("level"),
        )
        return web.json_response({"events": events, "count": journal.count()})

    return handler


def get_decisions(engine):
    """GET /decisions: every Brain judgement from the ledger, newest first."""

    async def handler(request):
        """Read the ledger; `limit` and `ticker` filter."""
        from core.ledger import recent_decisions

        try:
            limit = max(1, min(2000, int(request.query.get("limit", "200"))))
        except ValueError:
            limit = 200
        return web.json_response(
            {"decisions": recent_decisions(limit, request.query.get("ticker"))}
        )

    return handler


def get_orders(engine):
    """GET /orders: executed orders from the decision ledger, newest first."""

    async def handler(request):
        """Read the ledger; `limit` query param caps the rows (default 200)."""
        from core.ledger import recent_fills

        try:
            limit = max(1, min(1000, int(request.query.get("limit", "200"))))
        except ValueError:
            limit = 200
        return web.json_response({"orders": recent_fills(limit)})

    return handler


def get_env_health(engine):
    """GET /env-health: which optional services are configured and reachable."""

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
                    snapshots = [ln for ln in lines if ln.startswith("**Snapshot**")]
                    if snapshots:
                        last_snapshot = snapshots[-1].replace("**Snapshot**: ", "").strip()
            except Exception as e:
                last_snapshot = f"Error reading soul: {e}"

        return web.json_response(
            {
                "symlinks": {
                    "opencode_skills": "OK" if opencode_skills_ok else "BROKEN",
                    "agent_workflows": "OK" if agent_workflows_ok else "BROKEN",
                },
                "project_soul": {"exists": soul_exists, "last_intuition": last_snapshot},
                "status": (
                    "HEALTHY"
                    if (opencode_skills_ok and agent_workflows_ok and soul_exists)
                    else "DEGRADED"
                ),
            }
        )

    return handler


def trigger_ragnarok(engine):
    """POST /ragnarok: cancel every open order and flatten every position."""

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
        return web.json_response(
            {
                "status": "ragnarok_executed",
                "message": "Emergency liquidation complete. Vault locked.",
            }
        )

    return handler


def register_sse_subscriptions(engine):
    """
    Register SSE event subscriptions.

    Args:
        engine: GhostEngine instance
    """

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
            formatted_event = format_error_event(
                payload, engine.cycle_count, AGENT_TO_PHASE, AGENT_NAME_TO_ID
            )

        if formatted_event:
            # Use list() to create a snapshot since we might modify during iteration
            for queue in list(engine.sse_clients):
                try:
                    await queue.put(formatted_event)
                except Exception:
                    # Client disconnected, remove from set
                    engine.sse_clients.discard(queue)

    # Subscribe to bus events for SSE broadcast
    fire_and_forget(engine.bus.subscribe("SYSTEM_LOG", _broadcast_to_sse))
    fire_and_forget(engine.bus.subscribe("VAULT_UPDATE", _broadcast_to_sse))
    fire_and_forget(engine.bus.subscribe("SIM_RESULT", _broadcast_to_sse))
    fire_and_forget(engine.bus.subscribe("SYSTEM_STATE", _broadcast_to_sse))
    fire_and_forget(engine.bus.subscribe("SYSTEM_ERROR", _broadcast_to_sse))
