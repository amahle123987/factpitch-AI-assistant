"""
Shared pytest fixtures.

Sets fake API keys before any project module is imported, since config.py
raises at import time if OPENAI_API_KEY / FOOTBALL_DATA_API_KEY are missing.
This lets the whole suite run without real credentials or network access —
every external call (OpenAI, football-data.org) is mocked in the tests
themselves.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key-not-real")
os.environ.setdefault("FOOTBALL_DATA_API_KEY", "test-key-not-real")

import pytest


@pytest.fixture
def mock_db(mocker):
    """
    Patches tools.stats_api._get_db so tests never touch the real
    data/cache.db file, and every query is a guaranteed cache miss unless
    a test explicitly sets up a row.
    """
    conn = mocker.MagicMock()
    conn.execute.return_value.fetchone.return_value = None
    mocker.patch("tools.stats_api._get_db", return_value=conn)
    return conn
