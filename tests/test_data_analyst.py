"""
Tests for agents.data_analyst — match-to-dataframe conversion, summary
stats, opponent-strength context, and the before/after split. No network
calls: stats_api functions are mocked throughout.
"""

import json

import pandas as pd
import pytest
import requests

import agents.data_analyst as data_analyst
from agents.data_analyst import (
    _attach_opponent_positions,
    _compute_rolling_series,
    _matches_to_df,
    _standings_position_map,
    _summarize,
    analyze_before_after,
    get_headline_stats,
)

TEAM_ID = 57  # arbitrary — matches "home"/"away" id checks in fixture data


def make_match(date, home_id, away_id, home_score, away_score, competition_code="PL"):
    """Build a fake football-data.org match dict."""
    return {
        "utcDate": f"{date}T15:00:00Z",
        "homeTeam": {"id": home_id, "name": "Home Team"},
        "awayTeam": {"id": away_id, "name": "Away Team"},
        "score": {"fullTime": {"home": home_score, "away": away_score}},
        "competition": {"code": competition_code},
    }


@pytest.fixture(autouse=True)
def reset_standings_failure_cache():
    """The module remembers competitions with no standings across calls
    within a run — reset it between tests so they don't interfere."""
    data_analyst._STANDINGS_UNAVAILABLE.clear()
    yield
    data_analyst._STANDINGS_UNAVAILABLE.clear()


class TestMatchesToDf:
    def test_win_as_home_team(self):
        matches = [make_match("2025-01-05", TEAM_ID, 999, 2, 1)]
        df = _matches_to_df(matches, TEAM_ID)
        assert len(df) == 1
        assert df.iloc[0]["result"] == "W"
        assert df.iloc[0]["goals_for"] == 2
        assert df.iloc[0]["goals_against"] == 1
        assert bool(df.iloc[0]["home"]) is True

    def test_loss_as_away_team(self):
        matches = [make_match("2025-01-05", 999, TEAM_ID, 3, 1)]
        df = _matches_to_df(matches, TEAM_ID)
        assert df.iloc[0]["result"] == "L"
        assert df.iloc[0]["goals_for"] == 1  # our team's (away) score
        assert df.iloc[0]["goals_against"] == 3
        assert bool(df.iloc[0]["home"]) is False

    def test_draw(self):
        matches = [make_match("2025-01-05", TEAM_ID, 999, 1, 1)]
        df = _matches_to_df(matches, TEAM_ID)
        assert df.iloc[0]["result"] == "D"

    def test_unplayed_match_is_skipped(self):
        matches = [make_match("2025-01-05", TEAM_ID, 999, None, None)]
        df = _matches_to_df(matches, TEAM_ID)
        assert df.empty

    def test_empty_input_returns_empty_df(self):
        df = _matches_to_df([], TEAM_ID)
        assert df.empty

    def test_results_sorted_chronologically(self):
        matches = [
            make_match("2025-03-01", TEAM_ID, 999, 1, 0),
            make_match("2025-01-01", TEAM_ID, 999, 2, 0),
            make_match("2025-02-01", TEAM_ID, 999, 0, 0),
        ]
        df = _matches_to_df(matches, TEAM_ID)
        dates = df["date"].dt.strftime("%Y-%m-%d").tolist()
        assert dates == ["2025-01-01", "2025-02-01", "2025-03-01"]


class TestSummarize:
    def test_empty_dataframe(self):
        assert _summarize(pd.DataFrame()) == {"matches": 0}

    def test_mixed_results(self):
        matches = [
            make_match("2025-01-01", TEAM_ID, 999, 2, 1),  # W
            make_match("2025-01-08", TEAM_ID, 999, 0, 0),  # D
            make_match("2025-01-15", TEAM_ID, 999, 0, 3),  # L
        ]
        df = _matches_to_df(matches, TEAM_ID)
        summary = _summarize(df)

        assert summary["matches"] == 3
        assert summary["wins"] == 1
        assert summary["draws"] == 1
        assert summary["losses"] == 1
        assert summary["win_rate"] == round(1 / 3 * 100, 1)
        assert summary["avg_goals_for"] == round((2 + 0 + 0) / 3, 2)
        assert summary["avg_goals_against"] == round((1 + 0 + 3) / 3, 2)


