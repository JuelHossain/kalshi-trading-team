"""
Authentication module for Ghost Engine HTTP API.
Implements API key-based authentication for all trading endpoints.
"""

import os
from functools import wraps

from aiohttp import web

from core.http_utils import (
    unauthorized_response,
    error_response,
    auth_response,
    success_response,
)


# API Path Constants
_DIRECT_PATHS = {
    "/health", "/auth", "/pnl", "/pnl/heatmap", "/stream",
    "/trigger", "/cancel", "/kill-switch", "/deactivate-kill-switch",
    "/reset", "/autopilot/start", "/autopilot/stop", "/autopilot/status",
    "/synapse/queues",
}
_API_PREFIX = "/api"

# Auth status constants
MODE_DEMO = "demo"
MODE_PRODUCTION = "production"


class AuthManager:
    """Manages API authentication for the Ghost Engine."""

    # Production password for authentication (loaded from environment)
    AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "993728")

    def __init__(self):
        # Load API key from environment
        self.api_key = os.getenv("GHOST_API_KEY")
        if not self.api_key:
            # Generate a random key for development if not set
            import secrets
            self.api_key = secrets.token_urlsafe(32)
            print(f"[AUTH] Warning: GHOST_API_KEY not set. Using generated dev key: {self.api_key}")

        # Session state
        self.authenticated = False
        self.is_production = False
        self.mode = MODE_DEMO

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
        "password": "993728",
        "mode": "demo" | "production"
    }
    """
    try:
        data = await request.json()
        password = data.get("password", "")
        mode = data.get("mode", MODE_DEMO)

        # Empty password = demo mode
        if not password:
            auth_manager.authenticated = True
            auth_manager.mode = MODE_DEMO
            auth_manager.is_production = False
            print("[AUTH] Demo mode login successful")
            return auth_response(True, MODE_DEMO, False, "Logged in to demo mode")

        # Validate password for production mode
        if password != AuthManager.AUTH_PASSWORD:
            return error_response("Invalid password", "Authentication failed", 401)

        # Update session state
        auth_manager.authenticated = True
        auth_manager.mode = mode
        auth_manager.is_production = (mode == MODE_PRODUCTION)

        print(f"[AUTH] Login successful - Mode: {mode}")
        return auth_response(True, mode, auth_manager.is_production, f"Logged in to {mode} mode")

    except Exception as e:
        print(f"[AUTH] Login error: {e}")
        return error_response("Login failed", str(e))


async def verify_handler(request: web.Request) -> web.Response:
    """
    Verify authentication status.
    Returns current session state.
    """
    return auth_response(
        auth_manager.authenticated,
        auth_manager.mode,
        auth_manager.is_production,
        ""
    )


async def logout_handler(request: web.Request) -> web.Response:
    """
    Handle logout requests.
    Clears session state.
    """
    auth_manager.authenticated = False
    auth_manager.is_production = False
    auth_manager.mode = MODE_DEMO

    print("[AUTH] Logout successful")
    return success_response("Logged out successfully")
