"""Getting settled markets in.

Fetching needs network access to Kalshi; scoring does not. Keeping them apart
means the fetch runs wherever the network is and the scorer runs anywhere over
the resulting file -- which is also what makes a backtest reproducible.
"""

import json

import pytest
from backtest.runner import load_settled_markets, run_backtest

CSV = """ticker,probability,price,settled_yes,confidence
KXA,0.80,0.50,1,0.95
KXB,0.20,0.70,0,0.90
KXC,0.55,0.50,true,0.88
"""


@pytest.fixture
def csv_file(tmp_path):
    path = tmp_path / "settled.csv"
    path.write_text(CSV)
    return path


class TestLoading:
    def test_csv_numbers_are_parsed(self, csv_file):
        rows = load_settled_markets(csv_file)
        assert len(rows) == 3
        assert rows[0]["probability"] == pytest.approx(0.80)
        assert rows[0]["settled_yes"] is True

    @pytest.mark.parametrize(
        "text,expected",
        [("1", True), ("0", False), ("true", True), ("FALSE", False), ("yes", True), ("n", False)],
    )
    def test_outcomes_are_accepted_in_the_forms_people_write_them(self, tmp_path, text, expected):
        path = tmp_path / "x.csv"
        path.write_text(f"ticker,probability,price,settled_yes\nK,0.6,0.5,{text}\n")
        assert load_settled_markets(path)[0]["settled_yes"] is expected

    def test_json_is_accepted(self, tmp_path):
        path = tmp_path / "settled.json"
        path.write_text(
            json.dumps([{"ticker": "KXA", "probability": 0.8, "price": 0.5, "settled_yes": True}])
        )
        assert load_settled_markets(path)[0]["probability"] == pytest.approx(0.8)

    def test_an_end_to_end_run_scores_the_file(self, csv_file):
        result = run_backtest(csv_file)
        assert result.n == 3
        # All three clear the 5c minimum. KXC sits exactly on it, and the
        # boundary is inclusive here as it is in the Brain (ev >= MIN_EDGE).
        assert result.traded == 3

    def test_the_edge_threshold_boundary_is_inclusive(self, tmp_path):
        path = tmp_path / "edge.csv"
        path.write_text(
            "ticker,probability,price,settled_yes\n"
            "AT,0.55,0.50,1\n"  # edge exactly 0.05 -> trades
            "UNDER,0.549,0.50,1\n"  # edge 0.049 -> does not
        )
        assert run_backtest(path, min_edge=0.05).traded == 1


class TestMalformedFilesFailLoudly:
    """A backtest quietly missing half its data is worse than no backtest."""

    def test_a_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_settled_markets(tmp_path / "nope.csv")

    def test_a_non_numeric_probability_raises_naming_the_row(self, tmp_path):
        path = tmp_path / "bad.csv"
        path.write_text("ticker,probability,price,settled_yes\nKXA,high,0.5,1\n")
        with pytest.raises(ValueError, match="KXA"):
            load_settled_markets(path)

    def test_an_unreadable_outcome_raises(self, tmp_path):
        path = tmp_path / "bad.csv"
        path.write_text("ticker,probability,price,settled_yes\nKXA,0.6,0.5,maybe\n")
        with pytest.raises(ValueError, match="settled_yes"):
            load_settled_markets(path)

    def test_json_that_is_not_a_list_raises(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text('{"probability": 0.6}')
        with pytest.raises(ValueError, match="list"):
            load_settled_markets(path)
