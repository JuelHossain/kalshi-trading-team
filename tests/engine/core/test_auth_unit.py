"""
Unit tests for Authentication System - Login, Logout, Session Management.
Tests production-mode authentication. Demo mode has been removed.
"""

import json
import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from core.auth import (
    MODE_PRODUCTION,
    AuthManager,
    auth_manager,
    login_handler,
    logout_handler,
    verify_handler,
)


async def get_response_json(response):
    """Helper function to extract JSON from aiohttp response."""
    # Read the response body and parse as JSON
    body = response.body
    if body is None:
        return {}
    if isinstance(body, bytes):
        return json.loads(body.decode("utf-8"))
    if isinstance(body, str):
        return json.loads(body)
    return body


class TestAuthManager:
    """Test AuthManager class initialization and core functionality."""

    def test_auth_manager_initial_state(self):
        """Auth manager starts unauthenticated. Demo mode has been removed."""
        manager = AuthManager()
        assert manager.authenticated is False
        assert manager.is_production is False
        assert manager.mode == MODE_PRODUCTION

    def test_auth_manager_has_api_key(self):
        """Auth manager generates or loads an API key."""
        manager = AuthManager()
        assert manager.api_key is not None
        assert len(manager.api_key) > 0

    def test_is_public_path_returns_true_for_public_paths(self):
        """Public paths are correctly identified."""
        manager = AuthManager()
        public_paths = [
            "/health",
            "/auth",
            "/api/auth/login",
            "/api/auth/verify",
            "/api/auth/logout",
            "/stream",
        ]
        for path in public_paths:
            assert manager.is_public_path(path) is True, f"{path} should be public"

    def test_is_public_path_returns_false_for_protected_paths(self):
        """Protected paths are correctly identified."""
        manager = AuthManager()
        protected_paths = [
            "/api/trade",
            "/api/positions",
            "/api/balance",
            "/admin",
        ]
        for path in protected_paths:
            assert manager.is_public_path(path) is False, f"{path} should be protected"

    def test_validate_api_key_from_header(self):
        """API key validation works from Authorization header."""
        manager = AuthManager()
        manager.api_key = "test-api-key-123"

        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer test-api-key-123"}
        mock_request.query = {}

        assert manager.validate_api_key(mock_request) is True

    def test_a_key_in_the_query_string_is_refused(self):
        """Query-string keys leak into logs, history and Referer; header only."""
        manager = AuthManager()
        manager.api_key = "test-api-key-123"

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.query = {"api_key": "test-api-key-123"}

        assert manager.validate_api_key(mock_request) is False

    def test_validate_api_key_rejects_invalid_key(self):
        """Invalid API keys are rejected."""
        manager = AuthManager()
        manager.api_key = "test-api-key-123"

        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer wrong-key"}
        mock_request.query = {}

        assert manager.validate_api_key(mock_request) is False

    def test_validate_api_key_rejects_empty_key(self):
        """Empty API keys are rejected."""
        manager = AuthManager()
        manager.api_key = "test-api-key-123"

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.query = {}

        assert manager.validate_api_key(mock_request) is False


