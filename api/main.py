"""
FastAPI backend for the Sports Performance & News Analyst.

This wraps the same agents/tools the CLI (main.py) and Streamlit UI
(ui/app.py) already use — it's a second, independent client surface, not
a replacement for either. Run it with:

    uvicorn api.main:app --reload

Then see the auto-generated docs at http://localhost:8000/docs
"""

import json
import queue
import threading

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import config
from agents import data_analyst, orchestrator
from tools import stats_api, team_lookup

from api.schemas import AnalyzeRequest, AnalyzeResponse, CompetitionOut, HeadlineStatsOut, TeamOut

app = FastAPI(
    title="Sports Performance & News Analyst API",
    description="Connects sports news to what the underlying performance data actually shows.",
    version="1.0.0",
)

# Permissive CORS for local development (e.g. a future separate frontend
# calling this from a browser on a different port). Tighten this before
# deploying anywhere public.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# A handful of teams where football-data.org's own `crest` field is known
# to be stale (their upstream image hasn't caught up with a real-world
# rebrand). Checked before falling back to their API's value. If you clear
# data/cache.db and the crest is STILL wrong, that confirms it's genuinely
# their data (not our own caching) — add an entry here to fix it.
#
# Find a team's id with:
#   curl "https://api.football-data.org/v4/competitions/<CODE>/teams" \
#     -H "X-Auth-Token: YOUR_KEY"
# A Wikipedia/Wikimedia Commons club badge page is usually a safe, stable
# source for the replacement URL.
CREST_OVERRIDES: dict[int, str] = {
    64: "",   # Liverpool FC — confirmed id; paste the corrected crest URL
    # 0: "",  # Sporting CP — look up the id via the curl command above
}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/competitions", response_model=list[CompetitionOut])
def list_competitions() -> list[CompetitionOut]:
    return [
        CompetitionOut(code=code, name=name)
        for code, name in config.SUPPORTED_COMPETITIONS.items()
    ]


@app.get("/teams", response_model=list[TeamOut])
def list_teams(competition: str | None = None) -> list[TeamOut]:
    if competition and competition not in config.SUPPORTED_COMPETITIONS:
        raise HTTPException(status_code=400, detail=f"Unknown competition code '{competition}'")
    teams = team_lookup.list_teams(competition)
    return [TeamOut(**t) for t in teams]


@app.get("/teams/{team_id}/crest")
def get_team_crest(team_id: int) -> dict:
    override = CREST_OVERRIDES.get(team_id)
    if override:
        return {"team_id": team_id, "crest_url": override}
    try:
        info = stats_api.get_team_info(team_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch team info: {exc}")
    return {"team_id": team_id, "crest_url": info.get("crest")}


@app.get("/teams/{team_id}/headline", response_model=HeadlineStatsOut)
def get_team_headline(team_id: int, competition: str) -> HeadlineStatsOut:
    """
    Current league-standing headline numbers (position, record, goal
    difference, points) for a team in a specific competition. `available`
    is False — with all other fields null — if the competition has no
    league table (e.g. a knockout cup) or the team isn't in it.
    """
    if competition not in config.SUPPORTED_COMPETITIONS:
        raise HTTPException(status_code=400, detail=f"Unknown competition code '{competition}'")

    stats = data_analyst.get_headline_stats(team_id, competition)
    if stats is None:
        return HeadlineStatsOut(available=False)
    return HeadlineStatsOut(available=True, **stats)


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Runs the full pipeline synchronously: news research, pivot-date
    selection, performance-split analysis, and validation. This can take
    several seconds to tens of seconds (multiple LLM calls plus a stats API
    call) — there's no background/async job queue here, by design, to keep
    this a straightforward personal-project API rather than something that
    needs a task queue and polling endpoint.
    """
    result = orchestrator.run(
        team_id=request.team_id,
        team_name=request.team_name,
        event_query=request.query,
        window_days=request.window_days,
    )
    return AnalyzeResponse(**result)


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@app.post("/analyze/stream")
def analyze_stream(request: AnalyzeRequest) -> StreamingResponse:
    """
    Same pipeline as POST /analyze, but streamed as Server-Sent Events so a
    client can show live per-stage progress instead of waiting silently for
    one long response. Each event is a JSON line of one of these shapes:

        {"type": "progress", "stage": "<human-readable stage description>"}
        {"type": "result", "result": {<same shape as AnalyzeResponse>}}
        {"type": "error", "detail": "<error message>"}

    The pipeline itself (agents/orchestrator.py) is synchronous, so it runs
    in a background thread here; progress messages are pushed onto a queue
    that the generator below drains and yields from as SSE lines. This
    keeps the underlying agents/tools code unchanged — only this endpoint
    needs to know about threading.
    """
    progress_queue: queue.Queue = queue.Queue()

    def on_progress(stage: str) -> None:
        progress_queue.put({"type": "progress", "stage": stage})

    def worker() -> None:
        try:
            result = orchestrator.run(
                team_id=request.team_id,
                team_name=request.team_name,
                event_query=request.query,
                window_days=request.window_days,
                on_progress=on_progress,
            )
            progress_queue.put({"type": "result", "result": result})
        except Exception as exc:  # noqa: BLE001 — surface any failure to the client
            progress_queue.put({"type": "error", "detail": str(exc)})
        finally:
            progress_queue.put(None)  # sentinel: no more events

    def event_generator():
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        while True:
            item = progress_queue.get()
            if item is None:
                break
            yield _sse_event(item)

    return StreamingResponse(event_generator(), media_type="text/event-stream")