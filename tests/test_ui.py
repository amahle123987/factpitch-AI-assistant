"""
UI tests for ui/app.py using Streamlit's AppTest framework — runs the real
app script headlessly (no browser needed) and drives it like a user would:
selecting a team, typing a query, clicking Analyze.

Since ui/app.py talks to the FastAPI backend exclusively through
ui/api_client.py, everything here mocks that module's functions directly
(get_competitions, get_teams, get_crest, run_analysis) rather than the
agents/tools underneath the API — that boundary is covered separately by
tests/test_api_client.py and tests/test_api.py.
"""

import os
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = os.path.join(os.path.dirname(__file__), "..", "ui", "app.py")

FAKE_COMPETITIONS = [{"code": "PL", "name": "Premier League"}]
FAKE_TEAMS = [{"id": 57, "name": "Arsenal FC", "competition": "PL"}]
FAKE_HEADLINE = {
    "available": True, "position": 3, "played": 20, "won": 12, "draw": 5, "lost": 3,
    "goals_for": 35, "goals_against": 18, "goal_difference": 17, "points": 41,
}

FAKE_RESULT = {
    "news": {
        "query": "test query",
        "key_events": [{"date": "2025-10-14", "headline": "exact event", "detail": ""}],
        "primary_event": {"date": "2025-10-14", "headline": "exact event", "reason": "clear"},
        "summary": "test summary",
    },
    "stats": {
        "pivot_date": "2025-10-14",
        "pre": {"matches": 3, "wins": 1, "draws": 1, "losses": 1, "win_rate": 33.3,
                "avg_goals_for": 1.0, "avg_goals_against": 1.0},
        "post": {"matches": 2, "wins": 2, "draws": 0, "losses": 0, "win_rate": 100.0,
                 "avg_goals_for": 2.0, "avg_goals_against": 0.5},
        "series": [
            {"date": "2025-09-01", "opponent": "Team X", "result": "W", "rolling_win_rate": 100.0},
            {"date": "2025-10-14", "opponent": "Team Y", "result": "L", "rolling_win_rate": 50.0},
        ],
        "chart_path": None,
    },
    "verdict": "test verdict text",
}


def _fake_run_analysis_with_progress(**kwargs):
    """Simulates api_client.run_analysis firing a couple of progress
    callbacks before returning, like the real streaming version does."""
    on_progress = kwargs.get("on_progress")
    if on_progress:
        on_progress("Researching: test query")
        on_progress("Validating the narrative against the numbers")
    return FAKE_RESULT


@pytest.fixture
def mock_team_data():
    with patch("ui.api_client.get_competitions", return_value=FAKE_COMPETITIONS), \
         patch("ui.api_client.get_teams", return_value=FAKE_TEAMS), \
         patch("ui.api_client.get_crest", return_value=None), \
         patch("ui.api_client.get_headline_stats", return_value=None):
        yield


class TestEmptyState:
    def test_loads_with_no_exceptions(self, mock_team_data):
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.run()
        assert not at.exception

    def test_analyze_button_disabled_before_team_selected(self, mock_team_data):
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.run()
        assert at.button[0].disabled is True


class TestApiUnreachable:
    def test_competitions_fetch_failure_disables_widgets_gracefully(self):
        from ui.api_client import ApiError
        with patch("ui.api_client.get_competitions", side_effect=ApiError("Could not reach the API at http://x")):
            at = AppTest.from_file(APP_PATH, default_timeout=15)
            at.run()
            assert not at.exception
            assert at.button[0].disabled is True

    def test_team_fetch_failure_disables_widgets_gracefully(self):
        from ui.api_client import ApiError
        with patch("ui.api_client.get_competitions", return_value=FAKE_COMPETITIONS), \
             patch("ui.api_client.get_teams", side_effect=ApiError("Could not reach the API at http://x")):
            at = AppTest.from_file(APP_PATH, default_timeout=15)
            at.run()
            assert not at.exception
            assert at.button[0].disabled is True


