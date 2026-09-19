"""The journal keeps every event the bot emits, queryable afterwards."""

import pytest
from core.journal import TOPICS, Journal


@pytest.fixture
def journal(tmp_path):
    j = Journal(str(tmp_path / "journal.db"))
    yield j
    j.close()


class TestRecord:
    def test_log_lines_keep_agent_level_cycle_and_message(self, journal):
        row = journal.record(
            "SYSTEM_LOG",
            {"level": "WARN", "message": "Stock buffer low", "agent_name": "SENSES", "agent_id": 2},
            sender="SENSES",
            cycle=4,
        )
        assert row > 0
        (event,) = journal.query()
        assert event["agent"] == "SENSES"
        assert event["level"] == "WARN"
        assert event["cycle"] == 4
        assert event["message"] == "Stock buffer low"

    def test_structured_events_get_a_readable_summary(self, journal):
        journal.record(
            "SIM_RESULT",
            {"ticker": "T", "win_rate": 0.7, "ev_score": 0.083, "veto": False},
            "BRAIN",
        )
        journal.record(
            "TRADE_RESULT", {"ticker": "T", "outcome": "pending", "details": "T at 61¢"}, "HAND"
        )
        sim, trade = journal.query(limit=2)[::-1]
        assert "EV +0.083" in sim["message"] and "pass" in sim["message"]
        assert trade["message"].startswith("T: pending")
        assert trade["payload"]["details"] == "T at 61¢"

    def test_every_watched_topic_has_a_default_level(self):
        assert all(level in ("DEBUG", "INFO", "WARN", "ERROR") for level in TOPICS.values())


class TestQuery:
    def test_filters_by_agent_topic_and_level(self, journal):
        journal.record("SYSTEM_LOG", {"message": "a", "level": "INFO", "agent_name": "SOUL"})
        journal.record("SYSTEM_LOG", {"message": "b", "level": "ERROR", "agent_name": "HAND"})
        journal.record("SIM_RESULT", {"ticker": "X", "win_rate": 0.5, "ev_score": 0.0}, "BRAIN")
        assert [e["message"] for e in journal.query(agent="hand")] == ["b"]
        assert [e["topic"] for e in journal.query(topic="SIM_RESULT")] == ["SIM_RESULT"]
        assert [e["message"] for e in journal.query(level="error")] == ["b"]

    def test_since_id_pages_forward_oldest_first(self, journal):
        ids = [journal.record("SYSTEM_LOG", {"message": str(i)}) for i in range(5)]
        page = journal.query(since_id=ids[1], limit=10)
        assert [e["message"] for e in page] == ["2", "3", "4"]

    def test_newest_first_by_default_and_count(self, journal):
        for i in range(3):
            journal.record("SYSTEM_LOG", {"message": str(i)})
        assert [e["message"] for e in journal.query()] == ["2", "1", "0"]
        assert journal.count() == 3


class TestResilience:
    def test_an_unwritable_path_never_raises(self, tmp_path):
        j = Journal(str(tmp_path / "missing-dir" / "x" / "journal.db"))
        assert j.record("SYSTEM_LOG", {"message": "x"}) == -1
        assert j.query() == []
        assert j.count() == 0
