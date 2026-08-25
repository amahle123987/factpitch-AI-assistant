"""
Tests for agents.web_researcher — the two-step search-then-structure flow.
No real network/API calls: both the OpenAI search client and the LangChain
structuring LLM are mocked.
"""

from unittest.mock import MagicMock, patch

from agents import web_researcher
from agents.schemas import KeyEvent, NewsResearch, PrimaryEvent


def _fake_search_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.output_text = text
    return resp


class TestResearch:
    def test_happy_path_returns_structured_dict(self):
        search_resp = _fake_search_response("Raw notes about an injury on 2025-10-14.")
        structured = NewsResearch(
            query="test query",
            key_events=[KeyEvent(date="2025-10-14", headline="Player injured", detail="Knee injury")],
            primary_event=PrimaryEvent(date="2025-10-14", headline="Player injured", reason="Clear single event"),
            summary="A player got injured on 2025-10-14.",
        )
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = structured

        with patch.object(web_researcher._search_client.responses, "create", return_value=search_resp), \
             patch("agents.web_researcher._structuring_llm", mock_llm):
            result = web_researcher.research("test query")

        assert result["key_events"][0]["date"] == "2025-10-14"
        assert result["primary_event"]["headline"] == "Player injured"
        assert result["summary"] == "A player got injured on 2025-10-14."

    def test_query_field_is_always_the_callers_query(self):
        # Regression check: the structuring LLM could paraphrase the query
        # in its output — the caller's original string should always win.
        search_resp = _fake_search_response("notes")
        structured = NewsResearch(
            query="a paraphrased version",  # deliberately different
            key_events=[],
            primary_event=None,
            summary="summary",
        )
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = structured

        with patch.object(web_researcher._search_client.responses, "create", return_value=search_resp), \
             patch("agents.web_researcher._structuring_llm", mock_llm):
            result = web_researcher.research("original caller query")

        assert result["query"] == "original caller query"

    def test_empty_events_yields_null_primary_event(self):
        search_resp = _fake_search_response("Nothing specific found.")
        structured = NewsResearch(query="q", key_events=[], primary_event=None, summary="Nothing found.")
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = structured

        with patch.object(web_researcher._search_client.responses, "create", return_value=search_resp), \
             patch("agents.web_researcher._structuring_llm", mock_llm):
            result = web_researcher.research("q")

        assert result["key_events"] == []
        assert result["primary_event"] is None

    def test_structuring_failure_falls_back_to_raw_notes(self):
        search_resp = _fake_search_response("Some raw notes that failed to structure.")
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("simulated API error")

        with patch.object(web_researcher._search_client.responses, "create", return_value=search_resp), \
             patch("agents.web_researcher._structuring_llm", mock_llm):
            result = web_researcher.research("q")

        assert result["key_events"] == []
        assert result["primary_event"] is None
        assert result["summary"] == "Some raw notes that failed to structure."

    def test_search_failure_propagates(self):
        # Search itself failing (e.g. network error) is not caught here —
        # only the structuring step has a fallback. Confirms that behavior
        # is intentional rather than accidental.
        with patch.object(web_researcher._search_client.responses, "create",
                           side_effect=Exception("network error")):
            try:
                web_researcher.research("q")
                assert False, "expected an exception to propagate"
            except Exception as exc:
                assert "network error" in str(exc)