class TestAnalyzeBeforeAfter:
    def test_splits_matches_around_pivot_date(self, tmp_path, mocker):
        matches = [
            make_match("2025-01-01", TEAM_ID, 999, 2, 0),  # before
            make_match("2025-01-05", TEAM_ID, 999, 1, 1),  # before
            make_match("2025-02-01", TEAM_ID, 999, 0, 1),  # after
        ]
        mocker.patch("agents.data_analyst.stats_api.get_team_matches", return_value=matches)
        mocker.patch("agents.data_analyst.stats_api.get_standings", return_value={"standings": []})
        # chart save goes to a temp dir instead of the real data/ folder
        mocker.patch("agents.data_analyst.config.CHART_OUTPUT_DIR", str(tmp_path))

        result = analyze_before_after(TEAM_ID, "2025-01-20", window_days=60)

        assert result["pre"]["matches"] == 2
        assert result["post"]["matches"] == 1
        assert result["chart_path"] == str(tmp_path / "before_after_chart.png")
        assert (tmp_path / "before_after_chart.png").exists()

    def test_no_matches_returns_error(self, mocker):
        mocker.patch("agents.data_analyst.stats_api.get_team_matches", return_value=[])
        result = analyze_before_after(TEAM_ID, "2025-01-20")
        assert "error" in result

    def test_includes_opponent_position_end_to_end(self, tmp_path, mocker):
        matches = [
            make_match("2025-01-01", TEAM_ID, 111, 2, 0),  # before, vs team 111
            make_match("2025-02-01", TEAM_ID, 222, 0, 1),  # after, vs team 222
        ]
        standings = {
            "standings": [{
                "type": "TOTAL",
                "table": [
                    {"position": 3, "team": {"id": 111}},
                    {"position": 15, "team": {"id": 222}},
                ],
            }]
        }
        mocker.patch("agents.data_analyst.stats_api.get_team_matches", return_value=matches)
        mocker.patch("agents.data_analyst.stats_api.get_standings", return_value=standings)
        mocker.patch("agents.data_analyst.config.CHART_OUTPUT_DIR", str(tmp_path))

        result = analyze_before_after(TEAM_ID, "2025-01-20", window_days=60)

        assert result["pre"]["avg_opponent_position"] == 3.0
        assert result["post"]["avg_opponent_position"] == 15.0


class TestStandingsPositionMap:
    def test_builds_map_from_total_table(self, mocker):
        standings = {
            "standings": [{
                "type": "TOTAL",
                "table": [
                    {"position": 1, "team": {"id": 100}},
                    {"position": 2, "team": {"id": 200}},
                ],
            }]
        }
        mocker.patch("agents.data_analyst.stats_api.get_standings", return_value=standings)

        result = _standings_position_map("PL")
        assert result == {100: 1, 200: 2}

    def test_ignores_home_away_split_tables(self, mocker):
        standings = {
            "standings": [
                {"type": "HOME", "table": [{"position": 1, "team": {"id": 999}}]},
                {"type": "TOTAL", "table": [{"position": 5, "team": {"id": 100}}]},
            ]
        }
        mocker.patch("agents.data_analyst.stats_api.get_standings", return_value=standings)

        result = _standings_position_map("PL")
        assert result == {100: 5}
        assert 999 not in result

    def test_competition_without_standings_returns_empty_and_is_remembered(self, mocker):
        mock_get = mocker.patch(
            "agents.data_analyst.stats_api.get_standings",
            side_effect=requests.HTTPError("404"),
        )

        first = _standings_position_map("EC")  # e.g. a cup competition
        second = _standings_position_map("EC")  # should not re-fetch

        assert first == {}
        assert second == {}
        mock_get.assert_called_once()  # second call short-circuited via the failure cache

    def test_empty_or_missing_code_returns_empty_without_fetching(self, mocker):
        mock_get = mocker.patch("agents.data_analyst.stats_api.get_standings")
        assert _standings_position_map("") == {}
        mock_get.assert_not_called()


