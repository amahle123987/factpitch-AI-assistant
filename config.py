"""
Central configuration for the Sports Performance & News Analyst.

Edit TEAM_ID / COMPETITION below to point the analyst at a different
team or league. Team and competition IDs come from the football-data.org
API — see README.md for how to look them up.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- API credentials -------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")

if not OPENAI_API_KEY:
    raise EnvironmentError("Missing OPENAI_API_KEY — copy .env.example to .env and fill it in.")
if not FOOTBALL_DATA_API_KEY:
    raise EnvironmentError("Missing FOOTBALL_DATA_API_KEY — copy .env.example to .env and fill it in.")

# --- LLM settings ------------------------------------------------------------
# Check your OpenAI account for which models you have access to — swap freely.
OPENAI_MODEL = "gpt-5.1"

# --- football-data.org settings ---------------------------------------------
FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4"

# Default team/competition — used when no --team flag is given at the CLI,
# or as a fallback if a --team lookup finds no match. Edit these, or override
# per-run with: python main.py --team "Liverpool FC" "your query"
DEFAULT_TEAM_ID = 57
DEFAULT_TEAM_NAME = "Arsenal FC"
DEFAULT_COMPETITION = "PL"

# Free-tier competitions available on football-data.org, used when searching
# for a team by name across leagues. Verify against your own account if in
# doubt — free-tier coverage can change.
SUPPORTED_COMPETITIONS = {
    "PL": "Premier League",
    "ELC": "Championship",
    "PD": "La Liga",
    "SA": "Serie A",
    "BL1": "Bundesliga",
    "FL1": "Ligue 1",
    "DED": "Eredivisie",
    "PPL": "Primeira Liga",
    "CL": "Champions League",
    "EC": "European Championship",
    "WC": "World Cup",
    "BSA": "Campeonato Brasileiro Série A",
}

# --- Local cache --------------------------------------------------------------
CACHE_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "cache.db")

# --- Misc ----------------------------------------------------------------------
CHART_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data")
