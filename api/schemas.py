"""
Request/response models for the FastAPI layer.
"""

from typing import Optional

from pydantic import BaseModel, Field

from agents.schemas import NewsResearch


class TeamOut(BaseModel):
    id: int
    name: str
    competition: str


class CompetitionOut(BaseModel):
    code: str
    name: str


class AnalyzeRequest(BaseModel):
    team_id: int
    team_name: str
    query: str
    window_days: int = Field(default=60, ge=15, le=365)


class SplitStats(BaseModel):
    """Loosely typed — the underlying dict's exact keys (win_rate,
    avg_opponent_position, etc.) vary depending on data availability, so
    this is intentionally permissive rather than a rigid schema."""
    model_config = {"extra": "allow"}

    matches: int = 0


class AnalyzeResponse(BaseModel):
    news: NewsResearch
    stats: Optional[dict] = None
    verdict: str


class HeadlineStatsOut(BaseModel):
    """Current league-standing snapshot for a team. All fields except
    `available` are null when the competition has no league table (e.g. a
    knockout cup) or the team isn't in it."""
    available: bool
    position: Optional[int] = None
    played: Optional[int] = None
    won: Optional[int] = None
    draw: Optional[int] = None
    lost: Optional[int] = None
    goals_for: Optional[int] = None
    goals_against: Optional[int] = None
    goal_difference: Optional[int] = None
    points: Optional[int] = None