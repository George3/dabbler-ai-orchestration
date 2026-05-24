"""Layer-1 unit tests for ai_router.joiner.parsers.

Uses tmp_path-based synthetic fixtures rather than the operator's
real ~/.claude / ~/.copilot directories.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_router.joiner.parsers import (
    claude_slug_to_cwd,
    read_session_state,
    scan_claude_logs,
    scan_copilot_logs,
    scan_launch_log,
    scan_session_states,
)


# ---------------------------------------------------------------------------
# Claude slug helper.
# ---------------------------------------------------------------------------


class TestClaudeSlugToCwd:
    def test_windows_drive_slug(self):
        assert claude_slug_to_cwd("C--Users-foo") == "c:/users/foo"

    def test_short_slug_no_drive_prefix(self):
        # Not a drive-style slug; canonicalize the slug as-is.
        assert claude_slug_to_cwd("abc") == "abc"


# ---------------------------------------------------------------------------
# Claude JSONL scraper.
# ---------------------------------------------------------------------------


@pytest.fixture
def claude_root(tmp_path: Path) -> Path:
    root = tmp_path / "claude-projects"
    workspace = root / "C--Users-foo-project"
    workspace.mkdir(parents=True)
    jsonl = workspace / "conv-abc.jsonl"
    jsonl.write_text(
        "\n".join([
            json.dumps({"timestamp": "2026-05-24T08:00:00Z", "cwd": "C:/Users/foo/project"}),
            json.dumps({"timestamp": "2026-05-24T08:00:05Z", "tool": "Edit"}),
            json.dumps({"timestamp": "2026-05-24T08:00:10Z", "tool": "Bash"}),
        ]),
        encoding="utf-8",
    )
    return root


def test_scan_claude_logs_returns_one_session(claude_root: Path):
    sessions = list(scan_claude_logs(claude_root))
    assert len(sessions) == 1
    s = sessions[0]
    assert s.engine == "claude"
    assert s.conv_id == "conv-abc"
    assert s.cwd_canonical == "c:/users/foo/project"
    assert s.cwd_source == "jsonl-field"
    assert s.first_event_ts.isoformat().startswith("2026-05-24T08:00:00")
    assert s.last_event_ts.isoformat().startswith("2026-05-24T08:00:10")


def test_scan_claude_logs_empty_root_no_error(tmp_path: Path):
    sessions = list(scan_claude_logs(tmp_path / "does-not-exist"))
    assert sessions == []


def test_scan_claude_logs_skips_malformed_lines(tmp_path: Path):
    root = tmp_path / "claude"
    ws = root / "C--foo"
    ws.mkdir(parents=True)
    (ws / "conv.jsonl").write_text(
        "not-json\n"
        + json.dumps({"timestamp": "2026-05-24T08:00:00Z", "cwd": "C:/foo"})
        + "\n"
        + "more-garbage\n",
        encoding="utf-8",
    )
    sessions = list(scan_claude_logs(root))
    assert len(sessions) == 1
    assert sessions[0].cwd_canonical == "c:/foo"


def test_scan_claude_logs_slug_fallback_when_no_cwd_field(tmp_path: Path):
    root = tmp_path / "claude"
    ws = root / "C--Users-foo"
    ws.mkdir(parents=True)
    (ws / "conv.jsonl").write_text(
        json.dumps({"timestamp": "2026-05-24T08:00:00Z"}) + "\n",
        encoding="utf-8",
    )
    sessions = list(scan_claude_logs(root))
    assert len(sessions) == 1
    assert sessions[0].cwd_source == "slug-fallback"
    assert sessions[0].cwd_canonical == "c:/users/foo"


# ---------------------------------------------------------------------------
# Copilot OTel JSONL scraper.
# ---------------------------------------------------------------------------


@pytest.fixture
def copilot_root(tmp_path: Path) -> Path:
    root = tmp_path / "copilot"
    session = root / "conv-xyz"
    session.mkdir(parents=True)
    events = session / "events.jsonl"
    events.write_text(
        json.dumps({
            "type": "session.start",
            "timestamp": "2026-05-24T08:00:00Z",
            "data": {
                "sessionId": "conv-xyz",
                "startTime": "2026-05-24T08:00:00Z",
                "context": {"cwd": "C:/Users/foo/project"},
            },
        }) + "\n"
        + json.dumps({"type": "turn.start", "timestamp": "2026-05-24T08:00:05Z"}) + "\n",
        encoding="utf-8",
    )
    return root


def test_scan_copilot_logs_returns_one_session(copilot_root: Path):
    sessions = list(scan_copilot_logs(copilot_root))
    assert len(sessions) == 1
    s = sessions[0]
    assert s.engine == "copilot"
    assert s.conv_id == "conv-xyz"
    assert s.cwd_canonical == "c:/users/foo/project"
    assert s.cwd_source == "context"


def test_scan_copilot_logs_skips_dirs_without_events(tmp_path: Path):
    root = tmp_path / "copilot"
    (root / "session-no-events").mkdir(parents=True)
    sessions = list(scan_copilot_logs(root))
    assert sessions == []


def test_scan_copilot_logs_skips_when_first_record_not_session_start(tmp_path: Path):
    root = tmp_path / "copilot"
    sess = root / "conv-bad"
    sess.mkdir(parents=True)
    (sess / "events.jsonl").write_text(
        json.dumps({"type": "turn.start", "timestamp": "2026-05-24T08:00:00Z"}) + "\n",
        encoding="utf-8",
    )
    sessions = list(scan_copilot_logs(root))
    assert sessions == []


# ---------------------------------------------------------------------------
# Session-state reader.
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace_with_state(tmp_path: Path) -> Path:
    """Build a synthetic <workspace>/docs/session-sets/<slug>/ layout."""
    workspace = tmp_path / "workspace"
    set_dir = workspace / "docs" / "session-sets" / "999-test-set"
    set_dir.mkdir(parents=True)
    state = {
        "schemaVersion": 3,
        "sessionSetName": "999-test-set",
        "sessions": [{"number": 1, "title": "Test", "status": "in-progress"}],
        "currentSession": 1,
        "totalSessions": 1,
        "completedSessions": [],
        "status": "in-progress",
        "startedAt": "2026-05-24T08:00:00-04:00",
        "orchestrator": {
            "engine": "claude-code",
            "provider": "anthropic",
            "model": "claude-opus-4-7",
            "effort": "high",
            "checkedOutAt": "2026-05-24T08:00:00-04:00",
            "lastActivityAt": "2026-05-24T09:00:00-04:00",
        },
    }
    (set_dir / "session-state.json").write_text(json.dumps(state), encoding="utf-8")
    return workspace


def test_read_session_state_returns_view(workspace_with_state: Path):
    state_file = workspace_with_state / "docs" / "session-sets" / "999-test-set" / "session-state.json"
    view = read_session_state(state_file)
    assert view is not None
    assert view.set_slug == "999-test-set"
    assert view.orchestrator_engine == "claude-code"
    assert view.orchestrator_provider == "anthropic"
    assert view.last_activity is not None


def test_read_session_state_missing_file_returns_none(tmp_path: Path):
    assert read_session_state(tmp_path / "nope.json") is None


def test_read_session_state_malformed_returns_none(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("not valid json", encoding="utf-8")
    assert read_session_state(bad) is None


def test_scan_session_states_walks_pattern(workspace_with_state: Path):
    views = list(scan_session_states(workspace_with_state))
    assert len(views) == 1
    assert views[0].set_slug == "999-test-set"


def test_scan_session_states_missing_pattern_root_no_error(tmp_path: Path):
    views = list(scan_session_states(tmp_path / "nothing"))
    assert views == []


# ---------------------------------------------------------------------------
# Launch-log reader (S3 will write to it; S2 just confirms the shape works).
# ---------------------------------------------------------------------------


def test_scan_launch_log_missing_file_returns_empty(tmp_path: Path):
    records = list(scan_launch_log(tmp_path / "no-such-launch-log.jsonl"))
    assert records == []


def test_scan_launch_log_parses_records(tmp_path: Path):
    log = tmp_path / "launch-log.jsonl"
    log.write_text(
        json.dumps({
            "launch_ts": "2026-05-24T08:00:00Z",
            "workspace_cwd": "C:/Users/foo/project",
            "set_slug": "045-log-harvest-implementation",
            "session_number": 2,
            "target_backend": "claude",
            "launch_id": "uuid-1",
            "effort": "high",
        }) + "\n",
        encoding="utf-8",
    )
    records = list(scan_launch_log(log))
    assert len(records) == 1
    r = records[0]
    assert r.set_slug == "045-log-harvest-implementation"
    assert r.workspace_cwd_canonical == "c:/users/foo/project"
    assert r.target_backend == "claude"
    assert r.effort == "high"
    assert r.raw_ref["line"] == 1


def test_scan_launch_log_skips_malformed_and_missing_ts(tmp_path: Path):
    log = tmp_path / "launch-log.jsonl"
    log.write_text(
        "not-json\n"
        + json.dumps({"set_slug": "no-ts"}) + "\n"  # no launch_ts → skip
        + json.dumps({"launch_ts": "2026-05-24T08:00:00Z", "workspace_cwd": "/foo"}) + "\n",
        encoding="utf-8",
    )
    records = list(scan_launch_log(log))
    assert len(records) == 1
    assert records[0].workspace_cwd_canonical == "/foo"
