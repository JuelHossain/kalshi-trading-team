"""
Unit tests for Authentication System - Login, Logout, Session Management.
Tests demo mode (no password) and production mode (password: 993728).
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from core.auth import (
    AuthManager,
    auth_manager,
    login_handler,
    verify_handler,
    logout_handler,
)


async def get_response_json(response):
    """Helper function to extract JSON from aiohttp response."""
    # Read the response body and parse as JSON
    body = response.body
    if body is None:
        return {}
    if isinstance(body, bytes):
        return json.loads(body.decode('utf-8'))
    if isinstance(body, str):
        return json.loads(body)
    return body


class TestAuthManager:
    """Test AuthManager class initialization and core functionality."""

    def test_auth_manager_initial_state(self):
        """Auth manager starts unauthenticated in demo mode."""
        manager = AuthManager()
        assert manager.authenticated is False
        assert manager.is_production is False
        assert manager.mode == "demo"

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

    def test_validate_api_key_from_query_param(self):
        """API key validation works from query parameter."""
        manager = AuthManager()
        manager.api_key = "test-api-key-123"

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.query = {"api_key": "test-api-key-123"}

        assert manager.validate_api_key(mock_request) is True

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
        auth_manager.mode = "demo"
        yield
        # Reset after test as well
        auth_manager.authenticated = False
        auth_manager.is_production = False
        auth_manager.mode = "demo"

    @pytest.mark.asyncio
    async def test_login_demo_mode_empty_password(self):
        """Login with empty password sets demo mode."""
        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={
            "password": "",
            "mode": "demo"
        })

        response = await login_handler(mock_request)

        assert response.status == 200
        data = await get_response_json(response)
        assert data["success"] is True
        assert data["mode"] == "demo"
        assert data["is_production"] is False
        assert auth_manager.authenticated is True
        assert auth_manager.mode == "demo"
        assert auth_manager.is_production is False

    @pytest.mark.asyncio
    async def test_login_production_mode_correct_password(self):
        """Login with correct password sets production mode."""
        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={
            "password": "993728",
            "mode": "production"
        })

        response = await login_handler(mock_request)

        assert response.status == 200
        data = await get_response_json(response)
        assert data["success"] is True
        assert data["mode"] == "production"
        assert data["is_production"] is True
        assert auth_manager.authenticated is True
        assert auth_manager.mode == "production"
        assert auth_manager.is_production is True

    @pytest.mark.asyncio
    async def test_login_production_mode_wrong_password(self):
        """Login with wrong password returns 401."""
        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={
            "password": "wrong-password",
            "mode": "production"
        })

        response = await login_handler(mock_request)

        assert response.status == 401
        data = await get_response_json(response)
        assert "error" in data
        assert data["error"] == "Invalid password"
        assert auth_manager.authenticated is False

    @pytest.mark.asyncio
    async def test_login_production_mode_with_demo_flag(self):
        """Login with correct password but demo mode stays in demo."""
        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={
            "password": "993728",
            "mode": "demo"
        })

        response = await login_handler(mock_request)

        assert response.status == 200
        data = await get_response_json(response)
        assert data["success"] is True
        assert data["mode"] == "demo"
        assert data["is_production"] is False

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
        auth_manager.mode = "demo"
        yield
        # Reset after test
        auth_manager.authenticated = False
        auth_manager.is_production = False
        auth_manager.mode = "demo"

    @pytest.mark.asyncio
    async def test_verify_returns_unauthenticated_when_not_logged_in(self):
        """Verify endpoint returns unauthenticated when not logged in."""
        mock_request = MagicMock()

        response = await verify_handler(mock_request)

        assert response.status == 200
        data = await get_response_json(response)
        assert data["authenticated"] is False
        assert data["mode"] == "demo"
        assert data["is_production"] is False

    @pytest.mark.asyncio
    async def test_verify_returns_authenticated_in_demo_mode(self):
        """Verify endpoint returns demo mode status."""
        auth_manager.authenticated = True
        auth_manager.mode = "demo"
        auth_manager.is_production = False

        mock_request = MagicMock()
        response = await verify_handler(mock_request)

        data = await get_response_json(response)
        assert data["authenticated"] is True
        assert data["mode"] == "demo"
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
        assert data["authenticated"] is True
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
        auth_manager.mode = "demo"

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
        assert auth_manager.mode == "demo"

    @pytest.mark.asyncio
    async def test_logout_from_demo_mode(self):
        """Logout works from demo mode as well."""
        auth_manager.authenticated = True
        auth_manager.is_production = False
        auth_manager.mode = "demo"

        mock_request = MagicMock()
        response = await logout_handler(mock_request)

        data = await get_response_json(response)
        assert data["success"] is True
        assert auth_manager.authenticated is False
        assert auth_manager.mode == "demo"


class TestAuthManagerStateTransitions:
    """Test complete state transition flows."""

    @pytest.fixture(autouse=True)
    def reset_auth_manager(self):
        """Reset auth manager state before each test."""
        auth_manager.authenticated = False
        auth_manager.is_production = False
        auth_manager.mode = "demo"
        yield
        auth_manager.authenticated = False
        auth_manager.is_production = False
        auth_manager.mode = "demo"

    @pytest.mark.asyncio
    async def test_full_flow_demo_mode(self):
        """Complete flow: login (demo) -> verify -> logout."""
        # Login
        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"password": "", "mode": "demo"})
        response = await login_handler(mock_request)
        assert response.status == 200

        # Verify
        mock_request = MagicMock()
        response = await verify_handler(mock_request)
        data = await get_response_json(response)
        assert data["authenticated"] is True
        assert data["mode"] == "demo"

        # Logout
        mock_request = MagicMock()
        response = await logout_handler(mock_request)
        assert response.status == 200

        # Verify logged out
        mock_request = MagicMock()
        response = await verify_handler(mock_request)
        data = await get_response_json(response)
        assert data["authenticated"] is False

    @pytest.mark.asyncio
    async def test_full_flow_production_mode(self):
        """Complete flow: login (production) -> verify -> logout."""
        # Login
        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={
            "password": "993728",
            "mode": "production"
        })
        response = await login_handler(mock_request)
        assert response.status == 200

        # Verify
        mock_request = MagicMock()
        response = await verify_handler(mock_request)
        data = await get_response_json(response)
        assert data["authenticated"] is True
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
        assert data["authenticated"] is False
        assert data["is_production"] is False

    @pytest.mark.asyncio
    async def test_failed_login_does_not_change_state(self):
        """Failed login attempt does not modify auth state."""
        # First successful login
        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={"password": "", "mode": "demo"})
        await login_handler(mock_request)

        # Failed login attempt
        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value={
            "password": "wrong-password",
            "mode": "production"
        })
        response = await login_handler(mock_request)
        assert response.status == 401

        # Verify still logged in from first attempt
        mock_request = MagicMock()
        response = await verify_handler(mock_request)
        data = await get_response_json(response)
        assert data["authenticated"] is True
        assert data["mode"] == "demo"


class TestAuthPasswordConstant:
    """Test the AUTH_PASSWORD constant."""

    def test_auth_password_is_correct_value(self):
        """Auth password is set to expected value."""
        assert AuthManager.AUTH_PASSWORD == "993728"

    def test_auth_password_is_string(self):
        """Auth password is a string type."""
        assert isinstance(AuthManager.AUTH_PASSWORD, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