class TestLoginHandler:
    """Test login_handler function for demo and production modes."""

    @pytest.fixture(autouse=True)
    def reset_auth_manager(self):
        """Reset auth manager state before each test."""
        auth_manager.authenticated = False
        auth_manager.is_production = False
        auth_manager.mode = MODE_PRODUCTION
        yield
        # Reset after test as well
        auth_manager.authenticated = False
        auth_manager.is_production = False
        auth_manager.mode = MODE_PRODUCTION

    @pytest.mark.asyncio
    async def test_login_rejects_empty_password(self):
        """An empty password is refused. Demo mode no longer grants access."""
        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"password": "", "mode": "demo"})

        response = await login_handler(mock_request)

        assert response.status == 401
        assert auth_manager.authenticated is False

    @pytest.mark.asyncio
    async def test_login_production_mode_correct_password(self):
        """Login with correct password sets production mode."""
        mock_request = MagicMock()
        mock_request.json = AsyncMock(
            return_value={"password": os.environ["AUTH_PASSWORD"], "mode": "production"}
        )

        response = await login_handler(mock_request)

        assert response.status == 200
        data = await get_response_json(response)
        assert data["isAuthenticated"] is True
        assert data["mode"] == "production"
        assert data["is_production"] is True
        assert auth_manager.authenticated is True
        assert auth_manager.mode == "production"
        assert auth_manager.is_production is True

    @pytest.mark.asyncio
    async def test_login_production_mode_wrong_password(self):
        """Login with wrong password returns 401."""
        mock_request = MagicMock()
        mock_request.json = AsyncMock(
            return_value={"password": "wrong-password", "mode": "production"}
        )

        response = await login_handler(mock_request)

        assert response.status == 401
        data = await get_response_json(response)
        assert "error" in data
        assert data["error"] == "Invalid password"
        assert auth_manager.authenticated is False

    @pytest.mark.asyncio
    async def test_client_supplied_mode_flag_cannot_downgrade_session(self):
        """A "demo" flag from the client is ignored; the server decides the mode.

        The client must not be able to talk the engine into a weaker session.
        """
        mock_request = MagicMock()
        mock_request.json = AsyncMock(
            return_value={"password": os.environ["AUTH_PASSWORD"], "mode": "demo"}
        )

        response = await login_handler(mock_request)

        assert response.status == 200
        data = await get_response_json(response)
        assert data["isAuthenticated"] is True
        assert data["mode"] == MODE_PRODUCTION
        assert data["is_production"] is True

    @pytest.mark.asyncio
    async def test_login_handles_exception(self):
        """Login handles exceptions gracefully."""
        mock_request = MagicMock()
        mock_request.json = AsyncMock(side_effect=Exception("JSON parse error"))

        response = await login_handler(mock_request)

        assert response.status == 500
        data = await get_response_json(response)
        assert "error" in data
        assert data["error"] == "Login failed"


class TestVerifyHandler:
    """Test verify_handler function for auth status checks."""

    @pytest.fixture(autouse=True)
    def reset_auth_manager(self):
        """Reset auth manager state before each test."""
        auth_manager.authenticated = False
        auth_manager.is_production = False
        auth_manager.mode = MODE_PRODUCTION
        yield
        # Reset after test
        auth_manager.authenticated = False
        auth_manager.is_production = False
        auth_manager.mode = MODE_PRODUCTION

    @pytest.mark.asyncio
    async def test_verify_returns_unauthenticated_when_not_logged_in(self):
        """Verify endpoint returns unauthenticated when not logged in."""
        mock_request = MagicMock()

        response = await verify_handler(mock_request)

        assert response.status == 200
        data = await get_response_json(response)
        assert data["isAuthenticated"] is False
        assert data["mode"] == MODE_PRODUCTION
        assert data["is_production"] is False

    @pytest.mark.asyncio
    async def test_verify_returns_authenticated_in_production_mode(self):
        """Verify endpoint returns production mode status."""
        auth_manager.authenticated = True
        auth_manager.mode = "production"
        auth_manager.is_production = True

        mock_request = MagicMock()
        response = await verify_handler(mock_request)

        data = await get_response_json(response)
        assert data["isAuthenticated"] is True
        assert data["mode"] == "production"
        assert data["is_production"] is True


class TestLogoutHandler:
    """Test logout_handler function for clearing sessions."""

    @pytest.fixture(autouse=True)
    def setup_logged_in_state(self):
        """Set up a logged-in state before each test."""
        auth_manager.authenticated = True
        auth_manager.is_production = True
        auth_manager.mode = "production"
        yield
        # Reset after test
        auth_manager.authenticated = False
        auth_manager.is_production = False
        auth_manager.mode = MODE_PRODUCTION

    @pytest.mark.asyncio
    async def test_logout_clears_session(self):
        """Logout clears all session state."""
        mock_request = MagicMock()

        response = await logout_handler(mock_request)

        assert response.status == 200
        data = await get_response_json(response)
        assert data["success"] is True
        assert "Logged out" in data["message"]
        assert auth_manager.authenticated is False
        assert auth_manager.is_production is False

    @pytest.mark.asyncio
    async def test_logout_from_authenticated_session(self):
        """Logout clears an established production session."""
        auth_manager.authenticated = True
        auth_manager.is_production = True
        auth_manager.mode = MODE_PRODUCTION

        mock_request = MagicMock()
        response = await logout_handler(mock_request)

        data = await get_response_json(response)
        assert data["success"] is True
        assert auth_manager.authenticated is False
        assert auth_manager.is_production is False