class TestFullAnalysisFlow:
    def test_select_team_type_query_and_analyze(self, mock_team_data):
        with patch("ui.api_client.run_analysis", side_effect=_fake_run_analysis_with_progress):
            at = AppTest.from_file(APP_PATH, default_timeout=15)
            at.run()

            at.selectbox[1].select("Arsenal FC").run()
            assert not at.exception
            assert at.button[0].disabled is False  # enabled once a team is picked

            at.text_input[0].input("recent injury news").run()
            at.button[0].click().run()

            assert not at.exception

    def test_status_widget_shows_completion(self, mock_team_data):
        with patch("ui.api_client.run_analysis", side_effect=_fake_run_analysis_with_progress):
            at = AppTest.from_file(APP_PATH, default_timeout=15)
            at.run()
            at.selectbox[1].select("Arsenal FC").run()
            at.text_input[0].input("recent injury news").run()
            at.button[0].click().run()

            assert len(at.status) == 1
            assert at.status[0].label == "Analysis complete"
            assert at.status[0].state == "complete"

    def test_progress_stages_appear_on_page(self, mock_team_data):
        with patch("ui.api_client.run_analysis", side_effect=_fake_run_analysis_with_progress):
            at = AppTest.from_file(APP_PATH, default_timeout=15)
            at.run()
            at.selectbox[1].select("Arsenal FC").run()
            at.text_input[0].input("recent injury news").run()
            at.button[0].click().run()

            all_markdown = " ".join(md.value for md in at.markdown)
            assert "Researching: test query" in all_markdown
            assert "Validating the narrative against the numbers" in all_markdown

    def test_verdict_text_renders_on_page(self, mock_team_data):
        with patch("ui.api_client.run_analysis", side_effect=_fake_run_analysis_with_progress):
            at = AppTest.from_file(APP_PATH, default_timeout=15)
            at.run()
            at.selectbox[1].select("Arsenal FC").run()
            at.text_input[0].input("recent injury news").run()
            at.button[0].click().run()

            all_markdown = " ".join(md.value for md in at.markdown)
            assert "test verdict text" in all_markdown

    def test_results_are_organized_into_three_tabs(self, mock_team_data):
        with patch("ui.api_client.run_analysis", return_value=FAKE_RESULT):
            at = AppTest.from_file(APP_PATH, default_timeout=15)
            at.run()
            at.selectbox[1].select("Arsenal FC").run()
            at.text_input[0].input("recent injury news").run()
            at.button[0].click().run()

            labels = [tab.label for tab in at.tabs]
            assert labels == ["Overview", "Performance Trends", "News & Timeline"]

    def test_overview_tab_shows_win_rate_metrics_with_delta(self, mock_team_data):
        with patch("ui.api_client.run_analysis", return_value=FAKE_RESULT):
            at = AppTest.from_file(APP_PATH, default_timeout=15)
            at.run()
            at.selectbox[1].select("Arsenal FC").run()
            at.text_input[0].input("recent injury news").run()
            at.button[0].click().run()

            metrics = {m.label: (m.value, m.delta) for m in at.metric}
            assert metrics["Win rate before"][0] == "33.3%"
            assert metrics["Win rate after"][0] == "100.0%"
            assert metrics["Win rate after"][1] == "66.7%"

    def test_news_tab_shows_a_card_per_key_event(self, mock_team_data):
        with patch("ui.api_client.run_analysis", return_value=FAKE_RESULT):
            at = AppTest.from_file(APP_PATH, default_timeout=15)
            at.run()
            at.selectbox[1].select("Arsenal FC").run()
            at.text_input[0].input("recent injury news").run()
            at.button[0].click().run()

            all_markdown = " ".join(md.value for md in at.markdown)
            for event in FAKE_RESULT["news"]["key_events"]:
                assert event["headline"] in all_markdown
                assert event["date"] in all_markdown


