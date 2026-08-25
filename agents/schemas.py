"""
Shared Pydantic schemas.

Used by agents.web_researcher (as the LangChain structured-output target)
and by the FastAPI layer (as response models), so both stay in sync with
one definition instead of two hand-maintained JSON shapes.
"""

from typing import Optional

from pydantic import BaseModel, Field


class KeyEvent(BaseModel):
    date: str = Field(
        description="YYYY-MM-DD if the exact day is known, YYYY-MM-?? if only "
                    "the month is known. Never fabricate a date."
    )
    headline: str = Field(description="Short factual headline for this event.")
    detail: str = Field(default="", description="A sentence or two of extra context.")


class PrimaryEvent(BaseModel):
    date: str = Field(description="Same date format rules as KeyEvent.date.")
    headline: str
    reason: str = Field(
        description="Why this specific event is the best single pivot point "
                    "for a before/after performance comparison — e.g. it marks "
                    "a clean start or resolution, not just the earliest or "
                    "latest mention."
    )


class NewsResearch(BaseModel):
    """The structured result of researching a team/player news query."""
    query: str
    key_events: list[KeyEvent] = Field(default_factory=list)
    primary_event: Optional[PrimaryEvent] = Field(
        default=None,
        description="Must be null if key_events is empty. Otherwise, must "
                    "describe the same event as exactly one of the key_events "
                    "entries — the single best turning point among them.",
    )
    summary: str = Field(description="2-4 sentence plain-language summary.")