class TestAttachOpponentPositions:
    def test_adds_position_column(self, mocker):
        matches = [
            make_match("2025-01-01", TEAM_ID, 111, 2, 0, competition_code="PL"),
            make_match("2025-01-08", TEAM_ID, 222, 1, 1, competition_code="PL"),
        ]
        df = _matches_to_df(matches, TEAM_ID)
        mocker.patch(
            "agents.data_analyst._standings_position_map",
            return_value={111: 4, 222: 9},
        )

        result = _attach_opponent_positions(df)

        assert result.iloc[0]["opponent_position"] == 4
        assert result.iloc[1]["opponent_position"] == 9

    def test_missing_opponent_in_standings_is_nan(self, mocker):
        matches = [make_match("2025-01-01", TEAM_ID, 111, 2, 0)]
        df = _matches_to_df(matches, TEAM_ID)
        mocker.patch("agents.data_analyst._standings_position_map", return_value={})

        result = _attach_opponent_positions(df)
        assert pd.isna(result.iloc[0]["opponent_position"])


class TestSummarizeOpponentContext:
    def test_includes_avg_opponent_position_when_available(self):
        matches = [
            make_match("2025-01-01", TEAM_ID, 111, 2, 0),
            make_match("2025-01-08", TEAM_ID, 222, 1, 1),
        ]
        df = _matches_to_df(matches, TEAM_ID)
        df["opponent_position"] = [4, 8]

        summary = _summarize(df)
        assert summary["avg_opponent_position"] == 6.0
        assert summary["opponent_position_coverage"] == "2/2 matches"
        assert "opponent_position_note" in summary

    def test_partial_coverage_still_averages_known_values(self):
        matches = [
            make_match("2025-01-01", TEAM_ID, 111, 2, 0),
            make_match("2025-01-08", TEAM_ID, 222, 1, 1),
        ]
        df = _matches_to_df(matches, TEAM_ID)
        df["opponent_position"] = [4, float("nan")]

        summary = _summarize(df)
        assert summary["avg_opponent_position"] == 4.0
        assert summary["opponent_position_coverage"] == "1/2 matches"

    def test_no_opponent_position_column_omits_the_field(self):
        matches = [make_match("2025-01-01", TEAM_ID, 111, 2, 0)]
        df = _matches_to_df(matches, TEAM_ID)  # no opponent_position column added

        summary = _summarize(df)
        assert "avg_opponent_position" not in summary

    def test_numeric_fields_are_json_serializable(self):
        # Regression test: pandas .mean() returns numpy scalars, which
        # json.dumps() cannot serialize (this bit the /analyze/stream SSE
        # endpoint — a raw dict, not run through Pydantic — before the
        # values were explicitly cast to native float/int).
        matches = [
            make_match("2025-01-01", TEAM_ID, 111, 2, 0),
            make_match("2025-01-08", TEAM_ID, 222, 0, 1),
        ]
        df = _matches_to_df(matches, TEAM_ID)
        summary = _summarize(df)

        json.dumps(summary)  # raises TypeError if any value is a numpy scalar
        assert type(summary["win_rate"]) is float
        assert type(summary["avg_goals_for"]) is float
        assert type(summary["avg_goals_against"]) is float


