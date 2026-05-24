"""Layer-1 unit tests for ai_router.joiner.schema."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ai_router.joiner.schema import (
    HarvestRecord,
    canonicalize_cwd,
    harvest,
    normalize_engine,
    parse_iso,
    serialize_records,
)


class TestCanonicalizeCwd:
    def test_backslashes_become_forward_slashes(self):
        assert canonicalize_cwd("C:\\foo\\bar") == "c:/foo/bar"

    def test_trailing_slash_stripped(self):
        assert canonicalize_cwd("/tmp/foo/") == "/tmp/foo"

    def test_case_insensitive_windows(self):
        assert canonicalize_cwd("C:/Users/Foo") == "c:/users/foo"

    def test_empty_string(self):
        assert canonicalize_cwd("") == ""

    def test_no_op_already_canonical(self):
        assert canonicalize_cwd("c:/users/foo") == "c:/users/foo"


class TestNormalizeEngine:
    def test_claude_code_normalizes_to_claude(self):
        assert normalize_engine("claude-code") == "claude"

    def test_copilot_cli_normalizes_to_copilot(self):
        assert normalize_engine("copilot-cli") == "copilot"

    def test_already_normalized(self):
        assert normalize_engine("claude") == "claude"

    def test_uppercase_handled(self):
        assert normalize_engine("Claude-Code") == "claude"

    def test_empty(self):
        assert normalize_engine("") == ""


class TestParseIso:
    def test_z_suffix(self):
        assert parse_iso("2026-05-24T08:00:00Z") == datetime(
            2026, 5, 24, 8, 0, 0, tzinfo=timezone.utc
        )

    def test_offset_suffix(self):
        result = parse_iso("2026-05-24T04:00:00-04:00")
        assert result == datetime(2026, 5, 24, 8, 0, 0, tzinfo=timezone.utc)

    def test_naive_assumed_utc(self):
        result = parse_iso("2026-05-24T08:00:00")
        assert result == datetime(2026, 5, 24, 8, 0, 0, tzinfo=timezone.utc)

    def test_malformed_raises(self):
        with pytest.raises(ValueError):
            parse_iso("not-a-date")


class TestHarvestRecord:
    def test_to_json_dict_serializes_ts(self):
        rec = HarvestRecord(
            ts=datetime(2026, 5, 24, 8, 0, 0, tzinfo=timezone.utc),
            event_type="session_start",
            source="claude-native",
            engine="claude",
            workspace_cwd="C:/foo",
            workspace_cwd_canonical="c:/foo",
            conv_id="abc",
            raw_ref={"file": "x.jsonl", "field": "first-event"},
        )
        payload = rec.to_json_dict()
        assert payload["ts"] == "2026-05-24T08:00:00+00:00"
        assert payload["event_type"] == "session_start"
        assert payload["conv_id"] == "abc"

    def test_serialize_records_roundtrip(self):
        rec = HarvestRecord(
            ts=datetime(2026, 5, 24, 8, 0, 0, tzinfo=timezone.utc),
            event_type="launch",
            source="wrapper",
            engine="claude",
            workspace_cwd="C:/foo",
            workspace_cwd_canonical="c:/foo",
        )
        output = serialize_records([rec])
        assert "launch" in output
        assert "claude" in output


class TestHarvest:
    """Integration smoke for the harvest() entry point with isolated fixtures."""

    def test_harvest_returns_iterable(self):
        # With no overrides this scans the operator's home; just confirm
        # the entry point returns an iterable without errors.
        result = list(harvest(workspace_cwd="c:/nonexistent/path/never-matches"))
        assert result == []
