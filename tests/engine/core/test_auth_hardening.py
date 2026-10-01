"""Auth hardening from the 2026-09-18 audit (the per-client session is separate)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from core import auth
from core.auth import auth_manager, login_handler


class TestKeyRotation:
    def test_a_rotated_key_is_the_one_accepted(self, monkeypatch):
        """Assignment used to land on the lazy proxy while the real object's
        methods read the old value: the old key kept working, the new one
        was refused."""
        monkeypatch.setattr(auth_manager, "api_key", "old-key")
        auth_manager.api_key = "new-key"  # what the settings applier does

        def req(key):
            r = MagicMock()
            r.headers = {"Authorization": f"Bearer {key}"}
            r.query = {}
            return r

        assert auth_manager.validate_api_key(req("new-key")) is True
        assert auth_manager.validate_api_key(req("old-key")) is False


def _login_request(password, remote="100.64.0.9"):
    request = MagicMock()
    request.json = AsyncMock(return_value={"password": password})
    request.remote = remote
    request.headers = {}
    return request


class TestLoginLimit:
    @pytest.fixture(autouse=True)
    def _fresh(self, monkeypatch):
        monkeypatch.setattr(auth_manager, "auth_password", "right")
        monkeypatch.setattr(auth, "_LOGIN_FAILURES", {})
        monkeypatch.setattr("asyncio.sleep", AsyncMock())

    @pytest.mark.asyncio
    async def test_five_failures_then_429(self):
        for _ in range(5):
            assert (await login_handler(_login_request("wrong"))).status == 401
        response = await login_handler(_login_request("right"))
        assert response.status == 429
        assert int(response.headers["Retry-After"]) > 0

    @pytest.mark.asyncio
    async def test_the_limit_is_per_client(self):
        for _ in range(5):
            await login_handler(_login_request("wrong", remote="100.64.0.9"))
        other = await login_handler(_login_request("right", remote="100.64.0.10"))
        assert other.status == 200, "a global cap would let anyone lock the operator out"

    @pytest.mark.asyncio
    async def test_a_non_string_password_is_a_bad_request(self):
        request = _login_request(None)
        request.json = AsyncMock(return_value={"password": 123})
        assert (await login_handler(request)).status == 400


def test_the_dashboard_password_has_no_hint(monkeypatch):
    from core.settings import settings

    monkeypatch.setenv("AUTH_PASSWORD", "a-long-password-1234")
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSomethingLongXYZ9")
    entries = {s["key"]: s for g in settings.describe()["groups"] for s in g["settings"]}
    assert entries["AUTH_PASSWORD"]["hint"] == ""
    assert entries["GEMINI_API_KEY"]["hint"] == "XYZ9", "other keys still show which one is set"
