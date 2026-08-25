"""
Team lookup by name across football-data.org's supported free-tier
competitions, so you don't have to manually curl and copy IDs by hand
every time you want to point the analyst at a different team.
"""

import config
from tools import stats_api


def find_team(name_query: str, competition: str | None = None) -> list[dict]:
    """
    Search for teams whose name/shortName/TLA contains `name_query`
    (case-insensitive), optionally restricted to one competition code.

    Returns a list of matches: [{"id": int, "name": str, "competition": str}, ...]
    Each competition's team list is cached (via stats_api's existing cache),
    so repeated searches don't burn API calls.
    """
    competitions = [competition] if competition else list(config.SUPPORTED_COMPETITIONS)
    query = name_query.strip().lower()
    matches = []

    for comp_code in competitions:
        try:
            data = stats_api.get_competition_teams(comp_code)
        except Exception as exc:  # noqa: BLE001 — surface but keep searching other leagues
            print(f"[team_lookup] Skipping {comp_code}: {exc}")
            continue

        for team in data.get("teams", []):
            haystacks = [team.get("name", ""), team.get("shortName", ""), team.get("tla", "")]
            if any(query in h.lower() for h in haystacks if h):
                matches.append({
                    "id": team["id"],
                    "name": team["name"],
                    "competition": comp_code,
                })

    return matches


def resolve_team(name_query: str, competition: str | None = None) -> dict | None:
    """
    Convenience wrapper for the common case: find exactly one team and
    return it, or None with an explanatory print if the match is ambiguous
    or not found. Intended for CLI use.
    """
    matches = find_team(name_query, competition)

    if not matches:
        print(f"[team_lookup] No team found matching '{name_query}'"
              + (f" in {competition}" if competition else " across supported competitions"))
        return None

    if len(matches) > 1:
        # De-duplicate teams that appear in more than one competition (e.g. cup + league)
        seen_ids = set()
        unique = []
        for m in matches:
            if m["id"] not in seen_ids:
                seen_ids.add(m["id"])
                unique.append(m)

        if len(unique) > 1:
            print(f"[team_lookup] Multiple teams match '{name_query}':")
            for m in unique:
                comp_name = config.SUPPORTED_COMPETITIONS.get(m["competition"], m["competition"])
                print(f"    - {m['name']} (id={m['id']}, {comp_name})")
            print("  Narrow it down with --competition, or use a more specific name.")
            return None
        matches = unique

    return matches[0]


def list_teams(competition: str | None = None) -> list[dict]:
    """
    Return every team for one competition, or across all supported
    competitions if `competition` is None — sorted alphabetically and
    de-duplicated by team id (a team can appear in more than one
    competition, e.g. league + Champions League).

    Returns: [{"id": int, "name": str, "competition": str}, ...]
    Intended for populating a dropdown/autocomplete rather than
    substring search — see find_team()/resolve_team() for that.
    """
    competitions = [competition] if competition else list(config.SUPPORTED_COMPETITIONS)
    seen_ids = set()
    teams = []

    for comp_code in competitions:
        try:
            data = stats_api.get_competition_teams(comp_code)
        except Exception as exc:  # noqa: BLE001 — surface but keep loading other leagues
            print(f"[team_lookup] Skipping {comp_code}: {exc}")
            continue

        for team in data.get("teams", []):
            team_id = team["id"]
            if team_id in seen_ids:
                continue
            seen_ids.add(team_id)
            teams.append({"id": team_id, "name": team["name"], "competition": comp_code})

    teams.sort(key=lambda t: t["name"])
    return teams


if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:]) or "Arsenal"
    result = resolve_team(query)
    print(result)