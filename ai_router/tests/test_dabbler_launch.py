"""Layer-1 unit tests for the dabbler-launch wrapper CLI.

These tests use synthetic launch logs under tmp_path; the wrapper's
subprocess spawn is exercised separately (the L1 layer here uses
``spawn=False`` / ``--dry-run`` to avoid invoking a real AI CLI).
The Layer-2 e2e test
(:mod:`ai_router.tests.test_dabbler_launch_join_e2e`) covers the
join round-trip.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ai_router.dabbler_launch import (
    LaunchInputs,
    append_launch_record,
    build_record,
    main,
    parse_args,
    run_launch,
)


def _basic_inputs(launch_log: Path, **overrides) -> LaunchInputs:
    defaults = dict(
        engine="claude",
        workspace_cwd="C:/Users/foo/project",
        set_slug="045-log-harvest-implementation",
        session_number=3,
        effort="high",
        provider="anthropic",
        model="claude-opus-4-7",
        launch_log=launch_log,
        child_argv=[],
    )
    defaults.update(overrides)
    return LaunchInputs(**defaults)


class TestBuildRecord:
    def test_emits_canonical_harvest_record_shape(self, tmp_path):
        inputs = _basic_inputs(tmp_path / "launch-log.jsonl")
        when = datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)
        rec = build_record(inputs=inputs, launch_id="launch-1", when=when)
        assert rec["ts"] == "2026-05-24T12:00:00+00:00"
        assert rec["event_type"] == "launch"
        assert rec["source"] == "wrapper"
        assert rec["engine"] == "claude"
        assert rec["provider"] == "anthropic"
        assert rec["model"] == "claude-opus-4-7"
        assert rec["workspace_cwd"] == "C:/Users/foo/project"
        assert rec["workspace_cwd_canonical"] == "c:/users/foo/project"
        assert rec["set_slug"] == "045-log-harvest-implementation"
        assert rec["session_number"] == 3
        assert rec["effort"] == "high"
        assert rec["raw_ref"]["launch_id"] == "launch-1"
        # Per §5.1, these fields are emitted as null on a launch event.
        for null_field in ("conv_id", "binding_state", "tool", "tool_args_summary",
                           "tokens_in", "tokens_out", "bound_candidates"):
            assert rec[null_field] is None

    def test_default_timestamp_is_utc_now(self, tmp_path):
        inputs = _basic_inputs(tmp_path / "launch-log.jsonl")
        rec = build_record(inputs=inputs, launch_id="x")
        # Should parse cleanly as ISO and carry a UTC offset.
        parsed = datetime.fromisoformat(rec["ts"])
        assert parsed.tzinfo is not None


class TestAppendLaunchRecord:
    def test_appends_jsonl_creating_parent_dir(self, tmp_path):
        log = tmp_path / "subdir" / "launch-log.jsonl"
        append_launch_record(log, {"ts": "2026-01-01T00:00:00+00:00", "engine": "claude"})
        append_launch_record(log, {"ts": "2026-01-01T00:00:01+00:00", "engine": "copilot"})
        lines = log.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["engine"] == "claude"
        assert json.loads(lines[1])["engine"] == "copilot"


class TestRunLaunch:
    def test_run_launch_dry_run_writes_record_and_skips_spawn(self, tmp_path):
        log = tmp_path / "launch-log.jsonl"
        inputs = _basic_inputs(log, child_argv=["echo", "hello"])
        launch_id, exit_code = run_launch(inputs, spawn=False)
        assert exit_code == 0
        assert log.exists()
        lines = log.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        rec = json.loads(lines[0])
        assert rec["raw_ref"]["launch_id"] == launch_id

    def test_run_launch_unique_launch_ids(self, tmp_path):
        log = tmp_path / "launch-log.jsonl"
        inputs = _basic_inputs(log)
        ids = {run_launch(inputs, spawn=False)[0] for _ in range(5)}
        assert len(ids) == 5  # uuid4 collisions are astronomically unlikely


class TestParseArgs:
    def test_engine_validation(self, capsys):
        with pytest.raises(SystemExit):
            parse_args([
                "--engine", "unknown-vendor",
                "--workspace-cwd", "/tmp",
                "--dry-run",
            ])
        err = capsys.readouterr().err
        assert "--engine must be one of" in err

    def test_dry_run_allows_empty_child_argv(self, tmp_path):
        inputs, dry_run = parse_args([
            "--engine", "claude",
            "--workspace-cwd", str(tmp_path),
            "--launch-log", str(tmp_path / "log.jsonl"),
            "--dry-run",
        ])
        assert dry_run is True
        assert inputs.child_argv == []

    def test_non_dry_run_requires_child_argv(self, capsys):
        with pytest.raises(SystemExit):
            parse_args([
                "--engine", "claude",
                "--workspace-cwd", "/tmp",
            ])
        err = capsys.readouterr().err
        assert "no child argv supplied" in err

    def test_strips_leading_double_dash_separator(self, tmp_path):
        inputs, _ = parse_args([
            "--engine", "claude",
            "--workspace-cwd", "/tmp",
            "--launch-log", str(tmp_path / "log.jsonl"),
            "--", "claude", "code", "--effort", "high",
        ])
        assert inputs.child_argv == ["claude", "code", "--effort", "high"]


class TestMain:
    def test_main_dry_run_writes_and_returns_zero(self, tmp_path, capsys):
        log = tmp_path / "launch-log.jsonl"
        rc = main([
            "--engine", "copilot",
            "--workspace-cwd", str(tmp_path),
            "--launch-log", str(log),
            "--set-slug", "999-test",
            "--session-number", "1",
            "--dry-run",
        ])
        assert rc == 0
        out = capsys.readouterr().out
        assert "launch-id:" in out
        assert str(log) in out
        rec = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
        assert rec["engine"] == "copilot"
        assert rec["set_slug"] == "999-test"
        assert rec["session_number"] == 1