class TestComputeRollingSeries:
    def test_empty_dataframe_returns_empty_list(self):
        assert _compute_rolling_series(pd.DataFrame()) == []

    def test_rolling_win_rate_matches_manual_calculation(self):
        # Sequence: W, W, L, D, W, L, W
        matches = [
            make_match("2025-01-01", TEAM_ID, 1, 2, 0),  # W
            make_match("2025-01-08", TEAM_ID, 2, 3, 1),  # W
            make_match("2025-01-15", TEAM_ID, 3, 0, 2),  # L
            make_match("2025-01-22", TEAM_ID, 4, 1, 1),  # D
            make_match("2025-01-29", TEAM_ID, 5, 2, 0),  # W
            make_match("2025-02-05", TEAM_ID, 6, 0, 1),  # L
            make_match("2025-02-12", TEAM_ID, 7, 3, 0),  # W
        ]
        df = _matches_to_df(matches, TEAM_ID)
        series = _compute_rolling_series(df, window=5)

        actual = [p["rolling_win_rate"] for p in series]
        # Trailing window=5, min_periods=1 (early points use fewer matches):
        #   [W]                     -> 100.0
        #   [W,W]                   -> 100.0
        #   [W,W,L]                 -> 66.7
        #   [W,W,L,D]               -> 50.0
        #   [W,W,L,D,W]             -> 60.0
        #   [W,L,D,W,L]  (last 5)   -> 40.0
        #   [L,D,W,L,W]  (last 5)   -> 40.0
        assert actual == [100.0, 100.0, 66.7, 50.0, 60.0, 40.0, 40.0]

    def test_points_are_chronologically_ordered(self):
        matches = [
            make_match("2025-03-01", TEAM_ID, 1, 1, 0),
            make_match("2025-01-01", TEAM_ID, 2, 1, 0),
            make_match("2025-02-01", TEAM_ID, 3, 1, 0),
        ]
        df = _matches_to_df(matches, TEAM_ID)
        series = _compute_rolling_series(df)
        dates = [p["date"] for p in series]
        assert dates == sorted(dates)

    def test_point_structure(self):
        matches = [make_match("2025-01-01", TEAM_ID, 111, 2, 0)]
        df = _matches_to_df(matches, TEAM_ID)
        series = _compute_rolling_series(df)
        assert set(series[0].keys()) == {"date", "opponent", "result", "rolling_win_rate"}

    def test_values_are_json_serializable(self):
        matches = [make_match("2025-01-01", TEAM_ID, 111, 2, 0)]
        df = _matches_to_df(matches, TEAM_ID)
        series = _compute_rolling_series(df)
        json.dumps(series)  # raises TypeError if rolling_win_rate is a numpy scalar
        assert type(series[0]["rolling_win_rate"]) is float

    def test_series_included_in_analyze_before_after(self, tmp_path, mocker):
        matches = [
            make_match("2025-01-01", TEAM_ID, 999, 2, 0),
            make_match("2025-02-01", TEAM_ID, 999, 0, 1),
        ]
        mocker.patch("agents.data_analyst.stats_api.get_team_matches", return_value=matches)
        mocker.patch("agents.data_analyst.stats_api.get_standings", return_value={"standings": []})
        mocker.patch("agents.data_analyst.config.CHART_OUTPUT_DIR", str(tmp_path))

        result = analyze_before_after(TEAM_ID, "2025-01-20", window_days=60)

        assert "series" in result
        assert len(result["series"]) == 2
        assert result["series"][0]["date"] == "2025-01-01"
        assert result["series"][1]["date"] == "2025-02-01"


class TestGetHeadlineStats:
    def test_returns_row_for_known_team(self, mocker):
        standings = {
            "standings": [{
                "type": "TOTAL",
                "table": [{
                    "position": 3, "team": {"id": 57}, "playedGames": 20,
                    "won": 12, "draw": 5, "lost": 3,
                    "goalsFor": 35, "goalsAgainst": 18, "goalDifference": 17,
                    "points": 41,
                }],
            }]
        }
        mocker.patch("agents.data_analyst.stats_api.get_standings", return_value=standings)

        result = get_headline_stats(57, "PL")
        assert result == {
            "position": 3, "played": 20, "won": 12, "draw": 5, "lost": 3,
            "goals_for": 35, "goals_against": 18, "goal_difference": 17, "points": 41,
        }

    def test_returns_none_for_unknown_team(self, mocker):
        standings = {"standings": [{"type": "TOTAL", "table": [{"position": 1, "team": {"id": 999}}]}]}
        mocker.patch("agents.data_analyst.stats_api.get_standings", return_value=standings)
        assert get_headline_stats(57, "PL") is None

    def test_returns_none_for_competition_without_standings(self, mocker):
        mocker.patch("agents.data_analyst.stats_api.get_standings", side_effect=requests.HTTPError("404"))
        assert get_headline_stats(57, "EC") is None

    def test_values_are_json_serializable(self, mocker):
        standings = {
            "standings": [{
                "type": "TOTAL",
                "table": [{
                    "position": 3, "team": {"id": 57}, "playedGames": 20,
                    "won": 12, "draw": 5, "lost": 3,
                    "goalsFor": 35, "goalsAgainst": 18, "goalDifference": 17,
                    "points": 41,
                }],
            }]
        }
        mocker.patch("agents.data_analyst.stats_api.get_standings", return_value=standings)
        result = get_headline_stats(57, "PL")
        json.dumps(result)  # these come straight from parsed JSON, so should already be native types