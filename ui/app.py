"""
Streamlit UI for the Sports Performance & News Analyst.

Design direction: "press-box dossier" — a tactics-board / matchday-dossier
feel rather than a generic dashboard. See README.md for the full token
rationale if you want to adjust the palette.

Run with: streamlit run ui/app.py
(Run from the project root so imports resolve correctly.)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import plotly.graph_objects as go
import streamlit as st

from ui import api_client

st.set_page_config(page_title="FactPitch", page_icon="⚽", layout="centered")

# --- Design tokens -------------------------------------------------------------
BG = "#0F1A14"
PANEL = "#16241C"
PANEL_BORDER = "#26362C"
TEXT = "#F4F1E8"
TEXT_MUTED = "#9FB3A6"
ACCENT = "#E8B93F"
WIN = "#3FA34D"
DRAW = "#7A8A82"
LOSS = "#C1443C"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;500&family=IBM+Plex+Mono:wght@500;600&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
    }}

    .dossier-hero {{
        display: flex;
        align-items: center;
        gap: 20px;
        padding-bottom: 14px;
        border-bottom: 2px solid {ACCENT};
        margin-bottom: 28px;
    }}
    .dossier-hero img {{
        width: 56px;
        height: 56px;
        object-fit: contain;
    }}
    .dossier-hero-fallback {{
        width: 56px;
        height: 56px;
        border-radius: 50%;
        background: {PANEL};
        border: 2px solid {PANEL_BORDER};
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 26px;
        color: {TEXT_MUTED};
    }}
    .dossier-hero-fallback.letter {{
        font-family: 'Bebas Neue', sans-serif;
        font-size: 24px;
    }}
    .dossier-hero h1 {{
        font-family: 'Bebas Neue', sans-serif;
        font-weight: 700;
        font-size: 34px;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        color: {TEXT};
        margin: 0;
        line-height: 1.1;
    }}
    .dossier-hero p {{
        font-family: 'Inter', sans-serif;
        color: {TEXT_MUTED};
        margin: 4px 0 0 0;
        font-size: 14px;
    }}

    .eyebrow {{
        font-family: 'Bebas Neue', sans-serif;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: {ACCENT};
        margin-bottom: 6px;
    }}

    .timeline-date {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12px;
        color: {TEXT_MUTED};
        white-space: nowrap;
    }}
    .timeline-headline {{
        font-size: 14px;
        color: {TEXT};
        margin-top: 2px;
    }}

    .news-card-icon {{
        font-size: 16px;
        color: {PANEL_BORDER};
        text-align: center;
        padding-top: 2px;
    }}
    .news-card-icon.primary {{
        color: {ACCENT};
    }}

    .split-label {{
        font-size: 12px;
        color: {TEXT_MUTED};
        margin-bottom: 2px;
    }}
    .split-stat {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 30px;
        font-weight: 600;
        color: {TEXT};
        line-height: 1.1;
    }}
    .split-sub {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 14px;
        color: {TEXT_MUTED};
        margin-top: 10px;
    }}

    .kickoff-badge {{
        text-align: center;
        font-family: 'Bebas Neue', sans-serif;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: {BG};
        background: {ACCENT};
        border-radius: 4px;
        padding: 6px 4px;
        margin: 8px 0;
    }}

    .verdict-text {{
        font-family: 'Inter', sans-serif;
        font-style: italic;
        font-size: 16px;
        line-height: 1.55;
        color: {TEXT};
        margin: 0;
    }}

    .opponent-note {{
        font-size: 12px;
        color: {TEXT_MUTED};
        margin-top: 10px;
        line-height: 1.5;
    }}
</style>
""", unsafe_allow_html=True)


# --- Sidebar: team selection -------------------------------------------------
NO_TEAM_SELECTED = "— Select a team —"


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_competitions():
    return api_client.get_competitions()


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_team_list(competition_code):
    return api_client.get_teams(competition_code or None)


api_unreachable = False

