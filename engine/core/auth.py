"""
Authentication module for Ghost Engine HTTP API.
Implements API key-based authentication for all trading endpoints.
"""

import os
from functools import wraps

from aiohttp import web
from core.http_utils import (
    auth_response,
    error_response,
    success_response,
    unauthorized_response,
)
from core.display import log_info, log_error, log_success, AgentType

# API Path Constants
_DIRECT_PATHS = {
    "/health", "/auth", "/pnl", "/pnl/heatmap", "/stream",
    "/trigger", "/cancel", "/kill-switch", "/deactivate-kill-switch",
    "/reset", "/autopilot/start", "/autopilot/stop", "/autopilot/status",
    "/synapse/queues",
}
_API_PREFIX = "/api"

# Auth status constants
MODE_PRODUCTION = "production"


class AuthManager:
    """Manages API authentication for the Ghost Engine."""

    # Production password for authentication (loaded from environment)
    AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "993728")

    def __init__(self):
        # Load API key from environment
        self.api_key = os.getenv("GHOST_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GHOST_API_KEY not configured. Set GHOST_API_KEY in environment variables. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
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
        """Check if a path is public (no auth required)."""
        return path in self.public_paths

    def validate_api_key(self, request: web.Request) -> bool:
        """Validate the API key from the request."""
        # Check header first
        api_key = request.headers.get("Authorization", "").replace("Bearer ", "")

        # Fall back to query param for SSE (headers not always available)
        if not api_key:
            api_key = request.query.get("api_key", "")

        return api_key == self.api_key

    async def middleware(self, app, handler):
        """aiohttp middleware for authentication."""
        async def middleware_handler(request):
            # Skip auth for public paths
            if self.is_public_path(request.path):
                return await handler(request)

            # Validate API key
            if not self.validate_api_key(request):
                return unauthorized_response()

            return await handler(request)

        return middleware_handler

    def require_auth(self, handler):
        """Decorator to require authentication on a specific handler."""
        @wraps(handler)
        async def wrapper(request):
            if not self.validate_api_key(request):
                return unauthorized_response()
            return await handler(request)
        return wrapper


# Global auth manager instance
auth_manager = AuthManager()


async def login_handler(request: web.Request) -> web.Response:
    """
    Handle login requests.

    Expected JSON body:
    {
        "password": "993728"
    }

    Note: Demo mode has been removed for production security.
    """
    try:
        data = await request.json()
        password = data.get("password", "")

        # Password is required for all access
        if not password:
            return error_response(
                "Password required",
                "Empty password not allowed. Demo mode has been removed.",
                401
            )

        # Validate password for production mode
        if password != AuthManager.AUTH_PASSWORD:
            return error_response("Invalid password", "Authentication failed", 401)

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
        auth_manager.authenticated,
        auth_manager.mode,
        auth_manager.is_production,
        "Authenticated"
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
