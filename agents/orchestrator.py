"""
Orchestrator.

Coordinates the Web-Researcher, Data-Analyst, and Validator agents to
answer a "how has the team performed since X" style query end to end.
"""

import re

from agents import data_analyst, validator, web_researcher
from datetime import datetime

# Matches a year-month with an unknown day, e.g. "2025-08-??" or "2025-08".
_APPROX_DATE_RE = re.compile(r"^(\d{4})-(\d{2})(?:-\?\?)?$")
_APPROX_DAY = 15  # placeholder day used when only year+month is known


def run(team_id: int, team_name: str, event_query: str, window_days: int = 60, on_progress=None) -> dict:
    """
    Full pipeline for a query like:
        "How has {team_name} performed since {event}?"

    `event_query` is a natural-language description passed to the web
    researcher, e.g. "recent injury news for Arsenal FC's captain".

    `on_progress`, if given, is called with a short human-readable string at
    each major pipeline stage — e.g. for driving a live progress UI. It's
    purely observational: the pipeline runs identically whether or not it's
    provided. Defaults to printing to the console (the original behavior).
    """
    notify = on_progress or (lambda stage: print(f"[Orchestrator] {stage}"))

    # Make sure the team name is always part of the query, so the researcher
    # never has to guess which team/player "the captain", "he", etc. refers to.
    if team_name.lower() not in event_query.lower():
        event_query = f"{event_query} ({team_name})"

    notify(f"Researching: {event_query}")
    news = web_researcher.research(event_query)

    if not news.get("key_events"):
        notify("No dated events found in the news — stopping here.")
        return {
            "news": news,
            "stats": None,
            "verdict": "Could not find a specific dated event to analyze against — try a more specific query.",
        }

    pivot_date = _select_pivot_date(news, notify)
    if not pivot_date:
        notify("Found news, but nothing had a usable date — stopping here.")
        return {
            "news": news,
            "stats": None,
            "verdict": "Found news, but no event had a usable date to pivot the analysis on — try a more specific query.",
        }

    notify(f"Pulling match data and computing performance around {pivot_date}")
    stats = data_analyst.analyze_before_after(team_id, pivot_date, window_days=window_days)

    notify("Validating the narrative against the numbers")
    verdict = validator.validate(news, stats)

    notify("Done")
    return {"news": news, "stats": stats, "verdict": verdict}


def _select_pivot_date(news: dict, notify=print) -> str | None:
    """
    Pick a pivot date, preferring precision in this order:
      1. news["primary_event"] with a fully-specified date
      2. news["primary_event"] with only year+month known (approximated)
      3. the earliest fully-specified date among key_events
      4. the earliest year+month-only date among key_events (approximated)
    Returns None only if nothing in the news has a usable date at all.
    """
    primary = news.get("primary_event") or {}
    parsed = _parse_date(primary.get("date", ""))
    if parsed:
        date_str, is_approx = parsed
        precision = "approximate (day assumed)" if is_approx else "exact"
        notify(f"Using primary event: {primary.get('headline')} "
               f"({primary.get('reason', 'no reason given')}) — {precision} date {date_str}")
        return date_str

    exact_dates, approx_dates = [], []
    for e in news["key_events"]:
        result = _parse_date(e["date"])
        if not result:
            continue
        date_str, is_approx = result
        (approx_dates if is_approx else exact_dates).append(date_str)

    if exact_dates:
        notify("No usable primary_event — falling back to earliest exact-dated event")
        return min(exact_dates)

    if approx_dates:
        chosen = min(approx_dates)
        notify(f"No usable primary_event or exact date — falling back to "
               f"earliest approximate event, day assumed as the {_APPROX_DAY}th: {chosen}")
        return chosen

    return None


def _parse_date(value: str) -> tuple[str, bool] | None:
    """
    Try to interpret `value` as a date, returning (YYYY-MM-DD, is_approximate)
    or None if it isn't usable at all.

    - A fully-specified date like "2026-02-22" returns (value, False).
    - A year+month with an unknown day, like "2025-08-??" or "2025-08",
      returns a date with the day filled in as _APPROX_DAY and (.., True).
    - Anything else (garbage, missing, wrong shape) returns None.
    """
    if not value:
        return None

    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value, False
    except (TypeError, ValueError):
        pass

    match = _APPROX_DATE_RE.match(value)
    if match:
        year, month = match.groups()
        try:
            approx = datetime(int(year), int(month), _APPROX_DAY)
            return approx.strftime("%Y-%m-%d"), True
        except ValueError:
            return None  # invalid month, e.g. "2025-13"

    return None


def _looks_like_date(value: str) -> bool:
    """Kept for backward compatibility — True for exact dates only."""
    return _parse_date(value) is not None and not _parse_date(value)[1]


if __name__ == "__main__":
    import config
    import json

    result = run(
        team_id=config.DEFAULT_TEAM_ID,
        team_name=config.DEFAULT_TEAM_NAME,
        event_query=f"Recent significant injury news for {config.DEFAULT_TEAM_NAME}",
    )
    print(json.dumps(result, indent=2, default=str))