class TestHeadlineMetrics:
    def test_shows_on_team_selection_before_any_query(self):
        with patch("ui.api_client.get_competitions", return_value=FAKE_COMPETITIONS), \
             patch("ui.api_client.get_teams", return_value=FAKE_TEAMS), \
             patch("ui.api_client.get_crest", return_value=None), \
             patch("ui.api_client.get_headline_stats", return_value=FAKE_HEADLINE):

            at = AppTest.from_file(APP_PATH, default_timeout=15)
            at.run()
            at.selectbox[1].select("Arsenal FC").run()

            assert not at.exception
            metrics = {m.label: m.value for m in at.metric}
            assert metrics["League Position"] == "#3"
            assert metrics["Record"] == "12-5-3"
            assert metrics["Goal Difference"] == "+17"

    def test_negative_goal_difference_has_no_extra_plus_sign(self):
        negative_headline = dict(FAKE_HEADLINE, goal_difference=-4)
        with patch("ui.api_client.get_competitions", return_value=FAKE_COMPETITIONS), \
             patch("ui.api_client.get_teams", return_value=FAKE_TEAMS), \
             patch("ui.api_client.get_crest", return_value=None), \
             patch("ui.api_client.get_headline_stats", return_value=negative_headline):

            at = AppTest.from_file(APP_PATH, default_timeout=15)
            at.run()
            at.selectbox[1].select("Arsenal FC").run()

            metrics = {m.label: m.value for m in at.metric}
            assert metrics["Goal Difference"] == "-4"

    def test_no_metrics_shown_when_headline_unavailable(self, mock_team_data):
        # mock_team_data already mocks get_headline_stats to return None
        at = AppTest.from_file(APP_PATH, default_timeout=15)
        at.run()
        at.selectbox[1].select("Arsenal FC").run()

        assert not at.exception
        labels = [m.label for m in at.metric]
        assert "League Position" not in labels


class TestRollingChart:
    def test_form_over_time_section_renders_without_exception(self, mock_team_data):
        with patch("ui.api_client.run_analysis", return_value=FAKE_RESULT):
            at = AppTest.from_file(APP_PATH, default_timeout=15)
            at.run()
            at.selectbox[1].select("Arsenal FC").run()
            at.text_input[0].input("recent injury news").run()
            at.button[0].click().run()

            assert not at.exception
            all_markdown = " ".join(md.value for md in at.markdown)
            assert "Form Over Time" in all_markdown

    def test_no_form_section_when_series_is_empty(self, mock_team_data):
        no_series_result = dict(FAKE_RESULT)
        no_series_result["stats"] = dict(FAKE_RESULT["stats"], series=[])
        with patch("ui.api_client.run_analysis", return_value=no_series_result):
            at = AppTest.from_file(APP_PATH, default_timeout=15)
            at.run()
            at.selectbox[1].select("Arsenal FC").run()
            at.text_input[0].input("recent injury news").run()
            at.button[0].click().run()

            assert not at.exception
            all_markdown = " ".join(md.value for md in at.markdown)
            assert "Form Over Time" not in all_markdown


class TestNoUsableEventPath:
    def test_status_shows_error_state_when_no_events_found(self, mock_team_data):
        no_stats_result = dict(FAKE_RESULT, stats=None)
        with patch("ui.api_client.run_analysis", return_value=no_stats_result):
            at = AppTest.from_file(APP_PATH, default_timeout=15)
            at.run()
            at.selectbox[1].select("Arsenal FC").run()
            at.text_input[0].input("vague query").run()
            at.button[0].click().run()

            assert not at.exception
            assert at.status[0].state == "error"


class TestAnalysisApiFailure:
    def test_api_error_during_analysis_shows_error_without_crashing(self, mock_team_data):
        from ui.api_client import ApiError
        with patch("ui.api_client.run_analysis", side_effect=ApiError("Could not reach the API at http://x")):
            at = AppTest.from_file(APP_PATH, default_timeout=15)
            at.run()
            at.selectbox[1].select("Arsenal FC").run()
            at.text_input[0].input("recent injury news").run()
            at.button[0].click().run()

            assert not at.exception
            assert at.status[0].state == "error"
            assert len(at.error) >= 1
