"""
HTTP response builders for Ghost Engine.
Provides standardized response formatting across all HTTP endpoints.
"""

from aiohttp import web


# ==============================================================================
# RESPONSE BUILDERS
# ==============================================================================

def json_response(data: dict, status: int = 200) -> web.Response:
    """Create a standardized JSON response."""
    return web.json_response(data, status=status)


def error_response(error: str, message: str, status: int = 500) -> web.Response:
    """Create a standardized error response."""
    return web.json_response(
        {"error": error, "message": message},
        status=status
    )


def unauthorized_response(message: str = "Valid API key required") -> web.Response:
    """Create a standardized unauthorized response."""
    return web.json_response(
        {"error": "Unauthorized", "message": message},
        status=401
    )


def success_response(message: str, **kwargs) -> web.Response:
    """Create a standardized success response."""
    return web.json_response({
        "success": True,
        "message": message,
        **kwargs
    })


def auth_response(is_authenticated: bool, mode: str, is_production: bool, message: str = "") -> web.Response:
    """Create a standardized authentication response."""
    return web.json_response({
        "isAuthenticated": is_authenticated,
        "mode": mode,
        "is_production": is_production,
        "message": message
    })
