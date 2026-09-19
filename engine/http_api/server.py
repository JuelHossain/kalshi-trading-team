"""
HTTP server setup with CORS middleware for Ghost Engine.
"""

import asyncio
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
        """aiohttp middleware factory adding the CORS headers the dashboard needs."""

        async def middleware_handler(request):
            """Answer OPTIONS directly; add CORS headers to every other response."""
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


def register_frontend(app, dist_dir) -> bool:
    """Serve the built cockpit from the engine itself.

    One process, one port: `frontend/dist` (from `npm run build`) is served
    at `/` and `/index.html`, its hashed bundles at `/assets/`. Nothing
    else is exposed: the cockpit keeps its views in memory rather than in
    the URL, so no catch-all route is needed and the auth whitelist stays
    exact. Returns False, and serves nothing, when there is no build --
    the API keeps working exactly as before.
    """
    import os

    from core.logger import get_logger

    dist = os.path.abspath(str(dist_dir))
    index = os.path.join(dist, "index.html")
    assets = os.path.join(dist, "assets")
    if not os.path.isfile(index):
        get_logger("GHOST").info(f"No cockpit build at {dist}; API only.")
        return False

    async def serve_index(request):
        """The page. Never cached, so a rebuild shows up on the next load."""
        return web.FileResponse(index, headers={"Cache-Control": "no-cache"})

    if os.path.isdir(assets):
        app.router.add_static("/assets/", assets, name="cockpit-assets")
    app.router.add_get("/", serve_index)
    app.router.add_get("/index.html", serve_index)
    get_logger("GHOST").info(f"Serving the cockpit from {dist}")
    return True


async def start_server(app, host: str | None = None, port: int = 3002):
    """
    Start the HTTP server on loopback plus any addresses in GHOST_BIND.

    It used to bind 0.0.0.0, and Fedora Workstation's default firewall zone
    opens 1025-65535/tcp, so every public control route was reachable from
    the Wi-Fi LAN and from Docker containers, not only over Tailscale.
    GHOST_BIND is a comma-separated list (e.g. "127.0.0.1,100.x.y.z" for
    loopback plus the Tailscale address); 0.0.0.0 restores the old exposure
    deliberately. Loopback is always included: the engine's own tooling
    talks to it. An address that is not up yet -- tailscale0 can come up
    after the service at boot -- is retried in the background rather than
    failing the start, which under systemd would become a restart loop.
    """
    from core.logger import get_logger
    from core.shared_utils import fire_and_forget

    logger = get_logger("GHOST")
    wanted = host or os.getenv("GHOST_BIND", "127.0.0.1")
    hosts = ["127.0.0.1"] + [h.strip() for h in wanted.split(",") if h.strip()]
    hosts = list(dict.fromkeys(hosts))  # de-duplicate, keep order

    runner = web.AppRunner(app)
    await runner.setup()
    for address in hosts:
        try:
            await web.TCPSite(runner, address, port).start()
            logger.info(f"HTTP Server online at http://{address}:{port}")
        except OSError as e:
            if address == "127.0.0.1":
                raise
            logger.warning(f"Cannot listen on {address}:{port} yet ({e}); retrying.")
            fire_and_forget(_bind_when_available(runner, address, port, logger))
    return runner


async def _bind_when_available(runner, address: str, port: int, logger, every: float = 15.0):
    """Keep trying an address that was not available at start (e.g. Tailscale)."""
    while True:
        await asyncio.sleep(every)
        try:
            await web.TCPSite(runner, address, port).start()
            logger.info(f"HTTP Server online at http://{address}:{port}")
            return
        except OSError:
            continue
