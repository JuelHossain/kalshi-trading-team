"""A restart-only edit must read as pending until a restart, everywhere.

settings.update writes os.environ at once, and /config then showed the new
KALSHI_ENV as the one in use while the Kalshi client still spoke to the old
exchange. The only sign a restart was needed lived in one browser tab's
memory, gone on reload or on another device. And the dashboard restart
exec'd with the process's edited environment, so hand edits to engine/.env
never applied.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from core.settings import settings
from http_api.routes import engine_config, restart_engine


@pytest.fixture
def booted(monkeypatch):
    monkeypatch.setenv("KALSHI_ENV", "prod")
    monkeypatch.setattr(settings, "boot_values", {"KALSHI_ENV": "prod"})
    yield
    monkeypatch.setattr(settings, "boot_values", {})


def test_nothing_is_pending_at_boot(booted):
    assert settings.restart_pending() == []
    assert settings.describe()["restart_pending"] == []


def test_an_edit_is_pending_until_restart(booted, monkeypatch):
    monkeypatch.setenv("KALSHI_ENV", "demo")  # what settings.update does

    assert settings.restart_pending() == ["KALSHI_ENV"]
    entry = next(
        s for g in settings.describe()["groups"] for s in g["settings"] if s["key"] == "KALSHI_ENV"
    )
    assert entry["pending"] is True


def test_the_runtime_summary_names_the_exchange_in_use(booted, monkeypatch):
    from core.vault import RecursiveVault

    monkeypatch.setenv("KALSHI_ENV", "demo")
    engine = SimpleNamespace(vault=RecursiveVault(test_mode=True), brain=None)

    assert engine_config(engine)["kalshi_env"] == "prod"


@pytest.mark.asyncio
async def test_restart_goes_through_a_clean_shutdown(monkeypatch):
    """The re-exec now happens in GhostEngine.start after the loop closes,
    with the boot environment; the route only asks for it."""
    import asyncio

    from core.auth import auth_manager

    monkeypatch.setattr(auth_manager, "authenticated", True)
    engine = SimpleNamespace(shutdown=AsyncMock())
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    await restart_engine(engine)(SimpleNamespace(headers={}))
    await asyncio.gather(
        *[t for t in asyncio.all_tasks() if t is not asyncio.current_task()], return_exceptions=True
    )

    assert engine.restart_requested is True
    engine.shutdown.assert_awaited_once()