class TestAuthManagerStateTransitions:
    """Test complete state transition flows."""

    @pytest.fixture(autouse=True)
    def reset_auth_manager(self):
        """Reset auth manager state before each test."""
        auth_manager.authenticated = False
        auth_manager.is_production = False
        auth_manager.mode = MODE_PRODUCTION
        yield
        auth_manager.authenticated = False
        auth_manager.is_production = False
        auth_manager.mode = MODE_PRODUCTION

    @pytest.mark.asyncio
    async def test_full_flow(self):
        """Complete flow: login -> verify -> logout."""
        # Login
        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"password": os.environ["AUTH_PASSWORD"]})
        response = await login_handler(mock_request)
        assert response.status == 200

        # Verify
        mock_request = MagicMock()
        response = await verify_handler(mock_request)
        data = await get_response_json(response)
        assert data["isAuthenticated"] is True
        assert data["mode"] == MODE_PRODUCTION

        # Logout
        mock_request = MagicMock()
        response = await logout_handler(mock_request)
        assert response.status == 200

        # Verify logged out
        mock_request = MagicMock()
        response = await verify_handler(mock_request)
        data = await get_response_json(response)
        assert data["isAuthenticated"] is False

    @pytest.mark.asyncio
    async def test_full_flow_production_mode(self):
        """Complete flow: login (production) -> verify -> logout."""
        # Login
        mock_request = MagicMock()
        mock_request.json = AsyncMock(
            return_value={"password": os.environ["AUTH_PASSWORD"], "mode": "production"}
        )
        response = await login_handler(mock_request)
        assert response.status == 200

        # Verify
        mock_request = MagicMock()
        response = await verify_handler(mock_request)
        data = await get_response_json(response)
        assert data["isAuthenticated"] is True
        assert data["mode"] == "production"
        assert data["is_production"] is True

        # Logout
        mock_request = MagicMock()
        response = await logout_handler(mock_request)
        assert response.status == 200

        # Verify logged out
        mock_request = MagicMock()
        response = await verify_handler(mock_request)
        data = await get_response_json(response)
        assert data["isAuthenticated"] is False
        assert data["is_production"] is False

    @pytest.mark.asyncio
    async def test_failed_login_does_not_change_state(self):
        """Failed login attempt does not modify auth state."""
        # First successful login
        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"password": os.environ["AUTH_PASSWORD"]})
        await login_handler(mock_request)

        # Failed login attempt
        mock_request = MagicMock()
        mock_request.json = AsyncMock(
            return_value={"password": "wrong-password", "mode": "production"}
        )
        response = await login_handler(mock_request)
        assert response.status == 401

        # Verify still logged in from first attempt
        mock_request = MagicMock()
        response = await verify_handler(mock_request)
        data = await get_response_json(response)
        assert data["isAuthenticated"] is True
        assert data["mode"] == MODE_PRODUCTION


class TestAuthPasswordConfiguration:
    """The auth password must come from the environment, with no default.

    This class previously asserted the opposite -- that AuthManager.AUTH_PASSWORD
    falls back to a literal compiled into the source. That same literal was also
    built into the frontend bundle and is still in git history. These tests guard
    against a default being reintroduced.
    """

    def test_password_comes_from_environment(self):
        assert auth_manager.auth_password == os.environ["AUTH_PASSWORD"]

    def test_construction_fails_without_a_configured_password(self, monkeypatch):
        monkeypatch.delenv("AUTH_PASSWORD", raising=False)
        with pytest.raises(ValueError, match="AUTH_PASSWORD not configured"):
            AuthManager()
