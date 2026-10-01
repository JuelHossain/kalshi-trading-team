"""Autopilot must come back after a start when the operator asked, and only then.

Resuming lived in an untracked systemd ExecStartPost hook: missing from fresh
installs, and not re-run by the dashboard Restart, which keeps the same PID.
After the Restart the Config view asks for, autopilot stayed off while the
cockpit toggle, read once at page load, still said ON.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from main import GhostEngine


def _engine(**overrides):
    engine = SimpleNamespace(
        bus=SimpleNamespace(publish=AsyncMock()),
        manual_kill_switch=False,
        vault=SimpleNamespace(kill_switch_active=False),
        soul=SimpleNamespace(is_locked_down=False, autopilot_enabled=False),
    )
    for key, value in overrides.items():
        setattr(engine, key, value)
    return engine


async def _resume(engine):
    await GhostEngine._resume_autopilot_if_asked(engine)
    return [c.args[1] for c in engine.bus.publish.await_args_list if c.args[0] == "SYSTEM_CONTROL"]


@pytest.mark.asyncio
async def test_off_by_default(monkeypatch):
    monkeypatch.delenv("AUTOPILOT_ON_BOOT", raising=False)
    monkeypatch.delenv("SENTIENT_RESUME_AUTOPILOT", raising=False)
    assert await _resume(_engine()) == []


@pytest.mark.asyncio
async def test_on_boot_resumes_paper_autopilot(monkeypatch):
    monkeypatch.setenv("AUTOPILOT_ON_BOOT", "true")
    assert await _resume(_engine()) == [{"action": "START_AUTOPILOT", "isPaperTrading": True}]


@pytest.mark.asyncio
async def test_a_dashboard_restart_carries_autopilot_across(monkeypatch):
    import os

    monkeypatch.delenv("AUTOPILOT_ON_BOOT", raising=False)
    monkeypatch.setenv("SENTIENT_RESUME_AUTOPILOT", "1")

    assert len(await _resume(_engine())) == 1
    assert "SENTIENT_RESUME_AUTOPILOT" not in os.environ, "read once, then forgotten"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "overrides",
    [
        {"manual_kill_switch": True},
        {"vault": SimpleNamespace(kill_switch_active=True)},
        {"soul": SimpleNamespace(is_locked_down=True, autopilot_enabled=False)},
    ],
)
async def test_never_while_halted(monkeypatch, overrides):
    monkeypatch.setenv("AUTOPILOT_ON_BOOT", "true")
    assert await _resume(_engine(**overrides)) == []


@pytest.mark.asyncio
async def test_health_reports_autopilot():
    from http_api.routes import health_check

    engine = _engine(soul=SimpleNamespace(is_locked_down=False, autopilot_enabled=True))
    engine.synapse = None
    engine.cycle_count = 4
    engine.is_processing = False
    engine.agents = []
    engine.vault = SimpleNamespace(kill_switch_active=False, current_balance=32813)

    import json

    body = json.loads((await health_check(engine)(None)).text)
    assert body["autopilot"] is True
