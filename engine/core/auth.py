"""
Authentication module for Ghost Engine HTTP API.
Implements API key-based authentication for all trading endpoints.
"""

import os
from functools import wraps
from aiohttp import web


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
        self.mode = "demo"  # 'demo' or 'production'

        # List of paths that don't require authentication
        # In 2-tier local architecture, these endpoints are trusted
        # Note: Vite proxy now preserves /api prefix
        self.public_paths = {
            # Direct access (port 3002)
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
            # Proxied access (port 3000 via Vite)
            "/api/health",
            "/api/auth",
            "/api/auth/login",
            "/api/auth/verify",
            "/api/auth/logout",
            "/api/pnl",
            "/api/pnl/heatmap",
            "/api/stream",
            "/api/trigger",
            "/api/cancel",
            "/api/kill-switch",
            "/api/deactivate-kill-switch",
            "/api/reset",
            "/api/autopilot/start",
            "/api/autopilot/stop",
            "/api/autopilot/status",
        }

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
                return web.json_response(
                    {"error": "Unauthorized", "message": "Valid API key required"},
                    status=401
                )

            return await handler(request)

        return middleware_handler

    def require_auth(self, handler):
        """Decorator to require authentication on a specific handler."""
        @wraps(handler)
        async def wrapper(request):
            if not self.validate_api_key(request):
                return web.json_response(
                    {"error": "Unauthorized", "message": "Valid API key required"},
                    status=401
                )
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
        mode = data.get("mode", "demo")

        # Empty password = demo mode
        if not password:
            auth_manager.authenticated = True
            auth_manager.mode = "demo"
            auth_manager.is_production = False
            print(f"[AUTH] Demo mode login successful")
            return web.json_response({
                "isAuthenticated": True,
                "mode": "demo",
                "is_production": False,
                "message": "Logged in to demo mode"
            })

        # Validate password for production mode
        if password != AuthManager.AUTH_PASSWORD:
            return web.json_response(
                {"error": "Invalid password", "message": "Authentication failed"},
                status=401
            )

        # Update session state
        auth_manager.authenticated = True
        auth_manager.mode = mode
        auth_manager.is_production = (mode == "production")

        print(f"[AUTH] Login successful - Mode: {mode}")

        return web.json_response({
            "isAuthenticated": True,
            "mode": mode,
            "is_production": auth_manager.is_production,
            "message": f"Logged in to {mode} mode"
        })

    except Exception as e:
        print(f"[AUTH] Login error: {e}")
        return web.json_response(
            {"error": "Login failed", "message": str(e)},
            status=500
        )


async def verify_handler(request: web.Request) -> web.Response:
    """
    Verify authentication status.
    Returns current session state.
    """
    return web.json_response({
        "isAuthenticated": auth_manager.authenticated,
        "mode": auth_manager.mode,
        "is_production": auth_manager.is_production
    })


async def logout_handler(request: web.Request) -> web.Response:
    """
    Handle logout requests.
    Clears session state.
    """
    auth_manager.authenticated = False
    auth_manager.is_production = False
    auth_manager.mode = "demo"

    print("[AUTH] Logout successful")

    return web.json_response({
        "success": True,
        "message": "Logged out successfully"
    })
