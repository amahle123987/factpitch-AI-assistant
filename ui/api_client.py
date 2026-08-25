"""
Thin HTTP client for the FastAPI backend (api/main.py). Keeps ui/app.py
free of raw `requests` calls and SSE-parsing details, and gives the UI a
small, easily-mocked surface for tests — mirrors how tools/stats_api.py
wraps football-data.org for the rest of the project.

Configure the backend's location with the API_BASE_URL environment
variable; defaults to http://localhost:8000 for local development.
"""

import json
import os
from typing import Callable, Optional

import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


class ApiError(Exception):
    """Raised when the backend can't be reached or returns an error."""


def get_competitions() -> list[dict]:
    try:
        r = requests.get(f"{API_BASE_URL}/competitions", timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        raise ApiError(f"Could not reach the API at {API_BASE_URL}: {exc}") from exc


def get_teams(competition: Optional[str] = None) -> list[dict]:
    try:
        params = {"competition": competition} if competition else {}
        r = requests.get(f"{API_BASE_URL}/teams", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        raise ApiError(f"Could not reach the API at {API_BASE_URL}: {exc}") from exc


def get_crest(team_id: int) -> Optional[str]:
    """Never raises — a missing crest shouldn't block the page."""
    try:
        r = requests.get(f"{API_BASE_URL}/teams/{team_id}/crest", timeout=10)
        r.raise_for_status()
        return r.json().get("crest_url")
    except requests.RequestException:
        return None


def get_headline_stats(team_id: int, competition: str) -> Optional[dict]:
    """
    Current league-standing headline numbers for a team, or None if
    unavailable (e.g. a cup competition, or a request the backend can't
    fulfill) — never raises, since this is supplementary context for the
    hero section, not something that should block the page.
    """
    try:
        r = requests.get(
            f"{API_BASE_URL}/teams/{team_id}/headline", params={"competition": competition}, timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        return data if data.get("available") else None
    except requests.RequestException:
        return None


def run_analysis(
    team_id: int,
    team_name: str,
    query: str,
    window_days: int,
    on_progress: Optional[Callable[[str], None]] = None,
) -> dict:
    """
    Calls the streaming /analyze/stream endpoint, invoking on_progress for
    each stage as it arrives, and returns the final result dict once the
    stream completes. Raises ApiError if the backend can't be reached, the
    pipeline itself fails, or the stream ends without ever sending a result.
    """
    payload = {"team_id": team_id, "team_name": team_name, "query": query, "window_days": window_days}
    try:
        response = requests.post(
            f"{API_BASE_URL}/analyze/stream", json=payload, stream=True, timeout=180,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ApiError(f"Could not reach the API at {API_BASE_URL}: {exc}") from exc

    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line or not raw_line.startswith("data: "):
            continue
        event = json.loads(raw_line[len("data: "):])

        if event["type"] == "progress" and on_progress:
            on_progress(event["stage"])
        elif event["type"] == "result":
            return event["result"]
        elif event["type"] == "error":
            raise ApiError(f"Analysis failed: {event['detail']}")

    raise ApiError("Stream ended without a result — the backend may have crashed mid-request.")