with st.sidebar:
    st.markdown('<div class="eyebrow">Team</div>', unsafe_allow_html=True)

    try:
        competitions = _cached_competitions()
        competition_names = {c["code"]: c["name"] for c in competitions}
    except api_client.ApiError as exc:
        api_unreachable = True
        competition_names = {}
        st.error(f"Can't reach the API backend.\n\n{exc}\n\n"
                 f"Start it with: `uvicorn api.main:app --reload`")

    competition = st.selectbox(
        "Restrict to a competition (optional)",
        options=[""] + list(competition_names.keys()),
        format_func=lambda code: "Any competition" if code == "" else competition_names[code],
        help="Narrowing to one league loads faster — 'Any' checks all 12 supported competitions.",
        disabled=api_unreachable,
    )

    available_teams = []
    if not api_unreachable:
        try:
            with st.spinner("Loading teams..."):
                available_teams = _cached_team_list(competition)
        except api_client.ApiError as exc:
            api_unreachable = True
            st.error(f"Can't reach the API backend.\n\n{exc}")

    team_options = [NO_TEAM_SELECTED] + [t["name"] for t in available_teams]
    selected_name = st.selectbox(
        "Search for a team",
        options=team_options,
        index=0,
        help="Start typing to filter — e.g. 'A' shows Arsenal, Aston Villa, etc.",
        label_visibility="collapsed",
        disabled=api_unreachable,
    )

    window_days = st.slider("Days before/after to compare", min_value=15, max_value=180, value=60, step=15)

# --- Resolve team --------------------------------------------------------------
team_id, team_name, team_competition, team_error = None, None, None, None

if selected_name != NO_TEAM_SELECTED:
    match = next((t for t in available_teams if t["name"] == selected_name), None)
    team_id, team_name, team_competition = match["id"], match["name"], match["competition"]

if team_error:
    st.sidebar.error(team_error)
elif team_name:
    st.sidebar.success(f"Team: {team_name}")
elif not api_unreachable:
    st.sidebar.info("Select a team above to get started.")

# --- Hero ------------------------------------------------------------------------
crest_url = api_client.get_crest(team_id) if team_id else None
headline = api_client.get_headline_stats(team_id, team_competition) if team_id and team_competition else None

if team_name:
    crest_html = (
        f'<img src="{crest_url}" alt="{team_name} crest" />'
        if crest_url else
        f'<div class="dossier-hero-fallback letter">{team_name[0]}</div>'
    )
    hero_title = team_name
    hero_subtitle = "Connects sports news to what the underlying performance data actually shows"
else:
    crest_html = '<div class="dossier-hero-fallback">\u26bd\ufe0f</div>'
    hero_title = "FactPitch"
    hero_subtitle = "Your Form Guide, Verified — select a team from the sidebar to get started"

st.markdown('<div class="eyebrow">FactPitch</div>', unsafe_allow_html=True)
st.markdown(f"""
<div class="dossier-hero">
    {crest_html}
    <div>
        <h1>{hero_title}</h1>
        <p>{hero_subtitle}</p>
    </div>
</div>
""", unsafe_allow_html=True)

if headline:
    gd = headline.get("goal_difference")
    gd_display = f"+{gd}" if isinstance(gd, int) and gd > 0 else str(gd)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("League Position", f"#{headline.get('position', '—')}")
    with col2:
        st.metric("Record", f"{headline.get('won', 0)}-{headline.get('draw', 0)}-{headline.get('lost', 0)}",
                   help="Wins-Draws-Losses this season")
    with col3:
        st.metric("Goal Difference", gd_display)
    st.caption(f"Current {competition_names.get(team_competition, team_competition)} standing "
               f"· {headline.get('points', '—')} points from {headline.get('played', '—')} games")

# --- Main query ------------------------------------------------------------------
query = st.text_input(
    "Ask about recent news and how it's shown up in performance",
    placeholder="e.g. Recent injury news for the captain",
    disabled=not team_id or api_unreachable,
)

analyze_clicked = st.button(
    "Analyze", disabled=bool(team_error) or not team_id or api_unreachable, type="primary",
)
if not team_id and not team_error and not api_unreachable:
    st.caption("Pick a team from the sidebar to enable analysis.")


def _rolling_chart(series: list[dict], pivot_date: str) -> go.Figure:
    dates = [p["date"] for p in series]
    rates = [p["rolling_win_rate"] for p in series]
    hover = [f"{p['date']} vs {p['opponent']} ({p['result']})" for p in series]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=rates, mode="lines+markers",
        line=dict(color=ACCENT, width=2),
        marker=dict(size=5, color=ACCENT),
        hovertext=hover, hoverinfo="text+y",
        showlegend=False,
    ))

    fig.add_vline(
        x=pivot_date, line_width=2, line_dash="dash", line_color=TEXT_MUTED,
        annotation_text=f"  {pivot_date}", annotation_position="top",
        annotation_font=dict(color=TEXT_MUTED, size=11, family="IBM Plex Mono, monospace"),
    )

    fig.update_layout(
        plot_bgcolor=PANEL,
        paper_bgcolor=PANEL,
        font=dict(family="IBM Plex Mono, monospace", color=TEXT, size=12),
        margin=dict(l=10, r=10, t=30, b=10),
        height=240,
        xaxis=dict(showgrid=False, tickfont=dict(color=TEXT_MUTED)),
        yaxis=dict(showgrid=True, gridcolor=PANEL_BORDER, tickfont=dict(color=TEXT_MUTED),
                   ticksuffix="%", range=[-5, 105]),
    )
    return fig


