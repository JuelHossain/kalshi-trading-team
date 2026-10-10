"""
Authentication module for Ghost Engine HTTP API.
Implements API key-based authentication for all trading endpoints.
"""

import os
import secrets

from aiohttp import web
from core.display import AgentType, log_error, log_success
from core.http_utils import (
    auth_response,
    error_response,
    success_response,
    unauthorized_response,
)
from core.lazy import lazy

# API Path Constants
_DIRECT_PATHS = {
    "/health",
    "/auth",
    "/pnl",
    "/pnl/heatmap",
    "/stream",
    "/trigger",
    "/cancel",
    "/kill-switch",
    "/deactivate-kill-switch",
    "/reset",
    "/autopilot/start",
    "/autopilot/stop",
    "/autopilot/status",
    "/synapse/queues",
    "/orders",
    "/config",
    "/engine/restart",
    "/journal",
    "/decisions",
}
_API_PREFIX = "/api"

# The built cockpit, served by http_api.server.register_frontend.
_STATIC_PUBLIC_PATHS = {"/", "/index.html"}
_STATIC_PUBLIC_PREFIX = "/assets/"

# Auth status constants
MODE_PRODUCTION = "production"


class AuthManager:
    """Manages API authentication for the Ghost Engine."""

    def __init__(self):
        # Load API key from environment
        self.api_key = os.getenv("GHOST_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GHOST_API_KEY not configured. Set GHOST_API_KEY in environment variables. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )

        # No default. A password written into the source is published with it:
        # readable in the repository, in git history, and in any built bundle.
        self.auth_password = os.getenv("AUTH_PASSWORD")
        if not self.auth_password:
            raise ValueError(
                "AUTH_PASSWORD not configured. Set AUTH_PASSWORD in environment variables. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(16))'"
            )

        # Session state
        self.authenticated = False
        self.is_production = False
        self.mode = MODE_PRODUCTION

        # Build public paths set (direct + proxied)
        self.public_paths = _DIRECT_PATHS | {_API_PREFIX + p for p in _DIRECT_PATHS}
        self.public_paths.add("/api/auth/login")
        self.public_paths.add("/api/auth/verify")
        self.public_paths.add("/api/auth/logout")

    def is_public_path(self, path: str) -> bool:
        """Check if a path is public (no auth required).

        Whitelist only. Besides the explicit route list, the cockpit's own
        static files are public: the page and its hashed bundles contain
        no secrets, and the password gate lives inside the app. Nothing
        else is opened.
        """
        if path in self.public_paths:
            return True
        return path in _STATIC_PUBLIC_PATHS or path.startswith(_STATIC_PUBLIC_PREFIX)

    def validate_api_key(self, request: web.Request) -> bool:
        """Validate the Bearer key from the Authorization header.

        Header only: a key in the query string (the old ?api_key= fallback)
        ends up in logs, browser history and Referer headers, and nothing
        uses it -- the cockpit's EventSource is same-origin. Compared in
        constant time, like the password.
        """
        supplied = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        expected = self.api_key or ""
        return bool(supplied) and secrets.compare_digest(supplied.encode(), expected.encode())

    async def middleware(self, app, handler):
        """aiohttp middleware for authentication."""

        async def middleware_handler(request):
            """Refuse cross-site writes; let public paths through; API key elsewhere."""
            # Cross-site request forgery. A page on any other site can make the
            # operator's browser POST here with a "simple" body (text/plain or
            # a form) and no CORS preflight, and aiohttp's request.json() parses
            # it regardless of Content-Type. The audit reproduced that turning
            # off paper trading and zeroing the hard floor through /config.
            # A browser always sends Origin on such a POST, and cannot send
            # application/json cross-site without a preflight that the CORS
            # allow-list refuses. The cockpit sends JSON on every write; clients
            # with no Origin (curl, the systemd hook) are not browsers.
            if request.method not in ("GET", "HEAD", "OPTIONS") and request.headers.get("Origin"):
                content_type = request.headers.get("Content-Type", "").lower()
                if not content_type.startswith("application/json"):
                    return web.json_response(
                        {
                            "error": "Forbidden",
                            "message": "Browser writes must be application/json.",
                        },
                        status=403,
                    )

            # Skip auth for public paths
            if self.is_public_path(request.path):
                return await handler(request)

            # Validate API key
            if not self.validate_api_key(request):
                return unauthorized_response()

            return await handler(request)

        return middleware_handler


# Global auth manager instance
auth_manager = lazy(AuthManager)


# Failed logins per client, for the rate limit below: {client: [monotonic times]}.
_LOGIN_FAILURES: dict[str, list[float]] = {}
_LOGIN_WINDOW_SECONDS = 15 * 60
_LOGIN_MAX_FAILURES = 5


def _login_client(request: web.Request) -> str:
    """Who is logging in: the forwarded client behind a local proxy, else the peer."""
    remote = request.remote or ""
    if remote in ("127.0.0.1", "::1"):
        forwarded = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if forwarded:
            return forwarded
    return remote


def _recent_failures(client: str, now: float) -> list[float]:
    kept = [t for t in _LOGIN_FAILURES.get(client, []) if now - t < _LOGIN_WINDOW_SECONDS]
    _LOGIN_FAILURES[client] = kept
    return kept


async def login_handler(request: web.Request) -> web.Response:
    """
    Handle login requests.

    Expected JSON body:
    {
        "password": "<the value of AUTH_PASSWORD>"
    }

    Note: Demo mode has been removed for production security.
    """
    import asyncio
    import time

    try:
        data = await request.json()
        password = data.get("password", "") if isinstance(data, dict) else None
        if not isinstance(password, str):
            return error_response("Bad request", "password must be a string", 400)

        # Password is required for all access
        if not password:
            return error_response(
                "Password required", "Empty password not allowed. Demo mode has been removed.", 401
            )

        # A per-client limit on failures, checked before comparing. There was
        # none, so the password could be guessed as fast as the network
        # allowed. Per client, not global: a global cap would let anyone lock
        # the operator out.
        client = _login_client(request)
        now = time.monotonic()
        failures = _recent_failures(client, now)
        if len(failures) >= _LOGIN_MAX_FAILURES:
            retry = int(_LOGIN_WINDOW_SECONDS - (now - failures[0])) + 1
            response = error_response("Too many attempts", f"Try again in {retry}s", 429)
            response.headers["Retry-After"] = str(retry)
            return response

        # Constant-time compare so response timing cannot leak the password.
        if not secrets.compare_digest(
            password.encode(), (auth_manager.auth_password or "").encode()
        ):
            failures.append(now)
            await asyncio.sleep(0.5)
            return error_response("Invalid password", "Authentication failed", 401)
        _LOGIN_FAILURES.pop(client, None)

        # Update session state
        auth_manager.authenticated = True
        auth_manager.mode = MODE_PRODUCTION
        auth_manager.is_production = True

        log_success(f"Login successful - Mode: {MODE_PRODUCTION}", AgentType.GATEWAY)
        return auth_response(True, MODE_PRODUCTION, True, f"Logged in to {MODE_PRODUCTION} mode")

    except Exception as e:
        log_error(f"Login error: {e}", AgentType.GATEWAY)
        return error_response("Login failed", str(e))


async def verify_handler(request: web.Request) -> web.Response:
    """
    Verify authentication status.
    Returns current session state.
    """
    if not auth_manager.authenticated:
        return auth_response(False, MODE_PRODUCTION, False, "Not authenticated")

    return auth_response(
        auth_manager.authenticated, auth_manager.mode, auth_manager.is_production, "Authenticated"
    )


async def logout_handler(request: web.Request) -> web.Response:
    """
    Handle logout requests.
    Clears session state.
    """
    auth_manager.authenticated = False
    auth_manager.is_production = False
    auth_manager.mode = MODE_PRODUCTION

    log_success("Logout successful", AgentType.GATEWAY)
    return success_response("Logged out successfully")
