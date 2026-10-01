"""Settings are one registry: typed reads, validated batch writes, live application.

The dashboard edits these. Every value it shows must be what the engine
runs with, and every edit must either apply immediately or say it needs a
restart. Nothing may half-apply.
"""

import os

import pytest
from core import constants
from core.settings import REGISTRY, Live, Settings, coerce


@pytest.fixture
def clean_env(monkeypatch):
    for setting in REGISTRY:
        monkeypatch.delenv(setting.key, raising=False)
    yield


class TestReads:
    def test_default_when_unset(self, clean_env):
        s = Settings()
        assert s.get("BRAIN_MIN_EDGE") == 0.05
        assert s.get("IS_PAPER_TRADING") is True

    def test_environment_wins_and_is_typed(self, clean_env, monkeypatch):
        monkeypatch.setenv("BRAIN_MIN_EDGE", "0.01")
        monkeypatch.setenv("IS_PAPER_TRADING", "false")
        monkeypatch.setenv("SENSES_MIN_VOLUME", "350")
        s = Settings()
        assert s.get("BRAIN_MIN_EDGE") == 0.01
        assert s.get("IS_PAPER_TRADING") is False
        assert s.get_int("SENSES_MIN_VOLUME") == 350

    def test_garbage_in_the_environment_falls_back_to_the_default(self, clean_env, monkeypatch):
        monkeypatch.setenv("BRAIN_MIN_EDGE", "lots")
        assert Settings().get("BRAIN_MIN_EDGE") == 0.05


class TestDescribe:
    def test_secrets_are_masked_never_returned(self, clean_env, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyExample1234abcd")
        groups = {g["id"]: g for g in Settings().describe()["groups"]}
        gemini = next(x for x in groups["ai"]["settings"] if x["key"] == "GEMINI_API_KEY")
        assert "value" not in gemini
        assert gemini["set"] is True
        assert gemini["hint"] == "abcd"
        assert "AIzaSy" not in str(gemini)

    def test_unset_secret_reports_not_set(self, clean_env):
        groups = {g["id"]: g for g in Settings().describe()["groups"]}
        pw = next(x for x in groups["auth"]["settings"] if x["key"] == "AUTH_PASSWORD")
        assert pw["set"] is False and pw["hint"] == ""

    def test_every_setting_has_a_group_and_help(self):
        described = Settings().describe()
        keys = {x["key"] for g in described["groups"] for x in g["settings"]}
        assert keys == {s.key for s in REGISTRY}
        assert all(s.help for s in REGISTRY)


class TestUpdate:
    def test_a_bad_value_rejects_the_whole_batch(self, clean_env):
        s = Settings()
        report = s.update({"BRAIN_MIN_EDGE": "0.02", "SENSES_MIN_VOLUME": "-5"})
        assert "SENSES_MIN_VOLUME" in report.errors
        assert report.applied == []
        assert "BRAIN_MIN_EDGE" not in os.environ

    def test_applies_to_environment_and_constants(self, clean_env):
        s = Settings()
        before = constants.BRAIN_MIN_EDGE
        try:
            report = s.update({"BRAIN_MIN_EDGE": 0.02})
            assert report.applied == ["BRAIN_MIN_EDGE"] and not report.errors
            assert os.environ["BRAIN_MIN_EDGE"] == "0.02"
            assert constants.BRAIN_MIN_EDGE == 0.02
        finally:
            constants.BRAIN_MIN_EDGE = before

    def test_restart_only_settings_are_reported(self, clean_env):
        report = Settings().update({"KALSHI_ENV": "prod"})
        assert report.restart_required == ["KALSHI_ENV"]
        assert report.applied == []

    def test_choice_is_validated(self, clean_env):
        report = Settings().update({"KALSHI_ENV": "staging"})
        assert "KALSHI_ENV" in report.errors

    def test_blank_secret_is_refused(self, clean_env):
        report = Settings().update({"AUTH_PASSWORD": "   "})
        assert "AUTH_PASSWORD" in report.errors

    def test_unknown_key_is_refused(self, clean_env):
        report = Settings().update({"NOT_A_SETTING": 1})
        assert "NOT_A_SETTING" in report.errors

    def test_appliers_run_with_the_typed_value(self, clean_env):
        s = Settings()
        seen = []
        s.register_applier("HARD_FLOOR_CENTS", seen.append)
        before = constants.HARD_FLOOR_CENTS
        try:
            s.update({"HARD_FLOOR_CENTS": "20000"})
            assert seen == [20000]
        finally:
            constants.HARD_FLOOR_CENTS = before

    def test_persists_to_the_env_file(self, clean_env, tmp_path):
        env = tmp_path / ".env"
        s = Settings(env)
        s.update({"BRAIN_ESTIMATE_SAMPLES": 5, "IS_PAPER_TRADING": False})
        text = env.read_text(encoding="utf-8")
        assert "BRAIN_ESTIMATE_SAMPLES" in text and "5" in text
        assert "IS_PAPER_TRADING" in text and "false" in text
        constants.BRAIN_ESTIMATE_SAMPLES = 3

    def test_clearing_a_setting_restores_the_default(self, clean_env, tmp_path):
        env = tmp_path / ".env"
        s = Settings(env)
        s.update({"BRAIN_ESTIMATE_SAMPLES": 7})
        s.update({"BRAIN_ESTIMATE_SAMPLES": None})
        assert "BRAIN_ESTIMATE_SAMPLES" not in os.environ
        assert s.get("BRAIN_ESTIMATE_SAMPLES") == 3
        assert constants.BRAIN_ESTIMATE_SAMPLES == 3


class TestLiveDescriptor:
    def test_reads_the_constant_at_access_time(self):
        class Agent:
            MIN_EDGE = Live("BRAIN_MIN_EDGE")

        before = constants.BRAIN_MIN_EDGE
        try:
            a = Agent()
            constants.BRAIN_MIN_EDGE = 0.123
            assert a.MIN_EDGE == 0.123
            assert Agent.MIN_EDGE == 0.123
        finally:
            constants.BRAIN_MIN_EDGE = before

    def test_an_instance_override_wins_for_that_instance_only(self):
        class Agent:
            MIN_EDGE = Live("BRAIN_MIN_EDGE")

        a, b = Agent(), Agent()
        a.MIN_EDGE = 0.5
        assert a.MIN_EDGE == 0.5
        assert b.MIN_EDGE == constants.BRAIN_MIN_EDGE


class TestCoerce:
    def test_bools_accept_common_spellings(self):
        spec = next(s for s in REGISTRY if s.key == "IS_PAPER_TRADING")
        assert (
            coerce(spec, "yes") is True
            and coerce(spec, "0") is False
            and coerce(spec, True) is True
        )

    def test_ints_accept_numeric_strings(self):
        spec = next(s for s in REGISTRY if s.key == "HAND_MAX_STAKE_CENTS")
        assert coerce(spec, "1000") == 1000
        with pytest.raises(ValueError):
            coerce(spec, "50")  # below minimum
