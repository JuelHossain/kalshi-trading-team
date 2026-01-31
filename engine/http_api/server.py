"""
HTTP server setup with CORS middleware for Ghost Engine.
"""
import os
from aiohttp import web


def create_cors_middleware():
    """
    Create CORS middleware that restricts to specific origins.

    Returns:
        CORS middleware function
    """
    # CORS middleware - restrict to specific origins
    ALLOWED_ORIGINS = [
        "http://localhost:3000",  # Dev frontend
        "http://127.0.0.1:3000",
    ]
    # Add production origins from env if set
    prod_origin = os.getenv("FRONTEND_ORIGIN")
    if prod_origin:
        ALLOWED_ORIGINS.append(prod_origin)

    async def cors_middleware(app, handler):
        async def middleware_handler(request):
            # Get origin from request
            origin = request.headers.get("Origin", "")

            # Handle preflight requests
            if request.method == "OPTIONS":
                response = web.Response(status=200)
            else:
                response = await handler(request)

            # Only allow specific origins, not wildcard
            if origin in ALLOWED_ORIGINS:
                response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return response
        return middleware_handler

    return cors_middleware


def setup_middlewares(app, auth_manager):
    """
    Setup all middlewares for the HTTP server.

    Args:
        app: aiohttp Application
        auth_manager: Authentication manager instance
    """
    cors_middleware = create_cors_middleware()

    # Add middlewares: CORS first, then auth
    app.middlewares.append(cors_middleware)
    app.middlewares.append(auth_manager.middleware)


async def start_server(app, host="0.0.0.0", port=3002):
    """
    Start the HTTP server.

    Args:
        app: aiohttp Application
        host: Server host
        port: Server port
    """
    from core.logger import get_logger
    logger = get_logger("GHOST")

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

    logger.info(f"HTTP Server online at http://{host}:{port}")