def _results_chart(pre: dict, post: dict) -> go.Figure:
    categories = ["Wins", "Draws", "Losses"]
    colors = [WIN, DRAW, LOSS]

    fig = go.Figure()
    for label, stats, opacity in [("Before", pre, 0.55), ("After", post, 1.0)]:
        fig.add_trace(go.Bar(
            name=label,
            x=categories,
            y=[stats.get("wins", 0), stats.get("draws", 0), stats.get("losses", 0)],
            marker=dict(color=colors, opacity=opacity, line=dict(width=0)),
            text=[stats.get("wins", 0), stats.get("draws", 0), stats.get("losses", 0)],
            textposition="outside",
            showlegend=False,
        ))

    fig.update_layout(
        barmode="group",
        plot_bgcolor=PANEL,
        paper_bgcolor=PANEL,
        font=dict(family="IBM Plex Mono, monospace", color=TEXT, size=12),
        margin=dict(l=10, r=10, t=30, b=10),
        height=260,
        xaxis=dict(showgrid=False, tickfont=dict(color=TEXT_MUTED)),
        yaxis=dict(showgrid=True, gridcolor=PANEL_BORDER, tickfont=dict(color=TEXT_MUTED)),
        annotations=[
            dict(text="BEFORE", x=0.18, y=1.12, xref="paper", yref="paper",
                 showarrow=False, font=dict(color=TEXT_MUTED, size=11, family="Bebas Neue, sans-serif")),
            dict(text="AFTER", x=0.82, y=1.12, xref="paper", yref="paper",
                 showarrow=False, font=dict(color=ACCENT, size=11, family="Bebas Neue, sans-serif")),
        ],
    )
    return fig


