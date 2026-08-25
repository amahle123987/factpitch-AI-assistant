"""
Thin wrapper around the football-data.org v4 API, with a simple SQLite
cache so repeated runs don't burn your 10-requests/minute free-tier quota.
"""

import json
import sqlite3
import time
from datetime import datetime, timedelta

import requests

import config

_HEADERS = {"X-Auth-Token": config.FOOTBALL_DATA_API_KEY}

# How long a cached response stays valid before we re-fetch.
_CACHE_TTL = timedelta(hours=6)


def _get_db():
    conn = sqlite3.connect(config.CACHE_DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            fetched_at TEXT,
            payload TEXT
        )"""
    )
    return conn


def _cached_get(url: str, params: dict | None = None, ttl: timedelta = _CACHE_TTL) -> dict:
    """GET a URL, transparently caching the JSON response in SQLite."""
    key = url + json.dumps(params or {}, sort_keys=True)
    conn = _get_db()
    row = conn.execute("SELECT fetched_at, payload FROM cache WHERE key = ?", (key,)).fetchone()

    if row:
        fetched_at = datetime.fromisoformat(row[0])
        if datetime.now() - fetched_at < ttl:
            conn.close()
            return json.loads(row[1])

    resp = requests.get(url, headers=_HEADERS, params=params, timeout=15)

    attempts = 0
    while resp.status_code == 429 and attempts < 3:
        # Respect the API's own Retry-After header when it sends one;
        # otherwise fall back to a conservative fixed wait.
        wait_seconds = int(resp.headers.get("Retry-After", 10))
        print(f"[stats_api] Rate limited, waiting {wait_seconds}s before retry "
              f"({attempts + 1}/3)...")
        time.sleep(wait_seconds)
        resp = requests.get(url, headers=_HEADERS, params=params, timeout=15)
        attempts += 1

    resp.raise_for_status()
    payload = resp.json()

    conn.execute(
        "INSERT OR REPLACE INTO cache (key, fetched_at, payload) VALUES (?, ?, ?)",
        (key, datetime.now().isoformat(), json.dumps(payload)),
    )
    conn.commit()
    conn.close()
    return payload


def get_team_matches(team_id: int, date_from: str | None = None, date_to: str | None = None,
                      status: str = "FINISHED") -> list[dict]:
    """
    Fetch a team's matches. Dates are 'YYYY-MM-DD' strings.
    Returns a list of match dicts (raw football-data.org shape).
    """
    url = f"{config.FOOTBALL_DATA_BASE_URL}/teams/{team_id}/matches"
    params = {"status": status}
    if date_from:
        params["dateFrom"] = date_from
    if date_to:
        params["dateTo"] = date_to

    data = _cached_get(url, params)
    return data.get("matches", [])


def get_team_info(team_id: int) -> dict:
    url = f"{config.FOOTBALL_DATA_BASE_URL}/teams/{team_id}"
    return _cached_get(url)


def get_standings(competition_code: str) -> dict:
    url = f"{config.FOOTBALL_DATA_BASE_URL}/competitions/{competition_code}/standings"
    return _cached_get(url)


def get_competition_teams(competition_code: str) -> dict:
    """
    List all teams in a competition. Cached for a week rather than the usual
    6 hours, since team rosters in a league barely change day to day —
    keeps team-name searches fast and well within the free-tier rate limit.
    """
    url = f"{config.FOOTBALL_DATA_BASE_URL}/competitions/{competition_code}/teams"
    return _cached_get(url, ttl=timedelta(days=7))
