"""
CLI entry point for the Sports Performance & News Analyst.

Usage:
    python main.py "Recent injury news for Arsenal FC's captain"
    python main.py --days 120 "Recent injury news for Arsenal FC's captain"
    python main.py --team "Liverpool FC" "Recent injury news for the captain"
    python main.py --team "United" --competition PL "Recent news"
"""

import sys

import config
from agents import orchestrator
from tools import team_lookup


def _extract_flag(args: list[str], flag: str) -> tuple[str | None, list[str]]:
    """
    Pull a `--flag value` pair out of args (can appear anywhere), returning
    (value, remaining_args). Returns (None, args) unchanged if the flag
    isn't present. Exits with a usage message if the flag has no value.
    """
    if flag not in args:
        return None, args

    idx = args.index(flag)
    if idx + 1 >= len(args):
        print(f"Usage: {flag} requires a value")
        sys.exit(1)

    value = args[idx + 1]
    remaining = args[:idx] + args[idx + 2:]
    return value, remaining


def main():
    args = sys.argv[1:]

    days_str, args = _extract_flag(args, "--days")
    team_query, args = _extract_flag(args, "--team")
    competition, args = _extract_flag(args, "--competition")

    window_days = 60
    if days_str is not None:
        try:
            window_days = int(days_str)
        except ValueError:
            print("Usage: python main.py [--days N] \"your query\"")
            sys.exit(1)

    # Resolve which team to use: --team flag takes priority, else config default.
    if team_query:
        resolved = team_lookup.resolve_team(team_query, competition)
        if not resolved:
            sys.exit(1)  # team_lookup already printed why (not found / ambiguous)
        team_id, team_name = resolved["id"], resolved["name"]
    else:
        team_id, team_name = config.DEFAULT_TEAM_ID, config.DEFAULT_TEAM_NAME

    query = " ".join(args) or f"Recent significant news for {team_name}"

    print(f"\nTeam: {team_name}\nQuery: {query}\nWindow: \u00b1{window_days} days\n{'-' * 60}")
    result = orchestrator.run(
        team_id=team_id,
        team_name=team_name,
        event_query=query,
        window_days=window_days,
    )

    print("\n=== News Summary ===")
    print(result["news"].get("summary", "(no summary)"))
    for event in result["news"].get("key_events", []):
        print(f"  - {event.get('date')}: {event.get('headline')}")

    if result["stats"]:
        print("\n=== Performance Split ===")
        print("Before:", result["stats"].get("pre"))
        print("After: ", result["stats"].get("post"))
        if result["stats"].get("chart_path"):
            print(f"Chart saved to: {result['stats']['chart_path']}")

    print("\n=== Validator Verdict ===")
    print(result["verdict"])


if __name__ == "__main__":
    main()
