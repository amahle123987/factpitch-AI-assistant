"""
Data-Analyst agent.

Fetches a team's match history and computes performance splits around a
given date (e.g. an injury date), returning summary stats and a chart.
Also attaches opponent-strength context (current league standing position)
so a change in win rate can be read alongside whether the opponents faced
got tougher or easier.
"""

import os
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")  # headless — no display needed
import matplotlib.pyplot as plt
import pandas as pd
import requests

import config
from tools import stats_api

# Competitions we've already tried to fetch standings for and failed
# (e.g. knockout cups have no league table). Avoids repeat failed lookups
# and repeat warning spam within a single run.
_STANDINGS_UNAVAILABLE: set[str] = set()


def _matches_to_df(matches: list[dict], team_id: int) -> pd.DataFrame:
    rows = []
    for m in matches:
        home = m["homeTeam"]["id"] == team_id
        team_score = m["score"]["fullTime"]["home"] if home else m["score"]["fullTime"]["away"]
        opp_score = m["score"]["fullTime"]["away"] if home else m["score"]["fullTime"]["home"]

        if team_score is None or opp_score is None:
            continue  # skip matches without a final score

        if team_score > opp_score:
            result = "W"
        elif team_score < opp_score:
            result = "L"
        else:
            result = "D"

        opponent_team = m["awayTeam"] if home else m["homeTeam"]

        rows.append({
            "date": m["utcDate"][:10],
            "opponent": opponent_team.get("name", "Unknown"),
            "opponent_id": opponent_team.get("id"),
            "competition_code": (m.get("competition") or {}).get("code", ""),
            "home": home,
            "goals_for": team_score,
            "goals_against": opp_score,
            "result": result,
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
    return df


def _standings_table(competition_code: str) -> dict[int, dict]:
    """
    Fetch current standings for a competition and return the full TOTAL-table
    row for each team, keyed by team id — e.g. {57: {"position": 3, "won": 10,
    "draw": 2, "lost": 1, "goalsFor": 30, "goalsAgainst": 12,
    "goalDifference": 18, "points": 32, "playedGames": 13}, ...}.

    Returns {} (and remembers the failure for this run) if the competition
    has no standings — e.g. knockout cups like the League Cup or FA Cup
    don't have a league table on football-data.org.
    """
    if not competition_code or competition_code in _STANDINGS_UNAVAILABLE:
        return {}

    try:
        data = stats_api.get_standings(competition_code)
    except requests.HTTPError:
        print(f"[data_analyst] No standings available for competition '{competition_code}' "
              f"(likely a cup/knockout competition) — opponent strength will be skipped for it.")
        _STANDINGS_UNAVAILABLE.add(competition_code)
        return {}

    table = {}
    for group in data.get("standings", []):
        if group.get("type") != "TOTAL":
            continue
        for row in group.get("table", []):
            table[row["team"]["id"]] = row
        break  # only need the TOTAL table, not HOME/AWAY splits

    if not table:
        _STANDINGS_UNAVAILABLE.add(competition_code)

    return table


def _standings_position_map(competition_code: str) -> dict[int, int]:
    """{team_id: position} for a competition — thin view over _standings_table."""
    return {team_id: row["position"] for team_id, row in _standings_table(competition_code).items()}


def get_headline_stats(team_id: int, competition_code: str) -> dict | None:
    """
    Current league-standing headline numbers for a team: position, record,
    goal difference, points. Returns None if unavailable — e.g. the
    competition has no league table (a cup), or the team isn't in it.

    Like opponent-strength context elsewhere in this module, this reflects
    CURRENT standings, not a historical snapshot.
    """
    row = _standings_table(competition_code).get(team_id)
    if not row:
        return None

    return {
        "position": row.get("position"),
        "played": row.get("playedGames"),
        "won": row.get("won"),
        "draw": row.get("draw"),
        "lost": row.get("lost"),
        "goals_for": row.get("goalsFor"),
        "goals_against": row.get("goalsAgainst"),
        "goal_difference": row.get("goalDifference"),
        "points": row.get("points"),
    }


def _attach_opponent_positions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds an 'opponent_position' column (current league standing of each
    opponent, or NaN where unavailable — e.g. cup matches, or a competition
    without a standings table).

    NOTE: this reflects each opponent's CURRENT standing, not their standing
    at the time the match was played — the free-tier API doesn't expose
    historical standings snapshots. Treat it as a rough proxy, not a precise
    strength-of-schedule measure.
    """
    df = df.copy()
    position_by_code = {
        code: _standings_position_map(code) for code in df["competition_code"].unique()
    }

    def lookup(row):
        return position_by_code.get(row["competition_code"], {}).get(row["opponent_id"])

    df["opponent_position"] = df.apply(lookup, axis=1)
    return df


def _summarize(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"matches": 0}

    summary = {
        "matches": len(df),
        "wins": int((df["result"] == "W").sum()),
        "draws": int((df["result"] == "D").sum()),
        "losses": int((df["result"] == "L").sum()),
        "win_rate": float(round((df["result"] == "W").mean() * 100, 1)),
        "avg_goals_for": float(round(df["goals_for"].mean(), 2)),
        "avg_goals_against": float(round(df["goals_against"].mean(), 2)),
    }

    if "opponent_position" in df.columns:
        known = df["opponent_position"].dropna()
        if len(known) > 0:
            summary["avg_opponent_position"] = float(round(known.mean(), 1))
            summary["opponent_position_coverage"] = f"{len(known)}/{len(df)} matches"
            summary["opponent_position_note"] = (
                "Opponent positions are CURRENT league standings, not standings "
                "at the time each match was played — treat as an approximation."
            )

    return summary


def _compute_rolling_series(df: pd.DataFrame, window: int = 5) -> list[dict]:
    """
    Trailing rolling win rate across the full match sequence (both sides of
    the pivot together, in chronological order) — the basis for the "form
    over time" chart. Uses min_periods=1 so early matches still get a
    (noisier) value rather than starting blank.

    Returns a list of per-match points:
        [{"date": "YYYY-MM-DD", "opponent": str, "result": "W"|"D"|"L",
          "rolling_win_rate": float}, ...]
    """
    if df.empty:
        return []

    is_win = (df["result"] == "W").astype(float)
    rolling = is_win.rolling(window=window, min_periods=1).mean() * 100

    return [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "opponent": row["opponent"],
            "result": row["result"],
            "rolling_win_rate": float(round(rolling.iloc[i], 1)),
        }
        for i, row in df.iterrows()
    ]


def analyze_before_after(team_id: int, pivot_date: str, window_days: int = 60) -> dict:
    """
    Compare a team's form in the `window_days` before and after `pivot_date`
    (format 'YYYY-MM-DD'), e.g. around an injury or managerial change.

    Returns a dict with pre/post summary stats (including opponent-strength
    context where available), a match-by-match rolling win-rate series for
    charting, and the path to a saved chart.
    """
    pivot = datetime.strptime(pivot_date, "%Y-%m-%d")
    date_from = (pivot - timedelta(days=window_days)).strftime("%Y-%m-%d")
    date_to = (pivot + timedelta(days=window_days)).strftime("%Y-%m-%d")

    matches = stats_api.get_team_matches(team_id, date_from=date_from, date_to=date_to)
    df = _matches_to_df(matches, team_id)

    if df.empty:
        return {"error": "No finished matches found in this date range."}

    df = _attach_opponent_positions(df)

    pre = df[df["date"] < pivot]
    post = df[df["date"] >= pivot]

    result = {
        "pivot_date": pivot_date,
        "pre": _summarize(pre),
        "post": _summarize(post),
        "series": _compute_rolling_series(df),
        "chart_path": None,
    }

    result["chart_path"] = _make_chart(pre, post, pivot_date)
    return result


def _make_chart(pre: pd.DataFrame, post: pd.DataFrame, pivot_date: str) -> str:
    """
    Styled to match Streamlit's dark theme (the app this chart is embedded
    in) rather than matplotlib's default white background, which looked
    like a broken image dropped into a dark UI.
    """
    os.makedirs(config.CHART_OUTPUT_DIR, exist_ok=True)
    path = os.path.join(config.CHART_OUTPUT_DIR, "before_after_chart.png")

    BG = "#0e1117"        # Streamlit's default dark background
    FG = "#fafafa"        # Streamlit's default light text
    GRID = "#31333f"      # subtle gridline color that doesn't fight the bars
    COLORS = {"W": "#4caf50", "D": "#9aa0a6", "L": "#ef5350"}  # brightened for dark bg

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), facecolor=BG)

    for ax, df, label in zip(axes, [pre, post], ["Before", "After"]):
        ax.set_facecolor(BG)
        counts = df["result"].value_counts().reindex(["W", "D", "L"], fill_value=0)
        ax.bar(counts.index, counts.values, color=[COLORS[k] for k in counts.index])
        ax.set_title(f"{label} {pivot_date}", color=FG, fontsize=11)
        ax.set_ylabel("Matches", color=FG)
        ax.tick_params(colors=FG)
        ax.grid(axis="y", color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_color(GRID)

    fig.suptitle("Results split: before vs. after", color=FG, fontsize=13)
    fig.tight_layout()
    fig.savefig(path, dpi=120, facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


if __name__ == "__main__":
    example = analyze_before_after(config.DEFAULT_TEAM_ID, "2025-01-01")
    print(example)