if analyze_clicked and query and team_id:
    with st.status("Starting analysis...", expanded=True) as status:
        def _progress(stage: str) -> None:
            status.write(stage)
            if stage.startswith("Researching"):
                status.update(label="Researching news...")
            elif stage.startswith("Pulling match data"):
                status.update(label="Crunching the numbers...")
            elif stage.startswith("Validating"):
                status.update(label="Validating the narrative against the data...")

        try:
            result = api_client.run_analysis(
                team_id=team_id,
                team_name=team_name,
                query=query,
                window_days=window_days,
                on_progress=_progress,
            )
        except api_client.ApiError as exc:
            status.update(label="Couldn't reach the API", state="error", expanded=True)
            st.error(str(exc))
            st.stop()

        if result["stats"] and "error" not in result["stats"]:
            status.update(label="Analysis complete", state="complete", expanded=False)
        elif result["stats"] is None:
            status.update(label="Couldn't complete — see notes below", state="error", expanded=True)
        else:
            status.update(label="Analysis complete (with a data caveat)", state="complete", expanded=False)

    st.markdown('<div class="eyebrow">News Summary</div>', unsafe_allow_html=True)
    st.write(result["news"].get("summary", "(no summary found)"))

    tab_overview, tab_trends, tab_news = st.tabs(["Overview", "Performance Trends", "News & Timeline"])

    primary_event = result["news"].get("primary_event") or {}
    primary_headline = primary_event.get("headline", "")
    key_events = result["news"].get("key_events", [])

    has_valid_stats = bool(result["stats"] and "error" not in result["stats"])
    pre, post, pivot = ({}, {}, "")
    if has_valid_stats:
        pre, post = result["stats"]["pre"], result["stats"]["post"]
        pivot = result["stats"].get("pivot_date", "")

    # --- Overview tab: the takeaway, front and center --------------------
    with tab_overview:
        st.markdown('<div class="eyebrow">Verdict</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(f'<p class="verdict-text">{result["verdict"]}</p>', unsafe_allow_html=True)

        if primary_event:
            st.markdown('<div class="eyebrow" style="margin-top: 20px;">Pivot Event</div>', unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown(f"""
                <div class="timeline-date">{primary_event.get('date', '')}</div>
                <div class="timeline-headline" style="font-size: 16px; margin-top: 4px;">{primary_event.get('headline', '')}</div>
                <div class="opponent-note" style="margin-top: 8px;">{primary_event.get('reason', '')}</div>
                """, unsafe_allow_html=True)

        if has_valid_stats:
            st.markdown('<div class="eyebrow" style="margin-top: 20px;">At a Glance</div>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Win rate before", f"{pre.get('win_rate', 0)}%")
            with col2:
                delta = round(post.get("win_rate", 0) - pre.get("win_rate", 0), 1)
                st.metric("Win rate after", f"{post.get('win_rate', 0)}%", delta=f"{delta}%")

    # --- Performance Trends tab: the full stats breakdown -----------------
    with tab_trends:
        if has_valid_stats:
            series = result["stats"].get("series", [])
            if series:
                st.markdown('<div class="eyebrow">Form Over Time</div>', unsafe_allow_html=True)
                st.plotly_chart(_rolling_chart(series, pivot), width="stretch", config={"displayModeBar": False})
                st.caption("Rolling win rate over a trailing 5-match window. Dashed line marks the pivot date.")

            col1, col2, col3 = st.columns([5, 2, 5])

            with col1:
                with st.container(border=True):
                    st.markdown(f"""
                    <div class="eyebrow">Before</div>
                    <div class="split-label">Win rate</div>
                    <div class="split-stat">{pre.get('win_rate', 0)}%</div>
                    <div class="split-sub">{pre.get('wins', 0)}W {pre.get('draws', 0)}D {pre.get('losses', 0)}L
                        &nbsp;·&nbsp; {pre.get('avg_goals_for', '—')} GF / {pre.get('avg_goals_against', '—')} GA</div>
                    """, unsafe_allow_html=True)

            with col2:
                st.markdown(f'<div class="kickoff-badge">{pivot}</div>', unsafe_allow_html=True)

            with col3:
                delta = round(post.get("win_rate", 0) - pre.get("win_rate", 0), 1)
                arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "—")
                with st.container(border=True):
                    st.markdown(f"""
                    <div class="eyebrow">After</div>
                    <div class="split-label">Win rate <span style="color:{WIN if delta > 0 else LOSS if delta < 0 else TEXT_MUTED}">{arrow} {abs(delta)}%</span></div>
                    <div class="split-stat">{post.get('win_rate', 0)}%</div>
                    <div class="split-sub">{post.get('wins', 0)}W {post.get('draws', 0)}D {post.get('losses', 0)}L
                        &nbsp;·&nbsp; {post.get('avg_goals_for', '—')} GF / {post.get('avg_goals_against', '—')} GA</div>
                    """, unsafe_allow_html=True)

            st.plotly_chart(_results_chart(pre, post), width="stretch", config={"displayModeBar": False})

            if "avg_opponent_position" in pre and "avg_opponent_position" in post:
                st.markdown(f"""
                <div class="opponent-note">
                    Avg opponent league position — before: <strong>{pre['avg_opponent_position']}</strong>,
                    after: <strong>{post['avg_opponent_position']}</strong>
                    (lower number = tougher opponent; based on <strong>current</strong> standings,
                    not standings at the time each match was played)
                </div>
                """, unsafe_allow_html=True)
        elif result["stats"] and "error" in result["stats"]:
            st.warning(result["stats"]["error"])
        else:
            st.info("No performance data to show — see the News & Timeline tab for what was found.")

    # --- News & Timeline tab: every event as its own card ------------------
    with tab_news:
        if not key_events:
            st.info("No dated events found for this query.")
        for event in key_events:
            is_primary = event.get("headline") == primary_headline
            with st.container(border=True):
                icon_col, text_col = st.columns([1, 11])
                with icon_col:
                    st.markdown(
                        f'<div class="news-card-icon{" primary" if is_primary else ""}">'
                        f'{"★" if is_primary else "●"}</div>',
                        unsafe_allow_html=True,
                    )
                with text_col:
                    st.markdown(f"""
                    <div class="timeline-date">{event.get('date', '')}</div>
                    <div class="timeline-headline">{event.get('headline', '')}</div>
                    """, unsafe_allow_html=True)
                    if event.get("detail"):
                        st.markdown(f'<div class="opponent-note">{event["detail"]}</div>', unsafe_allow_html=True)