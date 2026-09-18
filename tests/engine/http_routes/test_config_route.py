"""The dashboard reads and edits the engine's real settings through /config.

GET must report what the engine runs with (environment overrides included,
secrets masked). POST must validate as a batch, require a session, and say
which keys need a restart.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from core import constants
from core.vault import RecursiveVault
from http_api.routes import engine_config, get_config, get_decisions, get_journal, update_config


@pytest.fixture
def engine():
    vault = RecursiveVault(test_mode=True)
    bus = SimpleNamespace(publish=AsyncMock())
    return SimpleNamespace(
        vault=vault, bus=bus, brain=SimpleNamespace(gemini_model="gemini-3.8-flash")
    )


def _request(body=None, headers=None, query=None):
    req = SimpleNamespace(headers=headers or {}, query=query or {})
    req.json = AsyncMock(return_value=body)
    return req


@pytest.fixture
def signed_in(monkeypatch):
    from core.auth import auth_manager

    monkeypatch.setattr(auth_manager, "authenticated", True)
    yield
    monkeypatch.setattr(auth_manager, "authenticated", False)


class TestRuntimeSummary:
    def test_reports_the_limits_the_engine_runs_with(self, engine):
        cfg = engine_config(engine)
        assert cfg["brain"]["min_edge"] == constants.BRAIN_MIN_EDGE
        assert cfg["brain"]["model"] == "gemini-3.8-flash"
        assert cfg["hand"]["max_stake_cents"] == constants.HAND_MAX_STAKE_CENTS
        assert cfg["vault"]["hard_floor_cents"] == engine.vault.HARD_FLOOR_CENTS
        assert cfg["queues"]["max_execution"] == constants.MAX_EXECUTION_QUEUE_SIZE

    def test_paper_pin_reflects_the_environment(self, engine, monkeypatch):
        monkeypatch.setenv("IS_PAPER_TRADING", "true")
        assert engine_config(engine)["paper_pinned"] is True
        monkeypatch.delenv("IS_PAPER_TRADING")
        assert engine_config(engine)["paper_pinned"] is False


class TestGetConfig:
    @pytest.mark.asyncio
    async def test_returns_registry_groups_and_runtime(self, engine):
        body = json.loads((await get_config(engine)(_request())).text)
        ids = [g["id"] for g in body["groups"]]
        assert ids[:3] == ["engine", "auth", "kalshi"]
        assert body["runtime"]["vault"]["kill_switch_pct"] == engine.vault.KILL_SWITCH_THRESHOLD_PCT
        secrets = [
            x
            for g in body["groups"]
            for x in g["settings"]
            if x["kind"] in ("secret", "multiline_secret")
        ]
        assert secrets and all("value" not in x for x in secrets)


class TestUpdateConfig:
    @pytest.mark.asyncio
    async def test_requires_a_session(self, engine, monkeypatch):
        from core.auth import auth_manager

        monkeypatch.setattr(auth_manager, "authenticated", False)
        response = await update_config(engine)(_request({"changes": {"BRAIN_MIN_EDGE": 0.02}}))
        assert response.status == 401

    @pytest.mark.asyncio
    async def test_api_key_bearer_is_accepted(self, engine, monkeypatch):
        from core.auth import auth_manager

        monkeypatch.setattr(auth_manager, "authenticated", False)
        monkeypatch.setattr(auth_manager, "api_key", "k-123")
        before = constants.BRAIN_ESTIMATE_SAMPLES
        monkeypatch.delenv("BRAIN_ESTIMATE_SAMPLES", raising=False)
        try:
            response = await update_config(engine)(
                _request(
                    {"changes": {"BRAIN_ESTIMATE_SAMPLES": 2}},
                    headers={"Authorization": "Bearer k-123"},
                )
            )
            assert response.status == 200
            assert json.loads(response.text)["applied"] == ["BRAIN_ESTIMATE_SAMPLES"]
        finally:
            constants.BRAIN_ESTIMATE_SAMPLES = before

    @pytest.mark.asyncio
    async def test_applies_and_reports(self, engine, signed_in, monkeypatch):
        before = constants.BRAIN_MIN_EDGE
        monkeypatch.delenv("BRAIN_MIN_EDGE", raising=False)
        try:
            response = await update_config(engine)(
                _request({"changes": {"BRAIN_MIN_EDGE": 0.02, "KALSHI_ENV": "demo"}})
            )
            body = json.loads(response.text)
            assert response.status == 200
            assert body["applied"] == ["BRAIN_MIN_EDGE"]
            assert body["restart_required"] == ["KALSHI_ENV"]
            assert body["config"]["runtime"]["brain"]["min_edge"] == 0.02
            engine.bus.publish.assert_awaited()
        finally:
            constants.BRAIN_MIN_EDGE = before

    @pytest.mark.asyncio
    async def test_rejects_a_bad_batch_with_400(self, engine, signed_in):
        response = await update_config(engine)(_request({"changes": {"SENSES_MIN_VOLUME": -1}}))
        assert response.status == 400
        assert "SENSES_MIN_VOLUME" in json.loads(response.text)["errors"]

    @pytest.mark.asyncio
    async def test_rejects_a_malformed_body(self, engine, signed_in):
        assert (await update_config(engine)(_request({"nope": 1}))).status == 400


class TestJournalAndDecisions:
    @pytest.mark.asyncio
    async def test_journal_route_reads_the_engine_journal(self, engine, tmp_path):
        from core.journal import Journal

        engine.journal = Journal(str(tmp_path / "j.db"))
        engine.journal.record(
            "SYSTEM_LOG", {"message": "hello", "agent_name": "SOUL", "level": "INFO"}
        )
        body = json.loads(
            (await get_journal(engine)(_request(query={"agent": "soul", "limit": "5"}))).text
        )
        assert body["count"] == 1 and body["events"][0]["message"] == "hello"
        engine.journal.close()

    @pytest.mark.asyncio
    async def test_journal_route_without_a_journal_is_empty(self, engine):
        body = json.loads((await get_journal(engine)(_request())).text)
        assert body == {"events": [], "count": 0}

    @pytest.mark.asyncio
    async def test_decisions_route_reads_the_ledger(self, engine, tmp_path, monkeypatch):
        from core import ledger

        monkeypatch.setenv("GHOST_LEDGER_DB", str(tmp_path / "ledger.db"))
        ledger.record_decision(
            "T",
            0.4,
            outcome="VETOED",
            estimated_probability=0.42,
            confidence=0.9,
            veto_reason="Edge +0.020 below minimum +0.050",
        )
        body = json.loads((await get_decisions(engine)(_request(query={"limit": "10"}))).text)
        assert body["decisions"][0]["ticker"] == "T"
        assert body["decisions"][0]["veto_reason"].startswith("Edge")
