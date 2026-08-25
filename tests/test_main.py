"""
Tests for main.py's _extract_flag CLI argument parsing.
"""

import pytest

from main import _extract_flag


class TestExtractFlag:
    def test_flag_at_start(self):
        value, remaining = _extract_flag(["--team", "Liverpool FC", "recent", "news"], "--team")
        assert value == "Liverpool FC"
        assert remaining == ["recent", "news"]

    def test_flag_absent_returns_none_and_unchanged_args(self):
        args = ["recent", "news"]
        value, remaining = _extract_flag(args, "--team")
        assert value is None
        assert remaining == args

    def test_flag_in_middle(self):
        value, remaining = _extract_flag(
            ["recent", "--days", "90", "injury", "news"], "--days"
        )
        assert value == "90"
        assert remaining == ["recent", "injury", "news"]

    def test_two_different_flags_extracted_independently(self):
        args = ["--days", "90", "--team", "Arsenal", "query", "text"]
        days, args = _extract_flag(args, "--days")
        team, args = _extract_flag(args, "--team")
        assert days == "90"
        assert team == "Arsenal"
        assert args == ["query", "text"]

    def test_flag_with_no_value_exits(self):
        with pytest.raises(SystemExit):
            _extract_flag(["--days"], "--days")
