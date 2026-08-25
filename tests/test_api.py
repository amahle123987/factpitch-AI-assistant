"""
Tests for api.main — the FastAPI backend. Uses FastAPI's TestClient
(no real server, no network). Every underlying agent/tool call is mocked.
"""

from unittest.mock import patch

import json

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


class TestHealth:
    def test_returns_ok(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


class TestCompetitions:
    def test_returns_all_supported_competitions(self):
        r = client.get("/competitions")
        assert r.status_code == 200
        codes = [c["code"] for c in r.json()]
        assert "PL" in codes
        assert len(codes) == 12


class TestTeams:
    def test_returns_teams_for_competition(self):
        fake_teams = [{"id": 57, "name": "Arsenal FC", "competition": "PL"}]
        with patch("api.main.team_lookup.list_teams", return_value=fake_teams):
            r = client.get("/teams", params={"competition": "PL"})
        assert r.status_code == 200
        assert r.json()[0]["name"] == "Arsenal FC"

    def test_no_competition_param_searches_all(self):
        with patch("api.main.team_lookup.list_teams", return_value=[]) as mock_list:
            client.get("/teams")
        mock_list.assert_called_once_with(None)

    def test_unknown_competition_code_is_rejected(self):
        r = client.get("/teams", params={"competition": "NOTREAL"})
        assert r.status_code == 400


class TestTeamCrest:
    def test_returns_crest_url(self):
        with patch("api.main.stats_api.get_team_info", return_value={"crest": "https://example.com/x.png"}):
            r = client.get("/teams/57/crest")
        assert r.status_code == 200
        assert r.json()["crest_url"] == "https://example.com/x.png"

    def test_upstream_failure_returns_502(self):
        with patch("api.main.stats_api.get_team_info", side_effect=Exception("network error")):
            r = client.get("/teams/57/crest")
        assert r.status_code == 502


class TestTeamHeadline:
    FULL_STATS = {
        "position": 3, "played": 20, "won": 12, "draw": 5, "lost": 3,
        "goals_for": 35, "goals_against": 18, "goal_difference": 17, "points": 41,
    }

    def test_returns_headline_stats(self):
        with patch("api.main.data_analyst.get_headline_stats", return_value=self.FULL_STATS):
            r = client.get("/teams/57/headline", params={"competition": "PL"})
        assert r.status_code == 200
        body = r.json()
        assert body["available"] is True
        assert body["position"] == 3
        assert body["goal_difference"] == 17

    def test_unavailable_returns_null_fields(self):
        with patch("api.main.data_analyst.get_headline_stats", return_value=None):
            r = client.get("/teams/57/headline", params={"competition": "EC"})
        assert r.status_code == 200
        body = r.json()
        assert body["available"] is False
        assert body["position"] is None

    def test_unknown_competition_code_is_rejected(self):
        r = client.get("/teams/57/headline", params={"competition": "NOTREAL"})
        assert r.status_code == 400

    def test_missing_competition_param_returns_422(self):
        r = client.get("/teams/57/headline")
        assert r.status_code == 422


class TestAnalyze:
    FAKE_RESULT = {
        "news": {
            "query": "test query",
            "key_events": [{"date": "2025-10-14", "headline": "exact event", "detail": ""}],
            "primary_event": {"date": "2025-10-14", "headline": "exact event", "reason": "clear"},
            "summary": "summary text",
        },
        "stats": {"pivot_date": "2025-10-14", "pre": {"matches": 3}, "post": {"matches": 2}, "chart_path": None},
        "verdict": "test verdict",
    }

    def test_happy_path(self):
        with patch("api.main.orchestrator.run", return_value=self.FAKE_RESULT) as mock_run:
            r = client.post("/analyze", json={
                "team_id": 57, "team_name": "Arsenal FC", "query": "test query", "window_days": 90,
            })
        assert r.status_code == 200
        assert r.json()["verdict"] == "test verdict"
        mock_run.assert_called_once_with(
            team_id=57, team_name="Arsenal FC", event_query="test query", window_days=90,
        )

    def test_window_days_defaults_to_60(self):
        with patch("api.main.orchestrator.run", return_value=self.FAKE_RESULT) as mock_run:
            client.post("/analyze", json={"team_id": 57, "team_name": "Arsenal FC", "query": "q"})
        mock_run.assert_called_once_with(team_id=57, team_name="Arsenal FC", event_query="q", window_days=60)

    def test_missing_required_field_returns_422(self):
        r = client.post("/analyze", json={"team_id": 57, "team_name": "Arsenal FC"})
        assert r.status_code == 422

    def test_window_days_out_of_range_returns_422(self):
        r = client.post("/analyze", json={
            "team_id": 57, "team_name": "Arsenal FC", "query": "q", "window_days": 999,
        })
        assert r.status_code == 422

    def test_stats_none_is_valid_response(self):
        # e.g. the "couldn't find a usable event" early-exit path
        no_stats_result = dict(self.FAKE_RESULT, stats=None)
        with patch("api.main.orchestrator.run", return_value=no_stats_result):
            r = client.post("/analyze", json={"team_id": 57, "team_name": "Arsenal FC", "query": "q"})
        assert r.status_code == 200
        assert r.json()["stats"] is None

    def test_series_field_passes_through(self):
        result_with_series = dict(self.FAKE_RESULT)
        result_with_series["stats"] = dict(
            self.FAKE_RESULT["stats"],
            series=[{"date": "2025-01-01", "opponent": "X", "result": "W", "rolling_win_rate": 100.0}],
        )
        with patch("api.main.orchestrator.run", return_value=result_with_series):
            r = client.post("/analyze", json={"team_id": 57, "team_name": "Arsenal FC", "query": "q"})
        assert r.status_code == 200
        assert r.json()["stats"]["series"][0]["rolling_win_rate"] == 100.0


class TestAnalyzeStream:
    FAKE_RESULT = TestAnalyze.FAKE_RESULT

    @staticmethod
    def _fake_run_with_progress(team_id, team_name, event_query, window_days, on_progress=None):
        on_progress("Researching: test")
        on_progress("Pulling match data and computing performance")
        on_progress("Validating the narrative against the numbers")
        on_progress("Done")
        return TestAnalyzeStream.FAKE_RESULT

    @staticmethod
    def _collect_events(response) -> list[dict]:
        events = []
        for line in response.iter_lines():
            if line and line.startswith("data: "):
                events.append(json.loads(line[len("data: "):]))
        return events

    def test_streams_progress_then_result(self):
        with patch("api.main.orchestrator.run", side_effect=self._fake_run_with_progress):
            with client.stream("POST", "/analyze/stream", json={
                "team_id": 57, "team_name": "Arsenal FC", "query": "test query", "window_days": 60,
            }) as response:
                assert response.status_code == 200
                events = self._collect_events(response)

        progress_events = [e for e in events if e["type"] == "progress"]
        result_events = [e for e in events if e["type"] == "result"]
        assert len(progress_events) == 4
        assert len(result_events) == 1
        assert result_events[0]["result"]["verdict"] == "test verdict"

    def test_pipeline_failure_yields_error_event(self):
        def failing_run(team_id, team_name, event_query, window_days, on_progress=None):
            on_progress("Researching: test")
            raise RuntimeError("simulated pipeline failure")

        with patch("api.main.orchestrator.run", side_effect=failing_run):
            with client.stream("POST", "/analyze/stream", json={
                "team_id": 57, "team_name": "Arsenal FC", "query": "q", "window_days": 60,
            }) as response:
                events = self._collect_events(response)

        assert events[-1]["type"] == "error"
        assert "simulated pipeline failure" in events[-1]["detail"]

    def test_response_content_type_is_event_stream(self):
        with patch("api.main.orchestrator.run", side_effect=self._fake_run_with_progress):
            with client.stream("POST", "/analyze/stream", json={
                "team_id": 57, "team_name": "Arsenal FC", "query": "q", "window_days": 60,
            }) as response:
                assert response.headers["content-type"].startswith("text/event-stream")
                self._collect_events(response)  # drain the stream
