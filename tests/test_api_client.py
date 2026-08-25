"""
Tests for ui.api_client — the HTTP wrapper the Streamlit UI uses to talk
to the FastAPI backend. No real network calls: requests.get/post are
mocked throughout.
"""

import json
from unittest.mock import MagicMock

import pytest
import requests

from ui import api_client


def _mock_json_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(f"{status_code} error")
    else:
        resp.raise_for_status.return_value = None
    return resp


def _mock_stream_response(events: list[dict], status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status.return_value = None
    lines = [f"data: {json.dumps(e)}" for e in events]
    resp.iter_lines.return_value = iter(lines)
    return resp


class TestGetCompetitions:
    def test_returns_parsed_json(self, mocker):
        fake_data = [{"code": "PL", "name": "Premier League"}]
        mocker.patch("ui.api_client.requests.get", return_value=_mock_json_response(json_data=fake_data))

        result = api_client.get_competitions()
        assert result == fake_data

    def test_connection_failure_raises_api_error(self, mocker):
        mocker.patch("ui.api_client.requests.get", side_effect=requests.ConnectionError("refused"))

        with pytest.raises(api_client.ApiError, match="Could not reach the API"):
            api_client.get_competitions()


class TestGetTeams:
    def test_passes_competition_param(self, mocker):
        mock_get = mocker.patch("ui.api_client.requests.get", return_value=_mock_json_response(json_data=[]))
        api_client.get_teams("PL")
        _, kwargs = mock_get.call_args
        assert kwargs["params"] == {"competition": "PL"}

    def test_no_competition_sends_empty_params(self, mocker):
        mock_get = mocker.patch("ui.api_client.requests.get", return_value=_mock_json_response(json_data=[]))
        api_client.get_teams(None)
        _, kwargs = mock_get.call_args
        assert kwargs["params"] == {}

    def test_server_error_raises_api_error(self, mocker):
        mocker.patch("ui.api_client.requests.get", return_value=_mock_json_response(status_code=500))
        with pytest.raises(api_client.ApiError):
            api_client.get_teams("PL")


class TestGetCrest:
    def test_returns_crest_url(self, mocker):
        mocker.patch("ui.api_client.requests.get",
                      return_value=_mock_json_response(json_data={"crest_url": "https://x.com/c.png"}))
        assert api_client.get_crest(57) == "https://x.com/c.png"

    def test_never_raises_on_failure(self, mocker):
        mocker.patch("ui.api_client.requests.get", side_effect=requests.ConnectionError("refused"))
        assert api_client.get_crest(57) is None  # crest is a nice-to-have


class TestGetHeadlineStats:
    def test_returns_stats_when_available(self, mocker):
        fake_data = {"available": True, "position": 3, "goal_difference": 17}
        mocker.patch("ui.api_client.requests.get", return_value=_mock_json_response(json_data=fake_data))

        result = api_client.get_headline_stats(57, "PL")
        assert result == fake_data

    def test_returns_none_when_unavailable(self, mocker):
        fake_data = {"available": False, "position": None}
        mocker.patch("ui.api_client.requests.get", return_value=_mock_json_response(json_data=fake_data))

        assert api_client.get_headline_stats(57, "EC") is None

    def test_never_raises_on_connection_failure(self, mocker):
        mocker.patch("ui.api_client.requests.get", side_effect=requests.ConnectionError("refused"))
        assert api_client.get_headline_stats(57, "PL") is None


class TestRunAnalysis:
    def test_happy_path_calls_on_progress_and_returns_result(self, mocker):
        events = [
            {"type": "progress", "stage": "Researching: test"},
            {"type": "progress", "stage": "Validating the narrative"},
            {"type": "result", "result": {"verdict": "test verdict", "news": {}, "stats": None}},
        ]
        mocker.patch("ui.api_client.requests.post", return_value=_mock_stream_response(events))

        seen_stages = []
        result = api_client.run_analysis(57, "Arsenal FC", "test query", 60, on_progress=seen_stages.append)

        assert seen_stages == ["Researching: test", "Validating the narrative"]
        assert result["verdict"] == "test verdict"

    def test_works_without_on_progress_callback(self, mocker):
        events = [
            {"type": "progress", "stage": "Researching"},
            {"type": "result", "result": {"verdict": "v", "news": {}, "stats": None}},
        ]
        mocker.patch("ui.api_client.requests.post", return_value=_mock_stream_response(events))

        result = api_client.run_analysis(57, "Arsenal FC", "q", 60)  # no on_progress at all
        assert result["verdict"] == "v"

    def test_error_event_raises_api_error(self, mocker):
        events = [
            {"type": "progress", "stage": "Researching"},
            {"type": "error", "detail": "pipeline exploded"},
        ]
        mocker.patch("ui.api_client.requests.post", return_value=_mock_stream_response(events))

        with pytest.raises(api_client.ApiError, match="pipeline exploded"):
            api_client.run_analysis(57, "Arsenal FC", "q", 60)

    def test_connection_failure_raises_api_error(self, mocker):
        mocker.patch("ui.api_client.requests.post", side_effect=requests.ConnectionError("refused"))

        with pytest.raises(api_client.ApiError, match="Could not reach the API"):
            api_client.run_analysis(57, "Arsenal FC", "q", 60)

    def test_stream_ending_without_result_raises_api_error(self, mocker):
        events = [{"type": "progress", "stage": "Researching"}]  # never sends a result
        mocker.patch("ui.api_client.requests.post", return_value=_mock_stream_response(events))

        with pytest.raises(api_client.ApiError, match="ended without a result"):
            api_client.run_analysis(57, "Arsenal FC", "q", 60)

    def test_blank_and_malformed_lines_are_skipped(self, mocker):
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        resp.iter_lines.return_value = iter([
            "",  # blank line (SSE event separator)
            "not a data line",  # doesn't start with "data: "
            f'data: {json.dumps({"type": "result", "result": {"verdict": "v", "news": {}, "stats": None}})}',
        ])
        mocker.patch("ui.api_client.requests.post", return_value=resp)

        result = api_client.run_analysis(57, "Arsenal FC", "q", 60)
        assert result["verdict"] == "v"