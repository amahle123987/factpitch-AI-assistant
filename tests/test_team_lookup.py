"""
Tests for tools.team_lookup — name matching across competitions, and
deduplication when the same team appears in more than one (e.g. league +
Champions League).
"""

import pytest

from tools import team_lookup

PL_TEAMS = {
    "teams": [
        {"id": 57, "name": "Arsenal FC", "shortName": "Arsenal", "tla": "ARS"},
        {"id": 64, "name": "Liverpool FC", "shortName": "Liverpool", "tla": "LIV"},
        {"id": 66, "name": "Manchester United FC", "shortName": "Man United", "tla": "MUN"},
    ]
}
CL_TEAMS = {
    "teams": [
        {"id": 64, "name": "Liverpool FC", "shortName": "Liverpool", "tla": "LIV"},  # same team, different comp
    ]
}


@pytest.fixture
def mock_teams(mocker):
    def fake_get_teams(comp_code):
        return {"PL": PL_TEAMS, "CL": CL_TEAMS}.get(comp_code, {"teams": []})

    return mocker.patch("tools.team_lookup.stats_api.get_competition_teams", side_effect=fake_get_teams)


class TestFindTeam:
    def test_unique_partial_name_match(self, mock_teams):
        results = team_lookup.find_team("Arsenal")
        assert len(results) == 1
        assert results[0]["id"] == 57

    def test_tla_match(self, mock_teams):
        results = team_lookup.find_team("MUN")
        assert len(results) == 1
        assert results[0]["name"] == "Manchester United FC"

    def test_no_match(self, mock_teams):
        assert team_lookup.find_team("Nonexistent FC") == []

    def test_same_team_found_in_multiple_competitions(self, mock_teams):
        results = team_lookup.find_team("Liverpool")
        # raw find_team does NOT dedupe — that's resolve_team's job
        assert len(results) == 2

    def test_restricted_to_one_competition(self, mock_teams):
        results = team_lookup.find_team("Liverpool", competition="CL")
        assert len(results) == 1
        assert results[0]["competition"] == "CL"

    def test_case_insensitive(self, mock_teams):
        results = team_lookup.find_team("arsenal")
        assert len(results) == 1


class TestResolveTeam:
    def test_unique_match_resolves(self, mock_teams):
        result = team_lookup.resolve_team("Arsenal")
        assert result["id"] == 57

    def test_cross_competition_duplicate_resolves_to_one(self, mock_teams):
        # Liverpool appears in both PL and CL fixtures — should dedupe by id
        result = team_lookup.resolve_team("Liverpool")
        assert result is not None
        assert result["id"] == 64

    def test_no_match_returns_none(self, mock_teams):
        assert team_lookup.resolve_team("Nonexistent FC") is None


class TestResolveTeamAmbiguous:
    @pytest.fixture(autouse=True)
    def two_manchester_clubs(self, mocker):
        teams = {
            "teams": [
                {"id": 66, "name": "Manchester United FC", "shortName": "Man United", "tla": "MUN"},
                {"id": 65, "name": "Manchester City FC", "shortName": "Man City", "tla": "MCI"},
            ]
        }
        mocker.patch("tools.team_lookup.stats_api.get_competition_teams", return_value=teams)

    def test_ambiguous_name_returns_none(self):
        assert team_lookup.resolve_team("Manchester") is None


class TestListTeams:
    def test_single_competition_returns_sorted(self, mocker):
        teams = {"teams": [
            {"id": 65, "name": "Manchester City FC"},
            {"id": 57, "name": "Arsenal FC"},
        ]}
        mocker.patch("tools.team_lookup.stats_api.get_competition_teams", return_value=teams)

        result = team_lookup.list_teams("PL")
        assert [t["name"] for t in result] == ["Arsenal FC", "Manchester City FC"]

    def test_all_competitions_deduplicates_by_id(self, mocker):
        pl_teams = {"teams": [{"id": 64, "name": "Liverpool FC"}]}
        cl_teams = {"teams": [{"id": 64, "name": "Liverpool FC"}]}  # same team, different comp

        def fake_get_teams(code):
            return {"PL": pl_teams, "CL": cl_teams}.get(code, {"teams": []})

        mocker.patch("tools.team_lookup.stats_api.get_competition_teams", side_effect=fake_get_teams)

        result = team_lookup.list_teams(None)
        ids = [t["id"] for t in result]
        assert len(ids) == len(set(ids))  # no duplicates
        assert ids.count(64) == 1

    def test_skips_competition_that_errors(self, mocker):
        def fake_get_teams(code):
            if code == "PL":
                return {"teams": [{"id": 57, "name": "Arsenal FC"}]}
            raise Exception("simulated failure")

        mocker.patch("tools.team_lookup.stats_api.get_competition_teams", side_effect=fake_get_teams)

        result = team_lookup.list_teams(None)
        assert any(t["name"] == "Arsenal FC" for t in result)

    def test_empty_when_no_teams_found(self, mocker):
        mocker.patch("tools.team_lookup.stats_api.get_competition_teams", return_value={"teams": []})
        assert team_lookup.list_teams("PL") == []