# FactPitch

![Tests](https://github.com/amahle123987/factpitch/actions/workflows/tests.yml/badge.svg)

*Your Form Guide, Verified.*

A personal project: an agent-based assistant that connects sports news
(injuries, transfers, commentary) with what the underlying performance data
actually shows.

## Design

"Press-box dossier" visual direction — a tactics-board / matchday-dossier
feel rather than a generic dashboard. Deep pitch-night green-black palette,
one disciplined gold accent reserved for the Validator's verdict, **Bebas
Neue** for headers and stat labels (classic stadium-scoreboard type),
**Inter** for body text, **IBM Plex Mono** for tabular stat digits. Full
token/rationale details are in the docstring at the top of `ui/app.py`.

## Architecture

- **Orchestrator** (`agents/orchestrator.py`) — runs the pipeline end to end
- **Web-Researcher** (`agents/web_researcher.py`) — two-step: OpenAI's
  Responses API + built-in web search tool gathers raw research notes, then
  a LangChain-wrapped model extracts them into a validated `NewsResearch`
  schema (`agents/schemas.py`) via OpenAI's Structured Outputs API — no more
  manual JSON-fence-stripping or `try/except json.JSONDecodeError`
- **Data-Analyst** (`agents/data_analyst.py`) — pulls match data from
  football-data.org, computes before/after performance splits, attaches
  opponent-strength context (current league standing of each opponent
  faced), computes a trailing-5-match rolling win-rate series for the
  "Form Over Time" chart, and exposes `get_headline_stats()` (current
  league position, record, and goal difference from the standings table)
- **Validator** (`agents/validator.py`) — checks whether the stats actually
  back up the news narrative, factoring in opponent strength where available

The Orchestrator's `run()` accepts an optional `on_progress` callback,
called with a short string at each pipeline stage. `main.py` doesn't use
it (prints to console by default); the API's streaming endpoint (below)
uses it to drive live progress in the UI.

## Two client surfaces

- **FastAPI backend** (`api/main.py`) — the pipeline lives here.
  `GET /health`, `GET /competitions`, `GET /teams?competition=PL`,
  `GET /teams/{id}/crest`, `GET /teams/{id}/headline?competition=PL`
  (current league position/record/goal difference), `POST /analyze`
  (single JSON response), `POST /analyze/stream` (Server-Sent Events —
  live per-stage progress).
- **Streamlit UI** (`ui/app.py`) — a pure HTTP client of the API above,
  via `ui/api_client.py`. It no longer imports `agents`/`tools`/`config`
  directly at all — everything goes over HTTP.

**Both processes must be running for the UI to work.** In one terminal:
```bash
uvicorn api.main:app --reload
```
In a second terminal (same venv):
```bash
streamlit run ui/app.py
```
If the API isn't reachable, the UI shows a clear error in the sidebar
(with the command to start it) instead of crashing — team selection and
the Analyze button stay disabled until the connection succeeds.

The UI's `st.status` live progress works across the HTTP boundary via
`/analyze/stream`'s Server-Sent Events: the Orchestrator's `on_progress`
callback fires inside the API process, gets pushed onto a queue drained by
a background thread, and streamed to the browser as SSE —
`ui/api_client.run_analysis()` parses that stream and re-invokes
`on_progress` locally, so the Streamlit rendering code didn't need to change
at all when this was wired up.

By default the UI looks for the API at `http://localhost:8000` — override
with the `API_BASE_URL` environment variable if you're running it
elsewhere.

### A note on opponent strength

`avg_opponent_position` reflects each opponent's **current** league
standing, not their standing at the time the match was actually played —
the free-tier API doesn't expose historical standings snapshots. It's a
useful rough signal (e.g. "the after-period opponents were much
higher-ranked, so a lower win rate isn't necessarily a real decline") but
not a rigorous strength-of-schedule metric. Cup/knockout matches (no
league table) are automatically skipped and won't appear in the coverage
count. The same caveat applies to the hero section's headline metrics
(league position, record, goal difference) — they're the team's *current*
standing, fetched fresh each time a team is selected, not a snapshot tied
to any particular query.

## UI layout

Results are organized into three tabs rather than one long scroll:
**Overview** (verdict, the pivot event, and win-rate-before/after metrics),
**Performance Trends** (the rolling win-rate chart with a marker at the
pivot date, the before/after split cards, the results chart, and opponent
strength), and **News & Timeline** (every event as its own card, with the
pivot event visually distinguished).

The competition dropdown shows clean league names only (e.g. "Premier
League," not "PL — Premier League") — pick one first to scope the team
dropdown, which is a searchable combobox (type a letter to filter). The
browser tab uses a ⚽ favicon; the hero shows the selected team's crest
(or a letter-badge fallback if the crest can't be fetched) alongside
current headline stats — league position, record, and goal difference —
the moment a team is picked, before you've typed a query. Clicking
Analyze shows live progress as each agent runs (research → pivot
selection → stats → validation), rather than a single opaque spinner.

## Setup

1. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Get your API keys**
   - OpenAI API key: https://platform.openai.com/api-keys
   - football-data.org free key: https://www.football-data.org/client/register
     (takes ~2 minutes; free tier covers 12 major competitions, 10 requests/min)

3. **Configure**
   ```bash
   cp .env.example .env
   # then edit .env and paste in your keys
   ```

4. **Set your team/competition** in `config.py`. To find a team's ID, call:
   ```bash
   curl "https://api.football-data.org/v4/competitions/PL/teams" \
     -H "X-Auth-Token: YOUR_KEY"
   ```
   and look up the `id` field for your team.

## Running it

**CLI:**
```bash
python main.py "Recent injury news for the captain"
```

By default this uses the team set in `config.py` (`DEFAULT_TEAM_ID` /
`DEFAULT_TEAM_NAME`). To point it at a different team without editing
`config.py`, use `--team`:

```bash
python main.py --team "Liverpool FC" "Recent injury news for the captain"
```

`--team` does a name search across all 12 supported free-tier competitions
(see `SUPPORTED_COMPETITIONS` in `config.py`) and caches each competition's
team list for a week, so repeated lookups are fast and don't burn API calls.
If the name matches more than one distinct team, it'll print the candidates
so you can narrow it down — either with a more specific name, or by adding
`--competition`:

```bash
python main.py --team "United" --competition PL "Recent news"
```

Combine with `--days` freely, in any order:

```bash
python main.py --team "Liverpool FC" --days 120 "Recent injury news"
```

**Streamlit UI:**
```bash
streamlit run ui/app.py
```
Requires the FastAPI backend running too — see "Two client surfaces" above.
See "UI layout" above for how team/competition selection and the results
tabs work.

## Running the tests

The project has a pytest suite covering the trickiest logic — pivot-date
selection, match/stats computation, team-name lookup and deduplication,
cache/retry behavior, CLI flag parsing, the LangChain-backed news
extraction, every FastAPI endpoint (including the SSE streaming one), the
`ui/api_client` HTTP layer, and the Streamlit UI's rendering behavior via
`AppTest`. No real API keys or network access needed; everything external
is mocked.

```bash
pip install -r requirements-dev.txt
pytest -v
```

## Notes on the free tier

- football-data.org's free tier only covers 12 competitions and has delayed
  (not live) scores — fine for this kind of historical/reflective analysis.
- Responses are cached in `data/cache.db` for 6 hours to stay well within the
  10 requests/minute limit.

## Next steps / ideas to extend

- Swap the pivot-date logic to let you compare around *any* date (managerial
  change, transfer window close, etc.), not just injuries
- Add a second data source for competitions outside the free 12
  (e.g. API-Football) and merge results
- Track your own prompting/debugging effort in `logs/` if you want to keep
  the "entropy" reflection habit from the group project