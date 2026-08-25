"""
Tests for agents.orchestrator — specifically the date-parsing and
pivot-selection logic, since that's the part with the most subtle edge
cases (exact vs. approximate dates, malformed model output, fallback order).
"""

from agents.orchestrator import _looks_like_date, _parse_date, _select_pivot_date


class TestParseDate:
    def test_exact_date(self):
        assert _parse_date("2026-02-22") == ("2026-02-22", False)

    def test_year_month_with_question_marks(self):
        assert _parse_date("2025-08-??") == ("2025-08-15", True)

    def test_year_month_only(self):
        assert _parse_date("2025-08") == ("2025-08-15", True)

    def test_invalid_month_rejected(self):
        assert _parse_date("2025-13-??") is None

    def test_garbage_string_rejected(self):
        assert _parse_date("not a date") is None

    def test_empty_string_rejected(self):
        assert _parse_date("") is None

    def test_none_rejected(self):
        assert _parse_date(None) is None

    def test_invalid_calendar_day_rejected(self):
        assert _parse_date("2025-02-30") is None  # Feb has no 30th


class TestLooksLikeDate:
    def test_true_for_exact_date(self):
        assert _looks_like_date("2026-02-22") is True

    def test_false_for_approximate_date(self):
        # backward-compat helper is exact-only by design
        assert _looks_like_date("2025-08-??") is False

    def test_false_for_garbage(self):
        assert _looks_like_date("nonsense") is False


class TestSelectPivotDate:
    def test_prefers_exact_primary_event(self):
        news = {
            "key_events": [{"date": "2025-08-??", "headline": "vague"}],
            "primary_event": {"date": "2025-10-14", "headline": "exact", "reason": "clear"},
        }
        assert _select_pivot_date(news) == "2025-10-14"

    def test_uses_approximate_primary_event_if_thats_all_there_is(self):
        news = {
            "key_events": [{"date": "2025-08-??", "headline": "vague"}],
            "primary_event": {"date": "2025-08-??", "headline": "vague", "reason": "best guess"},
        }
        assert _select_pivot_date(news) == "2025-08-15"

    def test_falls_back_to_earliest_exact_key_event_over_approx(self):
        news = {
            "key_events": [
                {"date": "2025-08-??", "headline": "vague"},
                {"date": "2025-10-14", "headline": "exact"},
            ],
            # no primary_event at all
        }
        assert _select_pivot_date(news) == "2025-10-14"

    def test_falls_back_to_earliest_approx_when_no_exact_dates_exist(self):
        news = {
            "key_events": [
                {"date": "2025-09-??", "headline": "a"},
                {"date": "2025-08-??", "headline": "b"},
            ],
        }
        assert _select_pivot_date(news) == "2025-08-15"

    def test_returns_none_when_nothing_usable(self):
        news = {"key_events": [{"date": "garbage", "headline": "x"}]}
        assert _select_pivot_date(news) is None

    def test_malformed_primary_event_falls_back_to_key_events(self):
        news = {
            "key_events": [{"date": "2025-10-14", "headline": "exact"}],
            "primary_event": {"date": "unknown", "headline": "vague"},
        }
        assert _select_pivot_date(news) == "2025-10-14"

    def test_earliest_of_multiple_exact_dates_is_chosen(self):
        news = {
            "key_events": [
                {"date": "2025-11-01", "headline": "later"},
                {"date": "2025-10-01", "headline": "earlier"},
            ],
        }
        assert _select_pivot_date(news) == "2025-10-01"
