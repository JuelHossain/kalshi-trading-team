"""The engine serves the built cockpit itself, so deployment is one process.

The page and its bundles must be public; everything else keeps the
whitelist auth exactly as before, and the API keeps its own 404s.
"""

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from core.auth import auth_manager
from http_api.server import register_frontend, setup_middlewares


@pytest.fixture
def dist(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html><body>cockpit</body></html>", encoding="utf-8")
    (tmp_path / "assets" / "index-abc.js").write_text("console.log(1)", encoding="utf-8")
    return tmp_path


async def _client(app):
    client = TestClient(TestServer(app))
    await client.start_server()
    return client


def _app(dist):
    app = web.Application()
    setup_middlewares(app, auth_manager)
    app.router.add_get("/api/health", lambda r: web.json_response({"ok": True}))
    register_frontend(app, dist)
    return app


class TestServingTheBuild:
    @pytest.mark.asyncio
    async def test_page_and_bundles_are_served_without_auth(self, dist):
        client = await _client(_app(dist))
        try:
            for path in ("/", "/index.html"):
                resp = await client.get(path)
                assert resp.status == 200, path
                assert "cockpit" in await resp.text()
                assert resp.headers["Cache-Control"] == "no-cache"
            assert (await client.get("/assets/index-abc.js")).status == 200
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_everything_else_keeps_the_old_rules(self, dist):
        client = await _client(_app(dist))
        try:
            assert (await client.get("/api/health")).status == 200
            unknown_api = await client.get("/api/nope")
            assert unknown_api.status in (401, 404)
            assert "cockpit" not in await unknown_api.text()
            # Not on the whitelist: the auth middleware answers, not the page.
            assert (await client.get("/some/route")).status == 401
            assert (await client.get("/ragnarok")).status == 401
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_no_build_means_api_only(self, tmp_path):
        app = web.Application()
        assert register_frontend(app, tmp_path / "nowhere") is False
        client = await _client(app)
        try:
            assert (await client.get("/")).status == 404
        finally:
            await client.close()


class TestPublicPaths:
    def test_only_the_cockpit_files_were_added_to_the_whitelist(self):
        assert auth_manager.is_public_path("/") is True
        assert auth_manager.is_public_path("/index.html") is True
        assert auth_manager.is_public_path("/assets/index-abc.js") is True
        assert auth_manager.is_public_path("/api/config") is True  # explicit list, as before
        assert auth_manager.is_public_path("/api/secret") is False
        assert auth_manager.is_public_path("/settings") is False
        assert auth_manager.is_public_path("/ragnarok") is False
        assert auth_manager.is_public_path("/assets") is False
