"""
Web-Researcher agent.

Two-step design:
  1. OpenAI's Responses API + built-in web_search tool gathers raw, factual
     research notes (unstructured text) — unchanged mechanism from before.
  2. A LangChain-wrapped model extracts those notes into a validated
     NewsResearch schema (agents/schemas.py), replacing the old approach of
     asking the model to "respond only with JSON" and manually stripping
     markdown fences / catching json.JSONDecodeError. LangChain's
     with_structured_output enforces the schema via OpenAI's native
     Structured Outputs API, so malformed output isn't possible — the
     API guarantees a schema-conforming response.

Splitting search from structuring also means each step can be tested and
reasoned about independently: step 1 owns "did we find real information",
step 2 owns "did we shape it correctly".
"""

from openai import OpenAI
from langchain_openai import ChatOpenAI

import config
from agents.schemas import NewsResearch

_search_client = OpenAI(api_key=config.OPENAI_API_KEY)
_structuring_llm = ChatOpenAI(
    model=config.OPENAI_MODEL,
    api_key=config.OPENAI_API_KEY,
    temperature=0,
).with_structured_output(NewsResearch)

_SEARCH_INSTRUCTIONS = """\
You are a sports news researcher. Given a query about a team or player, \
search the web and write up factual research notes covering what you find:
dated events (injuries, transfers, managerial changes, notable results),
and a plain-language summary of the overall situation.

Only report events you found real sources for. If you can't find a precise \
date for something, say so explicitly rather than guessing silently. Do \
not fabricate dates or events.\
"""

_STRUCTURING_INSTRUCTIONS = """\
You are given raw research notes about a sports team or player, plus the \
original query that produced them. Extract the notes into the required \
structured format.

Rules:
- Only include events that are actually stated in the notes — never invent \
  or infer an event that isn't there.
- If the notes describe no dated events at all, key_events must be an empty \
  list and primary_event must be null.
- Otherwise, primary_event must describe the SAME event as exactly one of \
  the key_events entries — pick whichever one is the best single pivot \
  point for a before/after performance comparison (a clean start or \
  resolution of a situation, not just the earliest or most recent mention). \
  Explain the choice in "reason".
- Dates: use YYYY-MM-DD when the notes give an exact day. If only a month \
  is known, use YYYY-MM-??. Never fabricate a day that wasn't stated.\
"""


def research(query: str) -> dict:
    """
    Run a web-search-backed research query.
    Returns a dict matching the NewsResearch schema:
        {query, key_events: [...], primary_event: {...} | None, summary}
    """
    search_response = _search_client.responses.create(
        model=config.OPENAI_MODEL,
        instructions=_SEARCH_INSTRUCTIONS,
        tools=[{"type": "web_search"}],
        input=query,
    )
    raw_notes = search_response.output_text.strip()

    try:
        structured = _structuring_llm.invoke([
            ("system", _STRUCTURING_INSTRUCTIONS),
            ("human", f"Original query: {query}\n\nRaw research notes:\n{raw_notes}"),
        ])
        result = structured.model_dump()
        result["query"] = query  # ensure it's exactly the caller's query, not a paraphrase
        return result
    except Exception as exc:
        # Structuring failed (e.g. API error) — fall back to an empty-events
        # shape with the raw notes as the summary, so the orchestrator's
        # "no key_events" path handles it gracefully rather than crashing.
        print(f"[web_researcher] Structured extraction failed: {exc}")
        return {"query": query, "key_events": [], "primary_event": None, "summary": raw_notes}


if __name__ == "__main__":
    import json
    result = research(f"Recent injury news for {config.DEFAULT_TEAM_NAME}")
    print(json.dumps(result, indent=2))
