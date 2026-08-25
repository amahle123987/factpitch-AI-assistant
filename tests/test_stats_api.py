"""
Tests for tools.stats_api — cache hit/miss behavior and the 429 retry loop.
No real network calls: requests.get is mocked throughout.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from tools import stats_api


def make_response(status_code, headers=None, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.json.return_value = json_data or {}
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"{status_code} error")
    else:
        resp.raise_for_status.return_value = None
    return resp


class TestCachedGet:
    def test_cache_miss_fetches_and_stores(self, mock_db, mocker):
        response = make_response(200, json_data={"teams": ["ok"]})
        mock_get = mocker.patch("tools.stats_api.requests.get", return_value=response)

        result = stats_api._cached_get("http://fake-url")

        assert result == {"teams": ["ok"]}
        mock_get.assert_called_once()
        mock_db.commit.assert_called_once()  # confirms the result was persisted

    def test_cache_hit_skips_network_call(self, mocker):
        conn = mocker.MagicMock()
        fresh_time = datetime.now().isoformat()
        conn.execute.return_value.fetchone.return_value = (fresh_time, '{"cached": true}')
        mocker.patch("tools.stats_api._get_db", return_value=conn)
        mock_get = mocker.patch("tools.stats_api.requests.get")

        result = stats_api._cached_get("http://fake-url")

        assert result == {"cached": True}
        mock_get.assert_not_called()

    def test_expired_cache_entry_refetches(self, mocker):
        conn = mocker.MagicMock()
        stale_time = (datetime.now() - timedelta(hours=100)).isoformat()
        conn.execute.return_value.fetchone.return_value = (stale_time, '{"cached": true}')
        mocker.patch("tools.stats_api._get_db", return_value=conn)
        response = make_response(200, json_data={"fresh": True})
        mock_get = mocker.patch("tools.stats_api.requests.get", return_value=response)

        result = stats_api._cached_get("http://fake-url", ttl=timedelta(hours=6))

        assert result == {"fresh": True}
        mock_get.assert_called_once()


class TestRateLimitRetry:
    def test_recovers_after_one_429(self, mock_db, mocker):
        responses = [
            make_response(429, {"Retry-After": "1"}),
            make_response(200, json_data={"teams": ["ok"]}),
        ]
        mocker.patch("tools.stats_api.requests.get", side_effect=responses)
        mock_sleep = mocker.patch("tools.stats_api.time.sleep")

        result = stats_api._cached_get("http://fake-url")

        assert result == {"teams": ["ok"]}
        mock_sleep.assert_called_once_with(1)

    def test_gives_up_after_three_retries(self, mock_db, mocker):
        # 1 initial attempt + 3 retries, all 429 -> should raise
        responses = [make_response(429, {"Retry-After": "1"})] * 4
        mock_get = mocker.patch("tools.stats_api.requests.get", side_effect=responses)
        mocker.patch("tools.stats_api.time.sleep")

        with pytest.raises(Exception):
            stats_api._cached_get("http://fake-url")

        assert mock_get.call_count == 4

    def test_uses_default_wait_when_no_retry_after_header(self, mock_db, mocker):
        responses = [make_response(429, {}), make_response(200, json_data={})]
        mocker.patch("tools.stats_api.requests.get", side_effect=responses)
        mock_sleep = mocker.patch("tools.stats_api.time.sleep")

        stats_api._cached_get("http://fake-url")

        mock_sleep.assert_called_once_with(10)  # documented default fallback
