"""
Validator / Critic agent.

Takes the Web-Researcher's findings and the Data-Analyst's stats and
judges whether the narrative ("team struggled after the injury") is
actually supported by the numbers, or whether it's overstated/coincidental.
"""

from openai import OpenAI

import config

_client = OpenAI(api_key=config.OPENAI_API_KEY)

_SYSTEM_PROMPT = """\
You are a sceptical sports analyst. You are given (1) a news summary about \
an event (e.g. an injury) and (2) before/after performance statistics.

Judge whether the statistics actually support the narrative implied by the \
news. Consider: direction of change, size of the change, small-sample \
caveats (e.g. don't over-read 3-4 matches), and — where the stats include \
an "avg_opponent_position" figure for the before and after periods — \
whether a change in results could be explained by facing tougher or \
easier opponents rather than by the news event itself. Note that opponent \
position reflects CURRENT standings, not standings at the time each match \
was played, so treat it as a rough indicator rather than precise evidence.

Respond in 2-4 plain sentences. Be direct about whether the data backs the \
story, contradicts it, or is inconclusive.\
"""


def validate(news_summary: dict, stats: dict) -> str:
    prompt = f"News summary:\n{news_summary}\n\nBefore/after stats:\n{stats}"
    response = _client.responses.create(
        model=config.OPENAI_MODEL,
        instructions=_SYSTEM_PROMPT,
        input=prompt,
    )
    return response.output_text.strip()
